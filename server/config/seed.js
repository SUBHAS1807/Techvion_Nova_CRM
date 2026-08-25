const { query } = require('./database');
const { cleanAndEnrichLead } = require('../utils/dataCleaner');

const SEED_DATA = [
  {
    lead_id: 'TVN-000001',
    business_name: 'Blue Tokai Coffee Roasters',
    industry: 'Cafe & Roastery',
    email: 'info@bluetokaicoffee.com',
    phone: '+91 98200 12345',
    website: 'https://bluetokaicoffee.com',
    address: 'Park Street, Near St. Xavier College',
    city: 'Kolkata',
    state: 'West Bengal',
    country: 'India',
    postal_code: '700016',
    lead_status: 'New',
    lead_source: 'Google Maps',
    contact_person: 'Matt Chitharanjan',
    notes: 'Premium specialty coffee brand in Kolkata.',
  },
  {
    lead_id: 'TVN-000002',
    business_name: 'Flurys Heritage Bakery & Tearoom',
    industry: 'Bakery & Confectionery',
    email: 'contact@flurysindia.com',
    phone: '+91 33 4000 7822',
    website: 'https://flurys.com',
    address: '18A, Park Street',
    city: 'Kolkata',
    state: 'West Bengal',
    country: 'India',
    postal_code: '700071',
    lead_status: 'Contacted',
    lead_source: 'Google Search',
    contact_person: 'Rajiv Sengupta',
    notes: 'Historic European tearoom established in 1927.',
  },
  {
    lead_id: 'TVN-000003',
    business_name: 'Heritage Handlooms & Textiles',
    industry: 'Handicrafts & Apparel',
    email: '',
    phone: '+91 94330 88211',
    website: '',
    address: 'Gariahat Market, Stall #42',
    city: 'Kolkata',
    state: 'West Bengal',
    country: 'India',
    postal_code: '700019',
    lead_status: 'New',
    lead_source: 'Google Maps',
    contact_person: 'Subrata Roy',
    notes: 'Prime prospect for website development. Currently has NO online store.',
  },
  {
    lead_id: 'TVN-000004',
    business_name: 'Apex Dental Care & Implant Center',
    industry: 'Healthcare & Dental',
    email: 'dr.sneha.apex@gmail.com',
    phone: '+91 98311 55677',
    website: 'http://apexdentalkol.com',
    website_status: 'Broken',
    address: 'Salt Lake Sector 1, Block BD',
    city: 'Kolkata',
    state: 'West Bengal',
    country: 'India',
    postal_code: '700064',
    lead_status: 'Interested',
    lead_source: 'Google Maps',
    contact_person: 'Dr. Sneha Chatterjee',
    notes: 'Current website returns 404 error. Looking to redesign dental clinic website.',
  },
  {
    lead_id: 'TVN-000005',
    business_name: 'Royal Bengal Sweets & Savouries',
    industry: 'Food & Sweets',
    email: '',
    phone: '+91 91234 56789',
    website: '',
    address: 'Shyambazar Five Point Crossing',
    city: 'Kolkata',
    state: 'West Bengal',
    country: 'India',
    postal_code: '700004',
    lead_status: 'New',
    lead_source: 'CSV Import',
    contact_person: 'Anirban Mukherjee',
    notes: 'Traditional Bengali sweet shop seeking e-commerce delivery website.',
  },
  {
    lead_id: 'TVN-000006',
    business_name: 'Roastery Coffee House',
    industry: 'Cafe & Restaurant',
    email: 'roastery.kolkata@gmail.com',
    phone: '+91 73828 77777',
    website: 'https://roasterycoffee.co.in',
    address: 'South City Extension',
    city: 'Kolkata',
    state: 'Telangana', // Intentional mismatch for location validation testing
    country: 'India',
    postal_code: '700068',
    lead_status: 'Follow-up',
    lead_source: 'Google Maps',
    contact_person: 'Nishant Sinha',
    notes: 'Original flagship in Hyderabad; Kolkata branch detected with state mismatch.',
  },
  {
    lead_id: 'TVN-000007',
    business_name: 'Silver Oak Architecture & Interiors',
    industry: 'Architecture & Design',
    email: 'studio@silveroakarch.in',
    phone: '+91 98450 99882',
    website: 'https://silveroakarch.in',
    address: 'Indiranagar 100ft Road',
    city: 'Bengaluru',
    state: 'Karnataka',
    country: 'India',
    postal_code: '560038',
    lead_status: 'Proposal Sent',
    lead_source: 'LinkedIn',
    contact_person: 'Arjun Nambiar',
    notes: 'High-end architectural firm requiring portfolio redesign.',
  },
  {
    lead_id: 'TVN-000008',
    business_name: 'Metro Fitness Gym & Crossfit',
    industry: 'Fitness & Health',
    email: '',
    phone: '+91 98190 44332',
    website: '',
    address: 'Bandra West, Hill Road',
    city: 'Mumbai',
    state: 'Maharashtra',
    country: 'India',
    postal_code: '400050',
    lead_status: 'Contacted',
    lead_source: 'Google Maps',
    contact_person: 'Vikram Salgaonkar',
    notes: 'Gym chain branch with no web presence; needs booking website.',
  },
  {
    lead_id: 'TVN-000009',
    business_name: 'Green Leaf Organic Groceries',
    industry: 'Retail & Grocery',
    email: 'info@greenleafdaily.com',
    phone: '+91 97112 33445',
    website: 'https://greenleafdaily.com',
    address: 'DLF Phase 4',
    city: 'Noida',
    state: 'Uttar Pradesh',
    country: 'India',
    postal_code: '201301',
    lead_status: 'Converted',
    lead_source: 'Website',
    contact_person: 'Pooja Agarwal',
    notes: 'Converted customer. Ongoing website maintenance retainer.',
  },
  {
    lead_id: 'TVN-000010',
    business_name: 'Horizon Logistics & Cargo',
    industry: 'Logistics & Supply Chain',
    email: 'contact@horizoncargo.co',
    phone: '+91 98980 11223',
    website: 'http://horizoncargo.co',
    website_status: 'Poor Website',
    address: 'Sarkhej Gandhinagar Highway',
    city: 'Ahmedabad',
    state: 'Gujarat',
    country: 'India',
    postal_code: '380054',
    lead_status: 'Meeting',
    lead_source: 'Manual',
    contact_person: 'Dharmesh Patel',
    notes: 'Current website is outdated, non-responsive, and insecure (HTTP).',
  }
];

const seedDatabase = async () => {
  try {
    const existing = await query('SELECT COUNT(*) as count FROM leads');
    if (parseInt(existing.rows[0]?.count || 0, 10) > 0) {
      console.log(`ℹ️ Database already contains ${existing.rows[0].count} leads, skipping seed.`);
      return;
    }

    console.log('🌱 Seeding database with realistic initial CRM leads...');

    for (const raw of SEED_DATA) {
      const cleaned = cleanAndEnrichLead(raw);
      // Preserve explicit test conditions like the location mismatch in lead #6
      if (raw.lead_id === 'TVN-000006') {
        cleaned.state = raw.state;
        cleaned.needs_verification = true;
        cleaned.location_verified = false;
        cleaned.verification_reason = 'Possible location mismatch: Kolkata is typically in West Bengal, but state is listed as Telangana.';
      }
      if (raw.website_status) {
        cleaned.website_status = raw.website_status;
      }

      const insertSql = `
        INSERT INTO leads (
          lead_id, business_name, industry, email, email_status, phone, website,
          website_status, address, city, state, country, postal_code, lead_status,
          lead_source, contact_person, notes, data_quality, is_verified,
          needs_verification, location_verified, verification_reason,
          created_at, updated_at
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
          $15, $16, $17, $18, $19, $20, $21, $22, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
      `;

      await query(insertSql, [
        raw.lead_id,
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
      ]);
    }

    console.log(`✅ Seeded ${SEED_DATA.length} initial CRM leads successfully.`);
  } catch (err) {
    console.error('❌ Error seeding database:', err);
  }
};

if (require.main === module) {
  seedDatabase()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}

module.exports = seedDatabase;
