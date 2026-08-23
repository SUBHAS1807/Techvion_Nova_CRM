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
            }
            for col, ddl in migrations.items():
                if col not in existing_cols:
                    try:
                        conn.execute(text(ddl))
                    except Exception as e:
                        print(f"Migration notice ({col}): {e}")

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
            ]
            for idx_sql in indexes:
                try:
                    conn.execute(text(idx_sql))
                except Exception as e:
                    pass

        conn.commit()
