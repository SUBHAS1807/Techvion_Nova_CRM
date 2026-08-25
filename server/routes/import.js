const express = require('express');
const router = express.Router();
const multer = require('multer');
const { query } = require('../config/database');
const { parseUploadedFile } = require('../utils/excelEngine');
const { detectColumns, STANDARD_CRM_FIELDS } = require('../utils/columnMapper');
const { cleanAndEnrichLead, cleanString } = require('../utils/dataCleaner');
const { generateBatchLeadIds } = require('../utils/helpers');

// Configure multer memory storage
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 25 * 1024 * 1024 }, // 25 MB max
});

/**
 * POST /api/import/preview
 * Analyzes uploaded file, detects columns, cleans preview records,
 * checks for duplicates, and calculates health stats before saving.
 */
router.post('/preview', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ success: false, error: 'No file uploaded' });
    }

    const { headers, rawRows } = parseUploadedFile(req.file.buffer, req.file.originalname);
    const columnMapping = detectColumns(headers);

    // Fetch existing emails, phones, and business+city keys for duplicate detection
    const existingResult = await query('SELECT email, phone, website, business_name, city FROM leads');
    const existingEmails = new Set(existingResult.rows.map(r => cleanString(r.email).toLowerCase()).filter(Boolean));
    const existingPhones = new Set(existingResult.rows.map(r => cleanString(r.phone).replace(/\D/g, '')).filter(p => p.length >= 7));
    const existingKeys = new Set(existingResult.rows.map(r => `${cleanString(r.business_name).toLowerCase()}_${cleanString(r.city).toLowerCase()}`));

    let validCount = 0;
    let invalidCount = 0;
    let duplicateCount = 0;
    let missingEmailCount = 0;
    let missingWebsiteCount = 0;
    let needsVerificationCount = 0;

    const seenFileEmails = new Set();
    const seenFilePhones = new Set();
    const seenFileKeys = new Set();

    const sampleRows = [];
    const maxSample = Math.min(rawRows.length, 50);

    for (let i = 0; i < rawRows.length; i++) {
      const raw = rawRows[i];

      // Map raw headers to CRM fields
      const leadObj = {};
      for (const [header, targetField] of Object.entries(columnMapping)) {
        if (targetField && targetField !== 'ignore') {
          leadObj[targetField] = raw[header];
        }
      }

      const cleaned = cleanAndEnrichLead(leadObj);

      // Check validation
      const hasBusinessName = Boolean(cleaned.business_name && cleaned.business_name !== 'Unnamed Business');
      if (!hasBusinessName) {
        invalidCount++;
      } else {
        validCount++;
      }

      // Check duplicates
      let isDuplicate = false;
      let duplicateReason = '';
      const emailLower = cleaned.email ? cleaned.email.toLowerCase() : '';
      const phoneDigits = cleaned.phone ? cleaned.phone.replace(/\D/g, '') : '';
      const bizCityKey = `${cleaned.business_name.toLowerCase()}_${cleaned.city.toLowerCase()}`;

      if (emailLower && (existingEmails.has(emailLower) || seenFileEmails.has(emailLower))) {
        isDuplicate = true;
        duplicateReason = 'Matching Email in database/file';
      } else if (phoneDigits.length >= 7 && (existingPhones.has(phoneDigits) || seenFilePhones.has(phoneDigits))) {
        isDuplicate = true;
        duplicateReason = 'Matching Phone in database/file';
      } else if (bizCityKey.length > 3 && (existingKeys.has(bizCityKey) || seenFileKeys.has(bizCityKey))) {
        isDuplicate = true;
        duplicateReason = 'Matching Business Name & City in database/file';
      }

      if (emailLower) seenFileEmails.add(emailLower);
      if (phoneDigits.length >= 7) seenFilePhones.add(phoneDigits);
      if (bizCityKey.length > 3) seenFileKeys.add(bizCityKey);

      if (isDuplicate) duplicateCount++;
      if (!cleaned.email) missingEmailCount++;
      if (!cleaned.website || cleaned.website_status === 'No Website') missingWebsiteCount++;
      if (cleaned.needs_verification) needsVerificationCount++;

      if (i < maxSample) {
        sampleRows.push({
          row_index: i + 1,
          ...cleaned,
          is_duplicate: isDuplicate,
          duplicate_reason: duplicateReason,
          raw_data: raw,
        });
      }
    }

    return res.json({
      success: true,
      filename: req.file.originalname,
      headers,
      columnMapping,
      standardFields: STANDARD_CRM_FIELDS,
      summary: {
        totalRows: rawRows.length,
        validRecords: validCount,
        invalidRecords: invalidCount,
        duplicateRecords: duplicateCount,
        missingEmail: missingEmailCount,
        missingWebsite: missingWebsiteCount,
        needsVerification: needsVerificationCount,
      },
      sampleRows,
      rawRows, // returned so client can submit on confirm
    });
  } catch (err) {
    console.error('Error during import preview:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * POST /api/import/confirm
 * Commits cleaned data with confirmed column mappings into the database
 */
router.post('/confirm', async (req, res) => {
  try {
    const { rawRows, columnMapping, skipDuplicates = true, defaultSource = 'Excel Import' } = req.body;

    if (!rawRows || !Array.isArray(rawRows) || rawRows.length === 0) {
      return res.status(400).json({ success: false, error: 'No records to import' });
    }

    // Fetch existing identifiers for duplicate checks
    const existingResult = await query('SELECT email, phone, business_name, city FROM leads');
    const existingEmails = new Set(existingResult.rows.map(r => cleanString(r.email).toLowerCase()).filter(Boolean));
    const existingPhones = new Set(existingResult.rows.map(r => cleanString(r.phone).replace(/\D/g, '')).filter(p => p.length >= 7));
    const existingKeys = new Set(existingResult.rows.map(r => `${cleanString(r.business_name).toLowerCase()}_${cleanString(r.city).toLowerCase()}`));

    const leadsToInsert = [];
    let skippedDuplicates = 0;
    let skippedInvalid = 0;

    const seenFileEmails = new Set();
    const seenFilePhones = new Set();
    const seenFileKeys = new Set();

    for (let i = 0; i < rawRows.length; i++) {
      const raw = rawRows[i];
      const leadObj = {};

      for (const [header, targetField] of Object.entries(columnMapping || {})) {
        if (targetField && targetField !== 'ignore') {
          leadObj[targetField] = raw[header];
        }
      }

      if (!leadObj.lead_source) {
        leadObj.lead_source = defaultSource;
      }

      const cleaned = cleanAndEnrichLead(leadObj);

      // Skip invalid rows without business name
      if (!cleaned.business_name || cleaned.business_name === 'Unnamed Business') {
        skippedInvalid++;
        continue;
      }

      // Check duplicates
      const emailLower = cleaned.email ? cleaned.email.toLowerCase() : '';
      const phoneDigits = cleaned.phone ? cleaned.phone.replace(/\D/g, '') : '';
      const bizCityKey = `${cleaned.business_name.toLowerCase()}_${cleaned.city.toLowerCase()}`;

      const isDup =
        (emailLower && (existingEmails.has(emailLower) || seenFileEmails.has(emailLower))) ||
        (phoneDigits.length >= 7 && (existingPhones.has(phoneDigits) || seenFilePhones.has(phoneDigits))) ||
        (bizCityKey.length > 3 && (existingKeys.has(bizCityKey) || seenFileKeys.has(bizCityKey)));

      if (isDup && skipDuplicates) {
        skippedDuplicates++;
        continue;
      }

      if (emailLower) seenFileEmails.add(emailLower);
      if (phoneDigits.length >= 7) seenFilePhones.add(phoneDigits);
      if (bizCityKey.length > 3) seenFileKeys.add(bizCityKey);

      leadsToInsert.push(cleaned);
    }

    if (leadsToInsert.length === 0) {
      return res.json({
        success: true,
        message: 'No new leads imported (all were duplicates or empty).',
        importedCount: 0,
        skippedDuplicates,
        skippedInvalid,
      });
    }

    // Generate batch IDs
    const leadIds = await generateBatchLeadIds(leadsToInsert.length);

    // Insert records
    for (let i = 0; i < leadsToInsert.length; i++) {
      const lead = leadsToInsert[i];
      const id = leadIds[i];

      const insertSql = `
        INSERT INTO leads (
          lead_id, business_name, industry, email, email_status, phone, website,
          website_status, address, city, state, country, postal_code, lead_status,
          lead_source, contact_person, notes, data_quality, is_verified,
          needs_verification, location_verified, verification_reason, last_contacted,
          created_at, updated_at
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
          $15, $16, $17, $18, $19, $20, $21, $22, $23, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
      `;

      const params = [
        id,
        lead.business_name,
        lead.industry,
        lead.email,
        lead.email_status,
        lead.phone,
        lead.website,
        lead.website_status,
        lead.address,
        lead.city,
        lead.state,
        lead.country,
        lead.postal_code,
        lead.lead_status,
        lead.lead_source,
        lead.contact_person,
        lead.notes,
        lead.data_quality,
        lead.is_verified ? 1 : 0,
        lead.needs_verification ? 1 : 0,
        lead.location_verified ? 1 : 0,
        lead.verification_reason,
        lead.last_contacted,
      ];

      await query(insertSql, params);
    }

    return res.json({
      success: true,
      message: `Successfully imported ${leadsToInsert.length} clean leads.`,
      importedCount: leadsToInsert.length,
      skippedDuplicates,
      skippedInvalid,
    });
  } catch (err) {
    console.error('Error confirming import:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
