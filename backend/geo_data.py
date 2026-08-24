"""
TechvionNova CRM — Worldwide Geography Configuration
====================================================
Structured country database used by the Global Lead Collector.
No country-specific logic is hardcoded anywhere else in the pipeline.

Each country entry: (name, iso2, iso3, phone_code, currency)
Regions are provided ONLY where a real state/province structure exists.
City lists are optional suggestions for the UI datalist — always free-text capable.
"""

# (name, iso2, iso3, phone_code, currency)
COUNTRY_DATA = [
    # ── Asia ────────────────────────────────────────────────────────────
    ("India", "IN", "IND", "+91", "INR"),
    ("Japan", "JP", "JPN", "+81", "JPY"),
    ("South Korea", "KR", "KOR", "+82", "KRW"),
    ("Singapore", "SG", "SGP", "+65", "SGD"),
    ("United Arab Emirates", "AE", "ARE", "+971", "AED"),
    ("Saudi Arabia", "SA", "SAU", "+966", "SAR"),
    ("Qatar", "QA", "QAT", "+974", "QAR"),
    ("Kuwait", "KW", "KWT", "+965", "KWD"),
    ("Bahrain", "BH", "BHR", "+973", "BHD"),
    ("Oman", "OM", "OMN", "+968", "OMR"),
    ("Israel", "IL", "ISR", "+972", "ILS"),
    ("Turkey", "TR", "TUR", "+90", "TRY"),
    ("Thailand", "TH", "THA", "+66", "THB"),
    ("Vietnam", "VN", "VNM", "+84", "VND"),
    ("Malaysia", "MY", "MYS", "+60", "MYR"),
    ("Indonesia", "ID", "IDN", "+62", "IDR"),
    ("Philippines", "PH", "PHL", "+63", "PHP"),
    ("Pakistan", "PK", "PAK", "+92", "PKR"),
    ("Bangladesh", "BD", "BGD", "+880", "BDT"),
    ("Sri Lanka", "LK", "LKA", "+94", "LKR"),
    ("Nepal", "NP", "NPL", "+977", "NPR"),
    ("China", "CN", "CHN", "+86", "CNY"),
    ("Hong Kong", "HK", "HKG", "+852", "HKD"),
    ("Taiwan", "TW", "TWN", "+886", "TWD"),
    ("Jordan", "JO", "JOR", "+962", "JOD"),
    ("Lebanon", "LB", "LBN", "+961", "LBP"),
    # ── Europe ──────────────────────────────────────────────────────────
    ("United Kingdom", "GB", "GBR", "+44", "GBP"),
    ("Ireland", "IE", "IRL", "+353", "EUR"),
    ("Germany", "DE", "DEU", "+49", "EUR"),
    ("France", "FR", "FRA", "+33", "EUR"),
    ("Italy", "IT", "ITA", "+39", "EUR"),
    ("Spain", "ES", "ESP", "+34", "EUR"),
    ("Portugal", "PT", "PRT", "+351", "EUR"),
    ("Netherlands", "NL", "NLD", "+31", "EUR"),
    ("Belgium", "BE", "BEL", "+32", "EUR"),
    ("Switzerland", "CH", "CHE", "+41", "CHF"),
    ("Austria", "AT", "AUT", "+43", "EUR"),
    ("Sweden", "SE", "SWE", "+46", "SEK"),
    ("Norway", "NO", "NOR", "+47", "NOK"),
    ("Denmark", "DK", "DNK", "+45", "DKK"),
    ("Finland", "FI", "FIN", "+358", "EUR"),
    ("Iceland", "IS", "ISL", "+354", "ISK"),
    ("Poland", "PL", "POL", "+48", "PLN"),
    ("Czechia", "CZ", "CZE", "+420", "CZK"),
    ("Hungary", "HU", "HUN", "+36", "HUF"),
    ("Romania", "RO", "ROU", "+40", "RON"),
    ("Greece", "GR", "GRC", "+30", "EUR"),
    ("Croatia", "HR", "HRV", "+385", "EUR"),
    ("Bulgaria", "BG", "BGR", "+359", "BGN"),
    ("Serbia", "RS", "SRB", "+381", "RSD"),
    ("Slovakia", "SK", "SVK", "+421", "EUR"),
    ("Slovenia", "SI", "SVN", "+386", "EUR"),
    ("Estonia", "EE", "EST", "+372", "EUR"),
    ("Latvia", "LV", "LVA", "+371", "EUR"),
    ("Lithuania", "LT", "LTU", "+370", "EUR"),
    ("Luxembourg", "LU", "LUX", "+352", "EUR"),
    ("Malta", "MT", "MLT", "+356", "EUR"),
    ("Cyprus", "CY", "CYP", "+357", "EUR"),
    ("Ukraine", "UA", "UKR", "+380", "UAH"),
    # ── Americas ────────────────────────────────────────────────────────
    ("United States", "US", "USA", "+1", "USD"),
    ("Canada", "CA", "CAN", "+1", "CAD"),
    ("Mexico", "MX", "MEX", "+52", "MXN"),
    ("Brazil", "BR", "BRA", "+55", "BRL"),
    ("Argentina", "AR", "ARG", "+54", "ARS"),
    ("Chile", "CL", "CHL", "+56", "CLP"),
    ("Colombia", "CO", "COL", "+57", "COP"),
    ("Peru", "PE", "PER", "+51", "PEN"),
    ("Uruguay", "UY", "URY", "+598", "UYU"),
    ("Ecuador", "EC", "ECU", "+593", "USD"),
    ("Panama", "PA", "PAN", "+507", "PAB"),
    ("Costa Rica", "CR", "CRI", "+506", "CRC"),
    ("Dominican Republic", "DO", "DOM", "+1809", "DOP"),
    # ── Africa ──────────────────────────────────────────────────────────
    ("South Africa", "ZA", "ZAF", "+27", "ZAR"),
    ("Egypt", "EG", "EGY", "+20", "EGP"),
    ("Nigeria", "NG", "NGA", "+234", "NGN"),
    ("Kenya", "KE", "KEN", "+254", "KES"),
    ("Morocco", "MA", "MAR", "+212", "MAD"),
    ("Ghana", "GH", "GHA", "+233", "GHS"),
    ("Tanzania", "TZ", "TZA", "+255", "TZS"),
    # ── Oceania ─────────────────────────────────────────────────────────
    ("Australia", "AU", "AUS", "+61", "AUD"),
    ("New Zealand", "NZ", "NZL", "+64", "NZD"),
    ("Fiji", "FJ", "FJI", "+679", "FJD"),
]

COUNTRIES = {c[1]: {"name": c[0], "iso2": c[1], "iso3": c[2],
                    "phone_code": c[3], "currency": c[4]}
             for c in COUNTRY_DATA}

BY_NAME = {c[0].lower(): COUNTRIES[c[1]] for c in COUNTRY_DATA}
BY_ISO3 = {c[2]: COUNTRIES[c[1]] for c in COUNTRY_DATA}

# Preset used by the 🌎 Worldwide Collection mode (major business markets).
WORLDWIDE_PRESET = ["US", "GB", "CA", "AU", "IN", "DE", "FR", "IT", "ES",
                    "BR", "MX", "JP", "KR", "SG", "AE", "SA", "ZA", "NZ",
                    "NL", "IE"]

# ── Regions / States / Provinces (only where such a structure exists) ──
REGIONS = {
    "US": ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
           "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
           "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
           "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
           "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
           "New Hampshire", "New Jersey", "New Mexico", "New York",
           "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
           "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
           "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
           "West Virginia", "Wisconsin", "Wyoming", "District of Columbia"],
    "IN": ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
           "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
           "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
           "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
           "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
           "West Bengal", "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry",
           "Chandigarh", "Andaman and Nicobar Islands"],
    "GB": ["England", "Scotland", "Wales", "Northern Ireland"],
    "CA": ["Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba",
           "Saskatchewan", "Nova Scotia", "New Brunswick", "Prince Edward Island",
           "Newfoundland and Labrador", "Yukon", "Northwest Territories", "Nunavut"],
    "AU": ["New South Wales", "Victoria", "Queensland", "Western Australia",
           "South Australia", "Tasmania", "Australian Capital Territory",
           "Northern Territory"],
    "DE": ["Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen",
           "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen",
           "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen",
           "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"],
    "FR": ["Île-de-France", "Auvergne-Rhône-Alpes", "Provence-Alpes-Côte d'Azur",
           "Occitanie", "Nouvelle-Aquitaine", "Grand Est", "Hauts-de-France",
           "Bourgogne-Franche-Comté", "Pays de la Loire", "Bretagne",
           "Normandie", "Centre-Val de Loire", "Corse"],
    "IT": ["Lazio", "Lombardia", "Campania", "Veneto", "Piemonte", "Emilia-Romagna",
           "Sicilia", "Toscana", "Puglia", "Sardegna", "Liguria", "Marche",
           "Friuli-Venezia Giulia", "Abruzzo", "Umbria", "Calabria", "Basilicata",
           "Molise", "Trentino-Alto Adige", "Valle d'Aosta"],
    "ES": ["Andalucía", "Cataluña", "Comunidad de Madrid", "Comunitat Valenciana",
           "País Vasco", "Galicia", "Castilla y León", "Canarias", "Castilla-La Mancha",
           "Región de Murcia", "Aragón", "Illes Balears", "Extremadura",
           "Principado de Asturias", "Navarra", "Cantabria", "La Rioja"],
    "JP": ["Tokyo", "Osaka", "Kyoto", "Kanagawa", "Saitama", "Chiba", "Hyogo",
           "Aichi", "Fukuoka", "Hokkaido", "Miyagi", "Shizuoka", "Hiroshima",
           "Sendai", "Niigata", "Okayama", "Kumamoto", "Kagoshima", "Okinawa",
           "Nagano", "Gifu", "Shiga", "Nara", "Ehime", "Toyama", "Ishikawa"],
    "BR": ["São Paulo", "Rio de Janeiro", "Minas Gerais", "Bahia", "Paraná",
           "Rio Grande do Sul", "Pernambuco", "Ceará", "Santa Catarina",
           "Distrito Federal", "Goiás", "Amazonas", "Espírito Santo"],
    "MX": ["Ciudad de México", "Jalisco", "Nuevo León", "Estado de México",
           "Puebla", "Querétaro", "Guanajuato", "Yucatán", "Quintana Roo",
           "Baja California", "Sonora", "Coahuila"],
    "AE": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah",
           "Fujairah", "Umm Al Quwain"],
    "SA": ["Riyadh", "Makkah", "Eastern Province", "Madinah", "Asir",
           "Tabuk", "Qassim", "Jazan", "Hail", "Northern Borders"],
    "ZA": ["Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape",
           "Free State", "Limpopo", "Mpumalanga", "North West", "Northern Cape"],
    "NZ": ["Auckland", "Wellington", "Canterbury", "Waikato", "Bay of Plenty",
           "Otago", "Manawatū-Whanganui", "Taranaki", "Hawke's Bay", "Northland",
           "Southland"],
    "NL": ["Noord-Holland", "Zuid-Holland", "Utrecht", "Noord-Brabant",
           "Gelderland", "Overijssel", "Limburg", "Groningen", "Flevoland",
           "Drenthe", "Zeeland", "Friesland"],
    "SG": [],  # City-state
    "KR": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju",
           "Ulsan", "Gyeonggi-do", "Jeju-do"],
}

# Optional city suggestions for the search UI datalist (always free-text capable)
CITY_SUGGESTIONS = {
    "US": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
           "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Francisco",
           "Seattle", "Miami", "Atlanta", "Boston", "Austin", "Denver"],
    "GB": ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool",
           "Bristol", "Edinburgh", "Cardiff", "Belfast", "Newcastle", "Brighton"],
    "CA": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Edmonton",
           "Quebec City", "Winnipeg", "Halifax", "Victoria"],
    "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide",
           "Gold Coast", "Canberra", "Hobart", "Darwin", "Newcastle"],
    "IN": ["Kolkata", "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai",
           "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Kochi", "Goa"],
    "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Stuttgart",
           "Düsseldorf", "Leipzig", "Dresden", "Nuremberg"],
    "FR": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes",
           "Strasbourg", "Bordeaux", "Lille", "Cannes"],
    "IT": ["Rome", "Milan", "Naples", "Turin", "Florence", "Bologna",
           "Venice", "Verona", "Genoa", "Palermo"],
    "ES": ["Madrid", "Barcelona", "Valencia", "Seville", "Zaragoza",
           "Málaga", "Bilbao", "Granada", "Palma", "Marbella"],
    "JP": ["Tokyo", "Osaka", "Kyoto", "Yokohama", "Nagoya", "Sapporo",
           "Fukuoka", "Kobe", "Hiroshima", "Sendai"],
    "AE": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Al Ain",
           "Ras Al Khaimah", "Fujairah"],
    "SG": ["Singapore", "Jurong", "Woodlands", "Tampines"],
    "BR": ["São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza",
           "Belo Horizonte", "Curitiba", "Porto Alegre", "Recife"],
    "MX": ["Mexico City", "Guadalajara", "Monterrey", "Cancún", "Tijuana",
           "Puebla", "Mérida", "Querétaro"],
    "NL": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven",
           "Groningen", "Maastricht"],
    "NZ": ["Auckland", "Wellington", "Christchurch", "Hamilton",
           "Queenstown", "Dunedin"],
    "ZA": ["Johannesburg", "Cape Town", "Durban", "Pretoria",
           "Port Elizabeth", "Bloemfontein"],
    "KR": ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Jeju"],
    "SA": ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar"],
    "IE": ["Dublin", "Cork", "Galway", "Limerick", "Waterford"],
    "CH": ["Zurich", "Geneva", "Basel", "Bern", "Lausanne", "Lucerne"],
    "PT": ["Lisbon", "Porto", "Algarve", "Braga", "Funchal"],
    "TH": ["Bangkok", "Chiang Mai", "Phuket", "Pattaya", "Krabi"],
    "MY": ["Kuala Lumpur", "Penang", "Johor Bahru", "Malacca", "Kota Kinabalu"],
}

BUSINESS_CATEGORIES = [
    "Cafe", "Coffee Shop", "Bakery", "Restaurant", "Bistro", "Cloud Kitchen",
    "Fast Food Restaurant", "Tea Shop", "Dessert Shop", "Ice Cream Parlor",
    "Food Truck", "Sweet Shop", "Hotel", "Resort", "Hostel", "Banquet Hall",
    "Salon", "Spa", "Barber Shop", "Nail Salon", "Gym", "Yoga Studio",
    "Fitness Center", "Dental Clinic", "Hospital", "Diagnostic Lab", "Pharmacy",
    "Veterinary Clinic", "Coaching Center", "Play School", "Language School",
    "Real Estate Agency", "Construction Company", "Interior Designer",
    "Architect", "Event Planner", "Wedding Photographer", "Wedding Venue",
    "Boutique", "Clothing Store", "Jewellery Store", "Shoe Store",
    "Electronics Store", "Furniture Store", "Home Decor Store", "Book Store",
    "Toy Store", "Mobile Phone Shop", "Computer Store", "Car Dealer",
    "Bike Dealer", "Car Service Center", "Car Rental", "Travel Agency",
    "Packers and Movers", "Moving Company", "Storage Facility",
    "CA Firm", "Accounting Firm", "Law Firm", "Insurance Agency",
    "Digital Marketing Agency", "Advertising Agency", "IT Company",
    "Web Design Agency", "Printing Press", "Photography Studio",
    "Laundry Service", "Cleaning Service", "Pest Control Service",
    "Security Service", "Daycare", "Pet Shop", "Florist", "Gift Shop",
]


def find_country(query: str | None) -> dict | None:
    """Resolve a country by name / ISO2 / ISO3 (case-insensitive)."""
    if not query:
        return None
    q = query.strip()
    return COUNTRIES.get(q.upper()) or BY_NAME.get(q.lower()) or BY_ISO3.get(q.upper())


def get_regions(iso2: str) -> list[str]:
    return REGIONS.get((iso2 or "").upper(), [])


def get_city_suggestions(iso2: str) -> list[str]:
    return CITY_SUGGESTIONS.get((iso2 or "").upper(), [])


def normalize_intl_phone(raw: str | None, iso2: str | None) -> str:
    """
    Normalize a phone number to international format using the country code.
    '+44 20 7946 0958'  -> '+442079460958'
    '020 7946 0958' (GB)-> '+442079460958'
    '(415) 555-2671'(US)-> '+14155552671'
    Never invents digits beyond prefixing the country dial code.
    """
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return raw.strip()
    country = COUNTRIES.get((iso2 or "").upper())
    if raw.strip().startswith("+"):
        return "+" + digits.lstrip("0") if len(digits) > 6 else "+" + digits
    if country:
        code = "".join(ch for ch in country["phone_code"] if ch.isdigit())
        # Drop national trunk prefix '0' when prefixing country code
        if digits.startswith("0"):
            digits = digits.lstrip("0")
        return f"+{code}{digits}"
    return "+" + digits


def build_search_chunks(countries: list[str], region: str | None,
                        city: str | None, category: str,
                        keyword: str | None, max_chunks: int = 30) -> list[dict]:
    """
    Break a worldwide collection into manageable per-country chunks.
    Each chunk is one Google Places text-search target:
      {country_iso2, region, city, query}
    Never issues one enormous world-wide request.
    """
    chunks = []
    seen = set()
    kw = (keyword or "").strip()
    reg = (region or "").strip()
    cit = (city or "").strip()

    for c in countries:
        country = find_country(c)
        if not country:
            continue
        key = (country["iso2"], reg.lower(), cit.lower())
        if key in seen:
            continue
        seen.add(key)

        location_parts = [p for p in [cit, reg] if p]
        place_str = ", ".join(location_parts + [country["name"]])
        query = f"{kw or category} in {place_str}"
        chunks.append({
            "country_iso2": country["iso2"],
            "country_name": country["name"],
            "region": reg,
            "city": cit,
            "category": category,
            "keyword": kw,
            "query": query,
        })
        if len(chunks) >= max_chunks:
            break
    return chunks
