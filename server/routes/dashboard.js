const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

/**
 * GET /api/dashboard/stats
 * Aggregate key CRM metrics for Dashboard cards
 */
router.get('/stats', async (req, res) => {
  try {
    // 1. Total Leads
    const totalResult = await query('SELECT COUNT(*) as count FROM leads');
    const totalLeads = parseInt(totalResult.rows[0]?.count || 0, 10);

    // 2. Valid Emails
    const validEmailsResult = await query("SELECT COUNT(*) as count FROM leads WHERE email_status = 'Valid'");
    const validEmails = parseInt(validEmailsResult.rows[0]?.count || 0, 10);

    // 3. Leads Without Website (Key target for web dev)
    const noWebsiteResult = await query("SELECT COUNT(*) as count FROM leads WHERE website_status = 'No Website' OR website IS NULL OR website = ''");
    const leadsWithoutWebsite = parseInt(noWebsiteResult.rows[0]?.count || 0, 10);

    // 4. Leads With Website
    const withWebsiteResult = await query("SELECT COUNT(*) as count FROM leads WHERE website_status != 'No Website' AND website IS NOT NULL AND website != ''");
    const leadsWithWebsite = parseInt(withWebsiteResult.rows[0]?.count || 0, 10);

    // 5. Verified Leads
    const verifiedResult = await query("SELECT COUNT(*) as count FROM leads WHERE is_verified = 1 OR is_verified = true");
    const verifiedLeads = parseInt(verifiedResult.rows[0]?.count || 0, 10);

    // 6. Leads Needing Verification
    const needingVerificationResult = await query("SELECT COUNT(*) as count FROM leads WHERE needs_verification = 1 OR needs_verification = true");
    const leadsNeedingVerification = parseInt(needingVerificationResult.rows[0]?.count || 0, 10);

    // 7. Contacted
    const contactedResult = await query("SELECT COUNT(*) as count FROM leads WHERE lead_status = 'Contacted'");
    const contacted = parseInt(contactedResult.rows[0]?.count || 0, 10);

    // 8. Interested
    const interestedResult = await query("SELECT COUNT(*) as count FROM leads WHERE lead_status = 'Interested'");
    const interested = parseInt(interestedResult.rows[0]?.count || 0, 10);

    // 9. Converted
    const convertedResult = await query("SELECT COUNT(*) as count FROM leads WHERE lead_status = 'Converted'");
    const converted = parseInt(convertedResult.rows[0]?.count || 0, 10);

    // Data Quality breakdown
    const qualityResult = await query('SELECT data_quality, COUNT(*) as count FROM leads GROUP BY data_quality');
    const qualityBreakdown = { High: 0, Medium: 0, Low: 0 };
    qualityResult.rows.forEach(r => {
      if (r.data_quality) qualityBreakdown[r.data_quality] = parseInt(r.count, 10);
    });

    // Lead Status breakdown
    const statusResult = await query('SELECT lead_status, COUNT(*) as count FROM leads GROUP BY lead_status ORDER BY count DESC');
    const statusBreakdown = statusResult.rows.map(r => ({ status: r.lead_status || 'Unknown', count: parseInt(r.count, 10) }));

    // Lead Source breakdown
    const sourceResult = await query('SELECT lead_source, COUNT(*) as count FROM leads GROUP BY lead_source ORDER BY count DESC');
    const sourceBreakdown = sourceResult.rows.map(r => ({ source: r.lead_source || 'Manual', count: parseInt(r.count, 10) }));

    // Website Opportunities breakdown (No Website, Broken, Poor)
    const oppResult = await query(`
      SELECT website_status, COUNT(*) as count 
      FROM leads 
      WHERE website_status IN ('No Website', 'Broken', 'Poor Website', 'Under Construction', 'Unknown')
      GROUP BY website_status
    `);
    const websiteOpportunities = oppResult.rows.map(r => ({ status: r.website_status, count: parseInt(r.count, 10) }));

    // Recent 5 leads
    const recentResult = await query('SELECT * FROM leads ORDER BY created_at DESC LIMIT 5');

    return res.json({
      success: true,
      stats: {
        totalLeads,
        validEmails,
        leadsWithoutWebsite,
        leadsWithWebsite,
        verifiedLeads,
        leadsNeedingVerification,
        contacted,
        interested,
        converted,
      },
      qualityBreakdown,
      statusBreakdown,
      sourceBreakdown,
      websiteOpportunities,
      recentLeads: recentResult.rows,
    });
  } catch (err) {
    console.error('Error fetching dashboard stats:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

module.exports = router;
