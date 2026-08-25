/**
 * Data Cleaning, Location Validation, and Quality Engine for Lead CRM
 */

// Well-known Indian & Global City to State/Province mapping for mismatch detection
const CITY_STATE_KNOWLEDGE = {
  // India
  'kolkata': { state: 'West Bengal', aliases: ['wb', 'west bengal', 'calcutta'] },
  'howrah': { state: 'West Bengal', aliases: ['wb', 'west bengal'] },
  'siliguri': { state: 'West Bengal', aliases: ['wb', 'west bengal'] },
  'mumbai': { state: 'Maharashtra', aliases: ['mh', 'maharashtra', 'bombay'] },
  'pune': { state: 'Maharashtra', aliases: ['mh', 'maharashtra'] },
  'nagpur': { state: 'Maharashtra', aliases: ['mh', 'maharashtra'] },
  'nashik': { state: 'Maharashtra', aliases: ['mh', 'maharashtra'] },
  'delhi': { state: 'Delhi', aliases: ['dl', 'delhi', 'nct', 'new delhi'] },
  'new delhi': { state: 'Delhi', aliases: ['dl', 'delhi', 'nct', 'new delhi'] },
  'bengaluru': { state: 'Karnataka', aliases: ['ka', 'karnataka', 'bangalore'] },
  'bangalore': { state: 'Karnataka', aliases: ['ka', 'karnataka', 'bengaluru'] },
  'mysore': { state: 'Karnataka', aliases: ['ka', 'karnataka', 'mysuru'] },
  'hyderabad': { state: 'Telangana', aliases: ['tg', 'ts', 'telangana'] },
  'secunderabad': { state: 'Telangana', aliases: ['tg', 'ts', 'telangana'] },
  'chennai': { state: 'Tamil Nadu', aliases: ['tn', 'tamil nadu', 'madras'] },
  'coimbatore': { state: 'Tamil Nadu', aliases: ['tn', 'tamil nadu'] },
  'ahmedabad': { state: 'Gujarat', aliases: ['gj', 'gujarat'] },
  'surat': { state: 'Gujarat', aliases: ['gj', 'gujarat'] },
  'vadodara': { state: 'Gujarat', aliases: ['gj', 'gujarat', 'baroda'] },
  'jaipur': { state: 'Rajasthan', aliases: ['rj', 'rajasthan'] },
  'jodhpur': { state: 'Rajasthan', aliases: ['rj', 'rajasthan'] },
  'udaipur': { state: 'Rajasthan', aliases: ['rj', 'rajasthan'] },
  'lucknow': { state: 'Uttar Pradesh', aliases: ['up', 'uttar pradesh'] },
  'kanpur': { state: 'Uttar Pradesh', aliases: ['up', 'uttar pradesh'] },
  'noida': { state: 'Uttar Pradesh', aliases: ['up', 'uttar pradesh'] },
  'patna': { state: 'Bihar', aliases: ['br', 'bihar'] },
  'chandigarh': { state: 'Chandigarh', aliases: ['ch', 'chandigarh', 'punjab', 'haryana'] },
  'indore': { state: 'Madhya Pradesh', aliases: ['mp', 'madhya pradesh'] },
  'bhopal': { state: 'Madhya Pradesh', aliases: ['mp', 'madhya pradesh'] },
  'kochi': { state: 'Kerala', aliases: ['kl', 'kerala', 'cochin'] },
  'thiruvananthapuram': { state: 'Kerala', aliases: ['kl', 'kerala', 'trivandrum'] },
  'bhubaneswar': { state: 'Odisha', aliases: ['od', 'orissa', 'odisha'] },
  'guwahati': { state: 'Assam', aliases: ['as', 'assam'] },

  // USA Major Cities
  'new york': { state: 'New York', aliases: ['ny', 'new york', 'nyc'] },
  'los angeles': { state: 'California', aliases: ['ca', 'california'] },
  'chicago': { state: 'Illinois', aliases: ['il', 'illinois'] },
  'houston': { state: 'Texas', aliases: ['tx', 'texas'] },
  'dallas': { state: 'Texas', aliases: ['tx', 'texas'] },
  'austin': { state: 'Texas', aliases: ['tx', 'texas'] },
  'san francisco': { state: 'California', aliases: ['ca', 'california'] },
  'seattle': { state: 'Washington', aliases: ['wa', 'washington'] },
  'miami': { state: 'Florida', aliases: ['fl', 'florida'] },
  'atlanta': { state: 'Georgia', aliases: ['ga', 'georgia'] },
  'boston': { state: 'Massachusetts', aliases: ['ma', 'massachusetts'] },

  // UK Major Cities
  'london': { state: 'England', aliases: ['greater london', 'england', 'uk'] },
  'manchester': { state: 'England', aliases: ['greater manchester', 'england', 'uk'] },
  'birmingham': { state: 'England', aliases: ['west midlands', 'england', 'uk'] },
  'edinburgh': { state: 'Scotland', aliases: ['scotland', 'uk'] },

  // UAE / Middle East
  'dubai': { state: 'Dubai', aliases: ['dubai', 'uae', 'united arab emirates'] },
  'abu dhabi': { state: 'Abu Dhabi', aliases: ['abu dhabi', 'uae', 'united arab emirates'] },
  'sharjah': { state: 'Sharjah', aliases: ['sharjah', 'uae'] },
};

/**
 * Strips invalid artifacts, nulls, undefined, NaN, and object representations
 */
const cleanString = (val) => {
  if (val === null || val === undefined) return '';
  let str = String(val).trim();
  const lower = str.toLowerCase();
  
  if (
    lower === 'undefined' ||
    lower === 'null' ||
    lower === 'nan' ||
    lower === '[object object]' ||
    lower === 'n/a' ||
    lower === 'none' ||
    lower === 'nil' ||
    lower === 'not available'
  ) {
    return '';
  }

  // Remove control characters
  str = str.replace(/[\x00-\x1F\x7F]/g, '');
  return str.trim();
};

/**
 * Validates Email and determines status
 */
const evaluateEmail = (emailStr) => {
  const email = cleanString(emailStr);
  if (!email) {
    return { email: '', email_status: 'Missing' };
  }

  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  if (!emailRegex.test(email)) {
    return { email, email_status: 'Invalid' };
  }

  // Check for placeholder or dummy emails
  const lower = email.toLowerCase();
  if (
    lower.includes('example.com') ||
    lower.includes('test.com') ||
    lower.includes('email.com') ||
    lower.includes('sample.com') ||
    lower.startsWith('noemail') ||
    lower.startsWith('dummy')
  ) {
    return { email, email_status: 'Risky' };
  }

  return { email, email_status: 'Valid' };
};

/**
 * Validates and standardizes Website URL and status
 */
const evaluateWebsite = (webStr, existingStatus = null) => {
  const raw = cleanString(webStr);
  if (!raw || raw.toLowerCase() === 'no website' || raw.toLowerCase() === 'none' || raw === '-') {
    return { website: '', website_status: 'No Website' };
  }

  // Normalize URL format
  let url = raw;
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = 'https://' + url;
  }

  try {
    const parsed = new URL(url);
    if (!parsed.hostname || !parsed.hostname.includes('.')) {
      return { website: raw, website_status: 'Broken' };
    }

    const host = parsed.hostname.toLowerCase();
    if (host === 'example.com' || host === 'localhost' || host === 'temp.com') {
      return { website: url, website_status: 'Poor Website' };
    }

    const status = existingStatus && existingStatus !== 'Unknown' ? existingStatus : 'Working';
    return { website: url, website_status: status };
  } catch (err) {
    return { website: raw, website_status: 'Broken' };
  }
};

/**
 * Verifies City and State consistency
 */
const validateLocation = (cityRaw, stateRaw, countryRaw) => {
  const city = cleanString(cityRaw);
  const state = cleanString(stateRaw);
  const country = cleanString(countryRaw);

  if (!city) {
    return {
      city: '',
      state,
      country,
      location_verified: true,
      needs_verification: false,
      reason: '',
    };
  }

  const cityKey = city.toLowerCase();
  const known = CITY_STATE_KNOWLEDGE[cityKey];

  if (known && state) {
    const stateLower = state.toLowerCase();
    const isMatch = known.aliases.some(alias => stateLower.includes(alias) || alias.includes(stateLower));
    
    if (!isMatch) {
      return {
        city,
        state,
        country: country || (known.aliases.includes('wb') ? 'India' : ''),
        location_verified: false,
        needs_verification: true,
        reason: `Location Conflict: ${city} is typically in ${known.state}, but listed as "${state}".`,
      };
    }
  }

  return {
    city,
    state,
    country,
    location_verified: true,
    needs_verification: false,
    reason: '',
  };
};

/**
 * Calculates overall Data Quality Score (High / Medium / Low)
 */
const calculateDataQuality = (lead) => {
  let points = 0;
  let maxPoints = 7;

  // 1. Business Name present
  if (lead.business_name && lead.business_name.trim().length > 1) points++;

  // 2. Email present and valid
  if (lead.email_status === 'Valid') points++;
  else if (lead.email && lead.email.trim().length > 0) points += 0.5;

  // 3. Phone present
  if (lead.phone && lead.phone.trim().length >= 7) points++;

  // 4. Website present or verified as No Website
  if (lead.website_status === 'Working' || lead.website_status === 'No Website') points++;

  // 5. City and Location clear
  if (lead.city && lead.city.trim().length > 1) points++;

  // 6. Location Verified (no conflict)
  if (lead.location_verified !== false && !lead.needs_verification) points++;

  // 7. Industry or Source defined
  if ((lead.industry && lead.industry.trim().length > 1) || lead.lead_source) points++;

  const ratio = points / maxPoints;
  if (ratio >= 0.75) return 'High';
  if (ratio >= 0.45) return 'Medium';
  return 'Low';
};

/**
 * Full single lead record cleaner and enrichment pipeline
 */
const cleanAndEnrichLead = (rawLead) => {
  const business_name = cleanString(rawLead.business_name || rawLead.business || rawLead.company || rawLead.name);
  const phone = cleanString(rawLead.phone || rawLead.mobile || rawLead.telephone || rawLead.tel);
  const industry = cleanString(rawLead.industry || rawLead.category || rawLead.type || rawLead.sector);
  const contact_person = cleanString(rawLead.contact_person || rawLead.owner || rawLead.person);
  const address = cleanString(rawLead.address || rawLead.street || rawLead.full_address);
  const postal_code = cleanString(rawLead.postal_code || rawLead.zip || rawLead.pincode);
  const notes = cleanString(rawLead.notes || rawLead.remarks || rawLead.comments);
  const lead_status = cleanString(rawLead.lead_status) || 'New';
  const lead_source = cleanString(rawLead.lead_source) || 'Manual';

  const { email, email_status } = evaluateEmail(rawLead.email);
  const { website, website_status } = evaluateWebsite(rawLead.website, rawLead.website_status);
  const loc = validateLocation(rawLead.city, rawLead.state, rawLead.country);

  const cleaned = {
    business_name: business_name || 'Unnamed Business',
    industry,
    email,
    email_status,
    phone,
    website,
    website_status,
    address,
    city: loc.city,
    state: loc.state,
    country: loc.country,
    postal_code,
    lead_status,
    lead_source,
    contact_person,
    notes,
    is_verified: rawLead.is_verified === true || rawLead.is_verified === 'true' || rawLead.is_verified === 1,
    needs_verification: loc.needs_verification || rawLead.needs_verification === true || rawLead.needs_verification === 'true' || rawLead.needs_verification === 1,
    location_verified: loc.location_verified,
    verification_reason: loc.reason || rawLead.verification_reason || '',
    last_contacted: rawLead.last_contacted || null,
  };

  cleaned.data_quality = calculateDataQuality(cleaned);

  return cleaned;
};

module.exports = {
  cleanString,
  evaluateEmail,
  evaluateWebsite,
  validateLocation,
  calculateDataQuality,
  cleanAndEnrichLead,
  CITY_STATE_KNOWLEDGE,
};
