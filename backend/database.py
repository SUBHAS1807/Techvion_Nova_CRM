import os
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, text
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'TechvionNova.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Ensure all required columns and tables exist without data loss."""
    with engine.connect() as conn:
        # Check if 'leads' table exists
        table_exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
        ).fetchone()

        if table_exists:
            existing_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(leads)"))]
            migrations = {
                "google_place_id": "ALTER TABLE leads ADD COLUMN google_place_id VARCHAR(255)",
                "google_maps_url": "ALTER TABLE leads ADD COLUMN google_maps_url VARCHAR(500)",
                "rating": "ALTER TABLE leads ADD COLUMN rating FLOAT",
                "google_rating": "ALTER TABLE leads ADD COLUMN google_rating FLOAT",
                "review_count": "ALTER TABLE leads ADD COLUMN review_count INTEGER",
                "google_reviews": "ALTER TABLE leads ADD COLUMN google_reviews INTEGER",
                "latitude": "ALTER TABLE leads ADD COLUMN latitude FLOAT",
                "longitude": "ALTER TABLE leads ADD COLUMN longitude FLOAT",
                "business_status": "ALTER TABLE leads ADD COLUMN business_status VARCHAR(50) DEFAULT 'OPERATIONAL'",
                "address": "ALTER TABLE leads ADD COLUMN address VARCHAR(500)",
                "is_demo": "ALTER TABLE leads ADD COLUMN is_demo BOOLEAN DEFAULT 0",
                "email_source": "ALTER TABLE leads ADD COLUMN email_source VARCHAR(100)",
                "email_source_url": "ALTER TABLE leads ADD COLUMN email_source_url VARCHAR(500)",
                "email_status": "ALTER TABLE leads ADD COLUMN email_status VARCHAR(30) DEFAULT 'Not Analyzed'",
                # Worldwide collection columns
                "country": "ALTER TABLE leads ADD COLUMN country VARCHAR(100)",
                "country_code": "ALTER TABLE leads ADD COLUMN country_code VARCHAR(2)",
                "region": "ALTER TABLE leads ADD COLUMN region VARCHAR(120)",
                "state_province": "ALTER TABLE leads ADD COLUMN state_province VARCHAR(120)",
                "postal_code": "ALTER TABLE leads ADD COLUMN postal_code VARCHAR(20)",
                "currency": "ALTER TABLE leads ADD COLUMN currency VARCHAR(8) DEFAULT 'INR'",
                "other_socials": "ALTER TABLE leads ADD COLUMN other_socials TEXT",
                "opening_hours": "ALTER TABLE leads ADD COLUMN opening_hours TEXT",
                # Machine website status code (worldwide collector)
                "website_status_code": "ALTER TABLE leads ADD COLUMN website_status_code VARCHAR(30)",
                # Contacted CRM Upgrade columns
                "contact_method": "ALTER TABLE leads ADD COLUMN contact_method VARCHAR(50)",
                "last_contacted_date": "ALTER TABLE leads ADD COLUMN last_contacted_date DATETIME",
                "followup_count": "ALTER TABLE leads ADD COLUMN followup_count INTEGER DEFAULT 0",
                "next_action": "ALTER TABLE leads ADD COLUMN next_action VARCHAR(255)",
            }
            for col, ddl in migrations.items():
                if col not in existing_cols:
                    try:
                        conn.execute(text(ddl))
                    except Exception as e:
                        print(f"Migration notice ({col}): {e}")

            # crawl_jobs global-collection columns
            job_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(crawl_jobs)"))]
            if job_cols:
                job_migrations = {
                    "is_global": "ALTER TABLE crawl_jobs ADD COLUMN is_global BOOLEAN DEFAULT 0",
                    "country": "ALTER TABLE crawl_jobs ADD COLUMN country VARCHAR(100)",
                    "countries_json": "ALTER TABLE crawl_jobs ADD COLUMN countries_json TEXT",
                    "region": "ALTER TABLE crawl_jobs ADD COLUMN region VARCHAR(120)",
                    "keyword": "ALTER TABLE crawl_jobs ADD COLUMN keyword VARCHAR(200)",
                    "radius_km": "ALTER TABLE crawl_jobs ADD COLUMN radius_km INTEGER",
                    "website_status_filter": "ALTER TABLE crawl_jobs ADD COLUMN website_status_filter VARCHAR(30)",
                    "discovered": "ALTER TABLE crawl_jobs ADD COLUMN discovered INTEGER DEFAULT 0",
                    "websites_found": "ALTER TABLE crawl_jobs ADD COLUMN websites_found INTEGER DEFAULT 0",
                    "emails_found": "ALTER TABLE crawl_jobs ADD COLUMN emails_found INTEGER DEFAULT 0",
                    "qualified_leads": "ALTER TABLE crawl_jobs ADD COLUMN qualified_leads INTEGER DEFAULT 0",
                    "skipped_no_email": "ALTER TABLE crawl_jobs ADD COLUMN skipped_no_email INTEGER DEFAULT 0",
                    "pending_chunks": "ALTER TABLE crawl_jobs ADD COLUMN pending_chunks TEXT",
                    "current_chunk": "ALTER TABLE crawl_jobs ADD COLUMN current_chunk VARCHAR(255)",
                }
                for col, ddl in job_migrations.items():
                    if col not in job_cols:
                        try:
                            conn.execute(text(ddl))
                        except Exception as e:
                            print(f"Migration notice (crawl_jobs.{col}): {e}")

            # discovered_businesses website_status column (new installs get it
            # from the model; existing DBs are migrated here)
            disc_cols = [r[1] for r in conn.execute(text("PRAGMA table_info(discovered_businesses)"))]
            if disc_cols and "website_status" not in disc_cols:
                try:
                    conn.execute(text("ALTER TABLE discovered_businesses ADD COLUMN website_status VARCHAR(30) DEFAULT 'WEBSITE_UNKNOWN'"))
                except Exception as e:
                    print(f"Migration notice (discovered_businesses.website_status): {e}")
            # Backfill: classify pre-existing rows from stored source truth
            # (website_url presence) so stats/filters cover legacy discoveries.
            # NOTE: SQLite's ALTER TABLE ... DEFAULT fills existing rows with
            # the default, so legacy rows carry 'WEBSITE_UNKNOWN' rather than NULL.
            if disc_cols:
                try:
                    conn.execute(text(
                        "UPDATE discovered_businesses SET website_status = 'HAS_WEBSITE' "
                        "WHERE (website_status IS NULL OR website_status = 'WEBSITE_UNKNOWN') "
                        "AND website_url IS NOT NULL AND TRIM(website_url) != ''"))
                    # Remaining legacy rows had no source URL → true no-website
                    conn.execute(text(
                        "UPDATE discovered_businesses SET website_status = 'NO_WEBSITE' "
                        "WHERE website_status IS NULL "
                        "OR website_status = 'WEBSITE_UNKNOWN'"))
                except Exception as e:
                    print(f"Migration notice (website_status backfill): {e}")

            # Create performance indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_leads_place_id ON leads(google_place_id)",
                "CREATE INDEX IF NOT EXISTS idx_leads_business_name ON leads(business_name)",
                "CREATE INDEX IF NOT EXISTS idx_leads_city ON leads(city)",
                "CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone)",
                "CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)",
                "CREATE INDEX IF NOT EXISTS idx_leads_website ON leads(current_website)",
                "CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(lead_source)",
                "CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score)",
                "CREATE INDEX IF NOT EXISTS idx_leads_next_followup ON leads(next_followup_date)",
                "CREATE INDEX IF NOT EXISTS idx_leads_outreach_status ON leads(outreach_status)",
                "CREATE INDEX IF NOT EXISTS idx_leads_response_status ON leads(response_status)",
                "CREATE INDEX IF NOT EXISTS idx_leads_deal_status ON leads(deal_status)",
                "CREATE INDEX IF NOT EXISTS idx_leads_project_status ON leads(project_status)",
                "CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country)",
                "CREATE INDEX IF NOT EXISTS idx_leads_country_code ON leads(country_code)",
                "CREATE INDEX IF NOT EXISTS idx_leads_contact_method ON leads(contact_method)",
                "CREATE INDEX IF NOT EXISTS idx_leads_last_contacted ON leads(last_contacted_date)",
                "CREATE INDEX IF NOT EXISTS idx_leads_followup_count ON leads(followup_count)",
            ]
            for idx_sql in indexes:
                try:
                    conn.execute(text(idx_sql))
                except Exception as e:
                    pass

        conn.commit()
