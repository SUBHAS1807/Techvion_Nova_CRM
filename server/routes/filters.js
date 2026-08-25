const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

/**
 * GET /api/filters/options
 * Returns distinct filter options populated from current database
 */
router.get('/options', async (req, res) => {
  try {
    const citiesRes = await query("SELECT DISTINCT city FROM leads WHERE city != '' AND city IS NOT NULL ORDER BY city ASC");
    const statesRes = await query("SELECT DISTINCT state FROM leads WHERE state != '' AND state IS NOT NULL ORDER BY state ASC");
    const countriesRes = await query("SELECT DISTINCT country FROM leads WHERE country != '' AND country IS NOT NULL ORDER BY country ASC");
    const industriesRes = await query("SELECT DISTINCT industry FROM leads WHERE industry != '' AND industry IS NOT NULL ORDER BY industry ASC");
    const sourcesRes = await query("SELECT DISTINCT lead_source FROM leads WHERE lead_source != '' AND lead_source IS NOT NULL ORDER BY lead_source ASC");

    return res.json({
      success: true,
      cities: citiesRes.rows.map(r => r.city),
      states: statesRes.rows.map(r => r.state),
      countries: countriesRes.rows.map(r => r.country),
      industries: industriesRes.rows.map(r => r.industry),
      sources: sourcesRes.rows.map(r => r.lead_source),
      statuses: [
        'New',
        'Verified',
        'Contacted',
        'Follow-up',
        'Interested',
        'Meeting',
        'Proposal Sent',
        'Converted',
        'Not Interested',
        'Closed',
      ],
      websiteStatuses: [
        'No Website',
        'Working',
        'Broken',
        'Redirect',
        'Poor Website',
        'Under Construction',
        'Unknown',
        'Needs Verification',
      ],
      emailStatuses: [
        'Valid',
        'Invalid',
        'Missing',
        'Risky',
        'Not Verified',
      ],
      dataQualities: ['High', 'Medium', 'Low'],
    });
  } catch (err) {
    console.error('Error fetching filter options:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
