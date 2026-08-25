const express = require('express');
const router = express.Router();
const { query } = require('../config/database');
const { generateBlackWhiteExcel, generateCleanCSV } = require('../utils/excelEngine');

/**
 * Helper to fetch leads matching filter or selection criteria
 */
const fetchLeadsForExport = async (reqBody, reqQuery) => {
  const {
    lead_ids,
    search,
    website_status,
    has_website,
    email_status,
    lead_status,
    lead_source,
    data_quality,
    city,
    state,
    country,
    industry,
    needs_verification,
    is_verified,
  } = { ...reqQuery, ...reqBody };

  // If specific lead IDs provided
  if (lead_ids && Array.isArray(lead_ids) && lead_ids.length > 0) {
    const placeholders = lead_ids.map((_, idx) => `$${idx + 1}`).join(',');
    const sql = `SELECT * FROM leads WHERE lead_id IN (${placeholders}) ORDER BY created_at DESC`;
    const result = await query(sql, lead_ids);
    return result.rows;
  }

  // Otherwise apply filters
  const conditions = [];
  const params = [];

  if (search && search.trim()) {
    const term = `%${search.trim()}%`;
    params.push(term, term, term, term, term, term, term);
    const startIdx = params.length - 6;
    conditions.push(`(
      business_name LIKE $${startIdx} OR
      email LIKE $${startIdx + 1} OR
      phone LIKE $${startIdx + 2} OR
      website LIKE $${startIdx + 3} OR
      city LIKE $${startIdx + 4} OR
      state LIKE $${startIdx + 5} OR
      country LIKE $${startIdx + 6}
    )`);
  }

  if (website_status) {
    params.push(website_status);
    conditions.push(`website_status = $${params.length}`);
  }

  if (has_website === 'no' || has_website === 'false') {
    conditions.push(`(website_status = 'No Website' OR website IS NULL OR website = '')`);
  } else if (has_website === 'yes' || has_website === 'true') {
    conditions.push(`(website_status != 'No Website' AND website IS NOT NULL AND website != '')`);
  }

  if (email_status) {
    params.push(email_status);
    conditions.push(`email_status = $${params.length}`);
  }

  if (lead_status) {
    params.push(lead_status);
    conditions.push(`lead_status = $${params.length}`);
  }

  if (lead_source) {
    params.push(lead_source);
    conditions.push(`lead_source = $${params.length}`);
  }

  if (data_quality) {
    params.push(data_quality);
    conditions.push(`data_quality = $${params.length}`);
  }

  if (city) {
    params.push(city);
    conditions.push(`city = $${params.length}`);
  }

  if (state) {
    params.push(state);
    conditions.push(`state = $${params.length}`);
  }

  if (country) {
    params.push(country);
    conditions.push(`country = $${params.length}`);
  }

  if (industry) {
    params.push(industry);
    conditions.push(`industry = $${params.length}`);
  }

  if (needs_verification !== undefined && needs_verification !== '') {
    const isNeed = needs_verification === 'true' || needs_verification === true || needs_verification === '1';
    conditions.push(isNeed ? `(needs_verification = 1 OR needs_verification = true)` : `(needs_verification = 0 OR needs_verification = false OR needs_verification IS NULL)`);
  }

  if (is_verified !== undefined && is_verified !== '') {
    const isVer = is_verified === 'true' || is_verified === true || is_verified === '1';
    conditions.push(isVer ? `(is_verified = 1 OR is_verified = true)` : `(is_verified = 0 OR is_verified = false OR is_verified IS NULL)`);
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  const sql = `SELECT * FROM leads ${whereClause} ORDER BY created_at DESC`;
  const result = await query(sql, params);
  return result.rows;
};

/**
 * GET or POST /api/export/excel
 * Export leads to genuine Black & White formatted .xlsx
 */
const handleExcelExport = async (req, res) => {
  try {
    const leads = await fetchLeadsForExport(req.body, req.query);
    const excelBuffer = generateBlackWhiteExcel(leads);

    const filename = `TechvionNova_Leads_${new Date().toISOString().split('T')[0]}.xlsx`;

    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    return res.send(excelBuffer);
  } catch (err) {
    console.error('Error in Excel export:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
};

/**
 * GET or POST /api/export/csv
 * Export leads to clean RFC 4180 UTF-8 CSV
 */
const handleCsvExport = async (req, res) => {
  try {
    const leads = await fetchLeadsForExport(req.body, req.query);
    const csvBuffer = generateCleanCSV(leads);

    const filename = `TechvionNova_Leads_${new Date().toISOString().split('T')[0]}.csv`;

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    return res.send(csvBuffer);
  } catch (err) {
    console.error('Error in CSV export:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
};

router.get('/excel', handleExcelExport);
router.post('/excel', handleExcelExport);

router.get('/csv', handleCsvExport);
router.post('/csv', handleCsvExport);

module.exports = router;
