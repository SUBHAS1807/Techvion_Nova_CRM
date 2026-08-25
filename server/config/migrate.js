const { query } = require('./database');

const migrate = async () => {
  console.log('🔄 Running database migrations...');
  try {
    // Create leads table
    await query(`
      CREATE TABLE IF NOT EXISTS leads (
        lead_id VARCHAR(50) PRIMARY KEY,
        business_name VARCHAR(255) NOT NULL,
        industry VARCHAR(100) DEFAULT '',
        email VARCHAR(255) DEFAULT '',
        email_status VARCHAR(50) DEFAULT 'Not Verified',
        phone VARCHAR(100) DEFAULT '',
        website VARCHAR(500) DEFAULT '',
        website_status VARCHAR(50) DEFAULT 'Unknown',
        address TEXT DEFAULT '',
        city VARCHAR(100) DEFAULT '',
        state VARCHAR(100) DEFAULT '',
        country VARCHAR(100) DEFAULT '',
        postal_code VARCHAR(50) DEFAULT '',
        lead_status VARCHAR(50) DEFAULT 'New',
        lead_source VARCHAR(100) DEFAULT 'Manual',
        contact_person VARCHAR(255) DEFAULT '',
        notes TEXT DEFAULT '',
        data_quality VARCHAR(20) DEFAULT 'Low',
        is_verified BOOLEAN DEFAULT FALSE,
        needs_verification BOOLEAN DEFAULT FALSE,
        location_verified BOOLEAN DEFAULT TRUE,
        verification_reason TEXT DEFAULT '',
        last_contacted TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // Create indexes for blazing-fast filtering, search, and sorting
    const indexes = [
      'CREATE INDEX IF NOT EXISTS idx_leads_business_name ON leads(business_name);',
      'CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);',
      'CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);',
      'CREATE INDEX IF NOT EXISTS idx_leads_website ON leads(website);',
      'CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city);',
      'CREATE INDEX IF NOT EXISTS idx_leads_state ON leads(state);',
      'CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country);',
      'CREATE INDEX IF NOT EXISTS idx_leads_website_status ON leads(website_status);',
      'CREATE INDEX IF NOT EXISTS idx_leads_email_status ON leads(email_status);',
      'CREATE INDEX IF NOT EXISTS idx_leads_lead_status ON leads(lead_status);',
      'CREATE INDEX IF NOT EXISTS idx_leads_lead_source ON leads(lead_source);',
      'CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads(industry);',
      'CREATE INDEX IF NOT EXISTS idx_leads_data_quality ON leads(data_quality);',
      'CREATE INDEX IF NOT EXISTS idx_leads_needs_verification ON leads(needs_verification);',
      'CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);',
    ];

    for (const idx of indexes) {
      await query(idx);
    }

    console.log('✅ Database migration completed successfully');
  } catch (err) {
    console.error('❌ Migration failed:', err);
    throw err;
  }
};

if (require.main === module) {
  migrate()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

module.exports = migrate;
