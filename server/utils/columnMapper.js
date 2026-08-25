/**
 * Intelligent Column Detection & Auto-Mapping for CRM Import
 */

const STANDARD_CRM_FIELDS = [
  { key: 'business_name', label: 'Business Name', required: true },
  { key: 'email', label: 'Email', required: false },
  { key: 'email_status', label: 'Email Status', required: false },
  { key: 'phone', label: 'Phone', required: false },
  { key: 'website', label: 'Website', required: false },
  { key: 'website_status', label: 'Website Status', required: false },
  { key: 'city', label: 'City', required: false },
  { key: 'state', label: 'State / Province', required: false },
  { key: 'country', label: 'Country', required: false },
  { key: 'industry', label: 'Industry / Category', required: false },
  { key: 'lead_status', label: 'Lead Status', required: false },
  { key: 'lead_source', label: 'Lead Source', required: false },
  { key: 'contact_person', label: 'Contact Person / Owner', required: false },
  { key: 'address', label: 'Street Address', required: false },
  { key: 'postal_code', label: 'Postal / Zip Code', required: false },
  { key: 'notes', label: 'Notes / Remarks', required: false },
  { key: 'last_contacted', label: 'Last Contacted Date', required: false },
];

const COLUMN_ALIASES = {
  business_name: [
    'business name', 'business_name', 'businessname', 'company', 'company name',
    'company_name', 'companyname', 'business', 'firm', 'organisation',
    'organization', 'establishment', 'shop name', 'store name', 'brand',
    'place name', 'place_name', 'merchant', 'vendor',
  ],
  email_status: [
    'email status', 'email_status', 'emailstatus', 'e-mail status',
  ],
  email: [
    'email', 'e-mail', 'email address', 'emailaddress', 'mail', 'contact email',
    'business email', 'work email', 'primary email', 'e-mail address', 'electronic mail',
  ],
  phone: [
    'phone', 'phone number', 'phonenumber', 'mobile', 'mobile number', 'cell',
    'telephone', 'tel', 'contact number', 'cellphone', 'phone no', 'phone_no',
    'mobile no', 'contact', 'call',
  ],
  website_status: [
    'website status', 'website_status', 'web status', 'site status',
  ],
  website: [
    'website', 'web', 'url', 'site', 'web address', 'webpage', 'website url',
    'website_url', 'websiteurl', 'domain', 'business website', 'current website',
    'link', 'homepage', 'web_link',
  ],
  city: [
    'city', 'town', 'location', 'area', 'district', 'municipality', 'city/town',
  ],
  state: [
    'state', 'state/province', 'state_province', 'stateprovince', 'province',
    'region', 'territory', 'state name',
  ],
  country: [
    'country', 'country name', 'country_name', 'nation', 'country code',
  ],
  industry: [
    'industry', 'business type', 'business_type', 'businesstype', 'type',
    'category', 'sector', 'niche', 'business category', 'segment', 'primary category',
  ],
  lead_status: [
    'lead status', 'lead_status', 'leadstatus', 'status', 'outreach status',
    'crm status', 'stage', 'pipeline stage',
  ],
  lead_source: [
    'lead source', 'lead_source', 'leadsource', 'source', 'origin',
    'how found', 'referral source', 'channel', 'acquired via',
  ],
  contact_person: [
    'contact person', 'contact_person', 'contactperson', 'owner', 'owner name',
    'owner_name', 'manager', 'person', 'contact name', 'decision maker', 'full name',
  ],
  address: [
    'address', 'full address', 'street', 'street address', 'location address',
    'business address', 'formatted address', 'postal address',
  ],
  postal_code: [
    'postal code', 'postal_code', 'postalcode', 'zip', 'zip code', 'pincode',
    'pin code', 'postcode', 'postal',
  ],
  notes: [
    'notes', 'remarks', 'comments', 'description', 'details', 'note',
    'additional info', 'additional information', 'extra',
  ],
  last_contacted: [
    'last contacted', 'last_contacted', 'contacted date', 'last outreach',
  ],
};

/**
 * Automatically inspects raw file header row and assigns best matching CRM field
 */
const detectColumns = (headers) => {
  const mapping = {};
  const usedFields = new Set();

  // Pass 1: Exact matches first
  for (const rawHeader of headers) {
    const cleanHeader = String(rawHeader || '').trim();
    if (!cleanHeader) continue;
    const normalized = cleanHeader.toLowerCase().replace(/[\s_-]+/g, ' ').trim();

    for (const [targetField, aliases] of Object.entries(COLUMN_ALIASES)) {
      if (usedFields.has(targetField)) continue;
      for (const alias of aliases) {
        if (normalized === alias || normalized === alias.replace(/[\s_-]+/g, ' ')) {
          mapping[cleanHeader] = targetField;
          usedFields.add(targetField);
          break;
        }
      }
      if (mapping[cleanHeader]) break;
    }
  }

  // Pass 2: Fuzzy / Substring matches for unmapped headers
  for (const rawHeader of headers) {
    const cleanHeader = String(rawHeader || '').trim();
    if (!cleanHeader || mapping[cleanHeader]) continue;
    const normalized = cleanHeader.toLowerCase().replace(/[\s_-]+/g, ' ').trim();

    for (const [targetField, aliases] of Object.entries(COLUMN_ALIASES)) {
      if (usedFields.has(targetField)) continue;
      for (const alias of aliases) {
        if (normalized.includes(alias) || alias.includes(normalized)) {
          mapping[cleanHeader] = targetField;
          usedFields.add(targetField);
          break;
        }
      }
      if (mapping[cleanHeader]) break;
    }

    if (!mapping[cleanHeader]) {
      mapping[cleanHeader] = 'ignore';
    }
  }

  return mapping;
};

module.exports = {
  STANDARD_CRM_FIELDS,
  COLUMN_ALIASES,
  detectColumns,
};
