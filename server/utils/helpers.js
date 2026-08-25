const { query } = require('../config/database');

/**
 * Generates next sequential CRM lead ID (TVN-000001, TVN-000002, ...)
 */
const generateLeadId = async () => {
  const result = await query('SELECT lead_id FROM leads ORDER BY lead_id DESC LIMIT 1');
  if (!result.rows || result.rows.length === 0) return 'TVN-000001';
  
  const lastId = result.rows[0].lead_id;
  const match = lastId.match(/TVN-(\d+)/);
  if (match) {
    const nextNum = parseInt(match[1], 10) + 1;
    return `TVN-${String(nextNum).padStart(6, '0')}`;
  }
  return `TVN-${Date.now().toString().slice(-6)}`;
};

/**
 * Generates an array of batch IDs for high-volume imports
 */
const generateBatchLeadIds = async (count) => {
  const result = await query('SELECT lead_id FROM leads ORDER BY lead_id DESC LIMIT 1');
  let currentNum = 0;
  if (result.rows && result.rows.length > 0) {
    const match = result.rows[0].lead_id.match(/TVN-(\d+)/);
    if (match) {
      currentNum = parseInt(match[1], 10);
    }
  }

  const ids = [];
  for (let i = 1; i <= count; i++) {
    ids.push(`TVN-${String(currentNum + i).padStart(6, '0')}`);
  }
  return ids;
};

module.exports = {
  generateLeadId,
  generateBatchLeadIds,
};
