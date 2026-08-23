# TechvionNova CRM — Google Places API (New) Lead Generation & CRM

TechvionNova is a modern, high-precision Cafe Lead Generation and CRM system. It integrates directly with the official **Google Maps Platform — Places API (New)**, eliminating brittle web scraping and providing structured, verified business data with website analysis and pipeline management.

---

## 🌟 Key Features

1. **Official Google Places API (New) Integration**:
   - Uses `places.googleapis.com/v1/places:searchText` (Text Search New).
   - Server-side API key management via `.env` (never exposed to frontend).
   - Real-time connection testing (`Settings → Google API`) with user-friendly error diagnostics (e.g. quota, billing, invalid key, service disabled).

2. **Search Result Preview & Selective Import**:
   - Preview search results before inserting into database.
   - Interactive preview table with Place ID, Rating, Reviews, Business Status, and Google Maps links.
   - Granular import options: `[Import]`, `[Import Selected]`, `[Import All]`.

3. **Multi-Level Duplicate Detection (5-Tier Matching)**:
   - 1. Google Place ID
   - 2. Website domain
   - 3. Phone digits
   - 4. Email address
   - 5. Business Name + City
   - Visual duplicate indicators with interactive conflict resolution: **Update Existing** or **Skip**.

4. **Public Website Analyzer & 0–100 Rules-Based Lead Score**:
   - Analyzes SSL, page load speed, responsiveness, and online table booking / ordering presence.
   - Discovers publicly displayed emails, phone numbers, Instagram, Facebook, and LinkedIn links.
   - Transparent 0–100 score:
     - No Website: `+30`
     - Broken Website: `+25`
     - Outdated Website: `+20`
     - No Online Booking: `+10`
     - No Online Ordering: `+10`
     - Public Business Email Found: `+5`

5. **Complete CRM Lifecycle Management**:
   - Lead table with server-side pagination (supports 50,000+ records).
   - Filters by City, Business Type, Website Status, Outreach Status, and Deal Status.
   - Outreach Activity Timeline & Follow-up tracking (Today, Tomorrow, This Week, Overdue).
   - Bulk actions (Status updates, follow-up dates, bulk delete).
   - CSV Export & Import with column mapping and validation.
   - Analytics Dashboard with 13 KPI cards and chart breakdowns.
   - Background collection jobs with rate limiting, timeouts, and cancellation.

---

## 🛠️ Setup & Google Cloud Configuration

### 1. Google Cloud Platform Requirements
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select your project.
3. In **APIs & Services → Library**, search for and enable **Places API (New)**.
4. Ensure a valid **Billing Account** is linked to the project (Google Cloud offers $200 free monthly credit).
5. Go to **Credentials → Create Credentials → API Key**.

### 2. Local Environment Setup
1. Clone / open the project directory.
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and set your key:
   ```env
   GOOGLE_MAPS_API_KEY=YOUR_API_KEY_HERE
   PORT=5000
   ```
4. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
5. Seed initial demo leads (20 clearly marked DEMO leads):
   ```bash
   python backend/seed.py
   ```
6. Start the server:
   ```bash
   python backend/app.py
   ```
7. Open in your browser:
   ```
   http://127.0.0.1:5000/
   ```

---

## 🧪 Testing

Run the automated test suite:
```bash
python test_suite.py
```
This tests API key connection testing, leads pagination, 5-tier duplicate detection, website analysis, CSV export, analytics, and collection jobs.

---

## 📁 Project Structure

```
TechvionNova_CRM/
├── backend/
│   ├── app.py                # Flask application entry point
│   ├── database.py           # SQLAlchemy database setup & migrations
│   ├── models/
│   │   ├── __init__.py
│   │   ├── lead.py           # Primary Lead ORM model
│   │   └── crm_models.py     # Outreach, Follow-ups, Analysis, Jobs models
│   ├── routes/
│   │   ├── google_places.py  # Google Places API (New) search, test, import & jobs
│   │   ├── leads.py          # Leads CRUD, filters, CSV, timeline, analytics
│   │   └── analyzer.py       # Website inspection & 0-100 scoring
│   ├── seed.py               # 20 DEMO leads seeder
│   └── requirements.txt
├── frontend/
│   ├── leads.html            # Master CRM table
│   ├── collect.html          # Google Places search & preview table
│   ├── lead-details.html     # Lead details, timeline & website analysis
│   ├── dashboard.html        # KPI cards & analytical charts
│   ├── followups.html        # Follow-up reminders
│   ├── jobs.html             # Background collection jobs
│   ├── settings.html         # Google API diagnostics & key settings
│   ├── analyzer.html         # Standalone website analyzer
│   ├── css/style.css         # Modern design system
│   └── js/api.js             # API client & UI helpers
├── .env.example
├── .gitignore
├── README.md
└── test_suite.py
```
