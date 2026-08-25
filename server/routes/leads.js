const express = require('express');
const router = express.Router();
const { query } = require('../config/database');
const { cleanAndEnrichLead, calculateDataQuality } = require('../utils/dataCleaner');
const { generateLeadId } = require('../utils/helpers');

/**
 * GET /api/leads
 * Server-side paginated, searchable, multi-filtered lead listing
 */
router.get('/', async (req, res) => {
  try {
    const {
      page = 1,
      limit = 25,
      search = '',
      sortBy = 'created_at',
      sortOrder = 'DESC',
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
    } = req.query;

    const pageNum = Math.max(1, parseInt(page, 10));
    const limitNum = Math.min(500, Math.max(5, parseInt(limit, 10)));
    const offset = (pageNum - 1) * limitNum;

    // Build WHERE clauses dynamically
    const conditions = [];
    const params = [];

    // Search across multiple fields
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

    // Filter by website status
    if (website_status) {
      params.push(website_status);
      conditions.push(`website_status = $${params.length}`);
    }

    // Filter by has_website boolean/string
    if (has_website === 'no' || has_website === 'false') {
      conditions.push(`(website_status = 'No Website' OR website IS NULL OR website = '')`);
    } else if (has_website === 'yes' || has_website === 'true') {
      conditions.push(`(website_status != 'No Website' AND website IS NOT NULL AND website != '')`);
    }

    // Filter by email status
    if (email_status) {
      params.push(email_status);
      conditions.push(`email_status = $${params.length}`);
    }

    // Filter by lead status
    if (lead_status) {
      params.push(lead_status);
      conditions.push(`lead_status = $${params.length}`);
    }

    // Filter by lead source
    if (lead_source) {
      params.push(lead_source);
      conditions.push(`lead_source = $${params.length}`);
    }

    // Filter by data quality
    if (data_quality) {
      params.push(data_quality);
      conditions.push(`data_quality = $${params.length}`);
    }

    // Filter by city
    if (city) {
      params.push(city);
      conditions.push(`city = $${params.length}`);
    }

    // Filter by state
    if (state) {
      params.push(state);
      conditions.push(`state = $${params.length}`);
    }

    // Filter by country
    if (country) {
      params.push(country);
      conditions.push(`country = $${params.length}`);
    }

    // Filter by industry
    if (industry) {
      params.push(industry);
      conditions.push(`industry = $${params.length}`);
    }

    // Filter by needs_verification
    if (needs_verification !== undefined && needs_verification !== '') {
      const isNeed = needs_verification === 'true' || needs_verification === true || needs_verification === '1';
      conditions.push(isNeed ? `(needs_verification = 1 OR needs_verification = true)` : `(needs_verification = 0 OR needs_verification = false OR needs_verification IS NULL)`);
    }

    // Filter by is_verified
    if (is_verified !== undefined && is_verified !== '') {
      const isVer = is_verified === 'true' || is_verified === true || is_verified === '1';
      conditions.push(isVer ? `(is_verified = 1 OR is_verified = true)` : `(is_verified = 0 OR is_verified = false OR is_verified IS NULL)`);
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

    // Sanitize sort parameters
    const allowedSortCols = [
      'lead_id', 'business_name', 'email', 'phone', 'website', 'website_status',
      'city', 'state', 'country', 'industry', 'lead_status', 'lead_source',
      'data_quality', 'is_verified', 'needs_verification', 'last_contacted', 'created_at', 'updated_at'
    ];
    const safeSortCol = allowedSortCols.includes(sortBy) ? sortBy : 'created_at';
    const safeSortOrder = sortOrder && sortOrder.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';

    // Get total count for pagination
    const countSql = `SELECT COUNT(*) as total FROM leads ${whereClause}`;
    const countResult = await query(countSql, params);
    const totalRecords = parseInt(countResult.rows[0]?.total || 0, 10);

    // Get page records
    const recordsSql = `
      SELECT * FROM leads 
      ${whereClause} 
      ORDER BY ${safeSortCol} ${safeSortOrder} 
      LIMIT ${limitNum} OFFSET ${offset}
    `;
    const recordsResult = await query(recordsSql, params);

    const totalPages = Math.ceil(totalRecords / limitNum);

    return res.json({
      success: true,
      data: recordsResult.rows,
      pagination: {
        page: pageNum,
        limit: limitNum,
        totalRecords,
        totalPages,
        hasPrevPage: pageNum > 1,
        hasNextPage: pageNum < totalPages,
      },
    });
  } catch (err) {
    console.error('Error in GET /api/leads:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * GET /api/leads/:id
 * Get single lead details
 */
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query('SELECT * FROM leads WHERE lead_id = $1', [id]);
    if (!result.rows || result.rows.length === 0) {
      return res.status(404).json({ success: false, error: 'Lead not found' });
    }
    return res.json({ success: true, data: result.rows[0] });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * POST /api/leads
 * Create single new lead with automated cleaning and validation
 */
router.post('/', async (req, res) => {
  try {
    const cleaned = cleanAndEnrichLead(req.body);
    const lead_id = await generateLeadId();

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
      lead_id,
      cleaned.business_name,
      cleaned.industry,
      cleaned.email,
      cleaned.email_status,
      cleaned.phone,
      cleaned.website,
      cleaned.website_status,
      cleaned.address,
      cleaned.city,
      cleaned.state,
      cleaned.country,
      cleaned.postal_code,
      cleaned.lead_status,
      cleaned.lead_source,
      cleaned.contact_person,
      cleaned.notes,
      cleaned.data_quality,
      cleaned.is_verified ? 1 : 0,
      cleaned.needs_verification ? 1 : 0,
      cleaned.location_verified ? 1 : 0,
      cleaned.verification_reason,
      cleaned.last_contacted,
    ];

    await query(insertSql, params);
    const created = await query('SELECT * FROM leads WHERE lead_id = $1', [lead_id]);

    return res.status(201).json({ success: true, data: created.rows[0] });
  } catch (err) {
    console.error('Error creating lead:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * PUT /api/leads/:id
 * Update an existing lead record
 */
router.put('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const existing = await query('SELECT * FROM leads WHERE lead_id = $1', [id]);
    if (!existing.rows || existing.rows.length === 0) {
      return res.status(404).json({ success: false, error: 'Lead not found' });
    }

    const merged = { ...existing.rows[0], ...req.body };
    const cleaned = cleanAndEnrichLead(merged);

    // If manually updated or verified by user
    if (req.body.is_verified !== undefined) {
      cleaned.is_verified = req.body.is_verified;
      if (cleaned.is_verified) {
        cleaned.needs_verification = false;
      }
    }

    if (req.body.needs_verification !== undefined) {
      cleaned.needs_verification = req.body.needs_verification;
    }

    cleaned.data_quality = calculateDataQuality(cleaned);

    const updateSql = `
      UPDATE leads SET
        business_name = $1,
        industry = $2,
        email = $3,
        email_status = $4,
        phone = $5,
        website = $6,
        website_status = $7,
        address = $8,
        city = $9,
        state = $10,
        country = $11,
        postal_code = $12,
        lead_status = $13,
        lead_source = $14,
        contact_person = $15,
        notes = $16,
        data_quality = $17,
        is_verified = $18,
        needs_verification = $19,
        location_verified = $20,
        verification_reason = $21,
        last_contacted = $22,
        updated_at = CURRENT_TIMESTAMP
      WHERE lead_id = $23
    `;

    const params = [
      cleaned.business_name,
      cleaned.industry,
      cleaned.email,
      cleaned.email_status,
      cleaned.phone,
      cleaned.website,
      cleaned.website_status,
      cleaned.address,
      cleaned.city,
      cleaned.state,
      cleaned.country,
      cleaned.postal_code,
      cleaned.lead_status,
      cleaned.lead_source,
      cleaned.contact_person,
      cleaned.notes,
      cleaned.data_quality,
      cleaned.is_verified ? 1 : 0,
      cleaned.needs_verification ? 1 : 0,
      cleaned.location_verified ? 1 : 0,
      cleaned.verification_reason,
      cleaned.last_contacted,
      id,
    ];

    await query(updateSql, params);
    const updated = await query('SELECT * FROM leads WHERE lead_id = $1', [id]);

    return res.json({ success: true, data: updated.rows[0] });
  } catch (err) {
    console.error('Error updating lead:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * DELETE /api/leads/:id
 * Delete a single lead
 */
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query('DELETE FROM leads WHERE lead_id = $1', [id]);
    return res.json({ success: true, message: 'Lead deleted successfully' });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * POST /api/leads/bulk-action
 * Perform actions on multiple selected leads (status, source, verify, note, delete)
 */
router.post('/bulk-action', async (req, res) => {
  try {
    const { action, lead_ids, payload } = req.body;

    if (!action || !lead_ids || !Array.isArray(lead_ids) || lead_ids.length === 0) {
      return res.status(400).json({ success: false, error: 'Invalid bulk action parameters' });
    }

    const placeholders = lead_ids.map((_, idx) => `$${idx + 1}`).join(',');

    if (action === 'delete') {
      await query(`DELETE FROM leads WHERE lead_id IN (${placeholders})`, lead_ids);
      return res.json({ success: true, message: `Successfully deleted ${lead_ids.length} leads` });
    }

    if (action === 'change_status') {
      const newStatus = payload?.status || 'Contacted';
      const sql = `UPDATE leads SET lead_status = $1, updated_at = CURRENT_TIMESTAMP WHERE lead_id IN (${placeholders.split(',').map((_, i) => `$${i + 2}`).join(',')})`;
      await query(sql, [newStatus, ...lead_ids]);
      return res.json({ success: true, message: `Updated status to "${newStatus}" for ${lead_ids.length} leads` });
    }

    if (action === 'change_source') {
      const newSource = payload?.source || 'Manual';
      const sql = `UPDATE leads SET lead_source = $1, updated_at = CURRENT_TIMESTAMP WHERE lead_id IN (${placeholders.split(',').map((_, i) => `$${i + 2}`).join(',')})`;
      await query(sql, [newSource, ...lead_ids]);
      return res.json({ success: true, message: `Updated source to "${newSource}" for ${lead_ids.length} leads` });
    }

    if (action === 'mark_verified') {
      const sql = `UPDATE leads SET is_verified = 1, needs_verification = 0, data_quality = 'High', updated_at = CURRENT_TIMESTAMP WHERE lead_id IN (${placeholders})`;
      await query(sql, lead_ids);
      return res.json({ success: true, message: `Marked ${lead_ids.length} leads as Verified` });
    }

    if (action === 'add_note') {
      const noteText = payload?.note || '';
      if (!noteText.trim()) {
        return res.status(400).json({ success: false, error: 'Note text cannot be empty' });
      }

      // Append note to existing notes
      for (const id of lead_ids) {
        const row = await query('SELECT notes FROM leads WHERE lead_id = $1', [id]);
        const existingNotes = row.rows[0]?.notes || '';
        const timestamp = new Date().toISOString().split('T')[0];
        const updatedNotes = existingNotes ? `${existingNotes}\n[${timestamp}] ${noteText}` : `[${timestamp}] ${noteText}`;
        await query('UPDATE leads SET notes = $1, updated_at = CURRENT_TIMESTAMP WHERE lead_id = $2', [updatedNotes, id]);
      }
      return res.json({ success: true, message: `Note appended to ${lead_ids.length} leads` });
    }

    return res.status(400).json({ success: false, error: `Unknown action: ${action}` });
  } catch (err) {
    console.error('Error in bulk action:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
