import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text, Index, ForeignKey
)
from backend.database import Base


class OutreachActivity(Base):
    __tablename__ = "outreach_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(12), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    activity_type = Column(String(50), nullable=False)  # First Contact, Follow-up, Proposal Sent, Deal Won, Meeting, etc.
    description = Column(Text, nullable=True)
    result = Column(String(100), nullable=True)  # Replied, Interested, No Response, Bounced, etc.
    created_by = Column(String(100), default="Admin")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "date": self.date.isoformat() if self.date else None,
            "activity_type": self.activity_type,
            "description": self.description or "",
            "result": self.result or "",
            "created_by": self.created_by or "Admin",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WebsiteAnalysisRecord(Base):
    __tablename__ = "website_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(12), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=True, index=True)
    url = Column(String(500), nullable=False, index=True)
    status_code = Column(Integer, nullable=True)
    has_ssl = Column(Boolean, default=False)
    emails = Column(Text, nullable=True)    # JSON array
    phones = Column(Text, nullable=True)    # JSON array
    socials = Column(Text, nullable=True)   # JSON dict
    analysis_json = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "url": self.url,
            "status_code": self.status_code,
            "has_ssl": self.has_ssl,
            "emails": json.loads(self.emails) if self.emails else [],
            "phones": json.loads(self.phones) if self.phones else [],
            "socials": json.loads(self.socials) if self.socials else {},
            "analysis": json.loads(self.analysis_json) if self.analysis_json else {},
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }


class CollectionJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), unique=True, index=True, nullable=False)
    query = Column(String(255), nullable=False)
    city = Column(String(100), nullable=True)
    business_type = Column(String(100), nullable=True)
    requested_results = Column(Integer, default=20)
    processed_results = Column(Integer, default=0)
    imported = Column(Integer, default=0)
    duplicates = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    status = Column(String(50), default="Pending", index=True)  # Pending, Running, Paused, Completed, Stopped, Failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ─── Global (worldwide) collection extensions ───────────────────────
    is_global = Column(Boolean, default=False, index=True)
    country = Column(String(100), nullable=True)          # single-country label (display)
    countries_json = Column(Text, nullable=True)          # JSON list of ISO2 codes
    region = Column(String(120), nullable=True)
    keyword = Column(String(200), nullable=True)
    radius_km = Column(Integer, nullable=True)
    website_status_filter = Column(String(30), nullable=True)  # ALL / NO_WEBSITE / HAS_WEBSITE / WEBSITE_INACCESSIBLE
    discovered = Column(Integer, default=0)               # Places results seen
    websites_found = Column(Integer, default=0)           # discoveries with a site
    emails_found = Column(Integer, default=0)             # analyses yielding an email
    qualified_leads = Column(Integer, default=0)          # promoted into leads table
    skipped_no_email = Column(Integer, default=0)         # NO EMAIL = NO LEAD
    pending_chunks = Column(Text, nullable=True)          # JSON queue for pause/resume
    current_chunk = Column(String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "query": self.query,
            "city": self.city or "",
            "business_type": self.business_type or "",
            "requested_results": self.requested_results,
            "processed_results": self.processed_results,
            "imported": self.imported,
            "duplicates": self.duplicates,
            "errors": self.errors,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # Global fields
            "is_global": bool(self.is_global),
            "country": self.country or "",
            "countries": json.loads(self.countries_json) if self.countries_json else [],
            "region": self.region or "",
            "keyword": self.keyword or "",
            "radius_km": self.radius_km,
            "website_status_filter": self.website_status_filter or "ALL",
            "discovered": self.discovered or 0,
            "websites_found": self.websites_found or 0,
            "emails_found": self.emails_found or 0,
            "qualified_leads": self.qualified_leads or 0,
            "skipped_no_email": self.skipped_no_email or 0,
            "pending_chunks": len(json.loads(self.pending_chunks)) if self.pending_chunks else 0,
            "current_chunk": self.current_chunk or "",
        }


class CollectionLog(Base):
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), ForeignKey("crawl_jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(12), ForeignKey("leads.lead_id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="Pending", index=True)  # Pending, Completed, Cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "status": self.status,
            "notes": self.notes or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ApiUsageRecord(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(100), nullable=False)  # places:searchText, etc.
    request_type = Column(String(50), default="search")  # search, details, test
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    status_code = Column(Integer, default=200)
    cost_estimate = Column(Float, default=0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "endpoint": self.endpoint,
            "request_type": self.request_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status_code": self.status_code,
            "cost_estimate": self.cost_estimate or 0.0,
        }


class DiscoveredBusiness(Base):
    """
    Raw worldwide discovery from Google Places — pre-qualification staging.
    Only rows that end with EMAIL_FOUND are promoted into the leads table.
    """
    __tablename__ = "discovered_businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(String(255), unique=True, index=True, nullable=False)
    business_name = Column(String(250), nullable=False, default="")
    business_type = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    country_code = Column(String(2), nullable=True, index=True)
    country_name = Column(String(100), nullable=True, index=True)
    region = Column(String(120), nullable=True, index=True)          # state/province (admin_area_1)
    city = Column(String(120), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True)
    phone_raw = Column(String(50), nullable=True)
    phone_intl = Column(String(30), nullable=True)
    website_url = Column(String(500), nullable=True)
    has_website = Column(Boolean, default=False)
    # NO_WEBSITE | HAS_WEBSITE | WEBSITE_INACCESSIBLE | WEBSITE_UNKNOWN
    website_status = Column(String(30), default="WEBSITE_UNKNOWN", index=True)
    maps_url = Column(String(500), nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    business_status = Column(String(50), nullable=True)              # OPERATIONAL / CLOSED_PERMANENTLY ...
    opening_hours_json = Column(Text, nullable=True)                 # JSON array of weekday strings

    job_id = Column(String(50), ForeignKey("crawl_jobs.job_id", ondelete="SET NULL"), nullable=True, index=True)

    # NOT_ANALYZED | ANALYZING | EMAIL_FOUND | EMAIL_NOT_FOUND |
    # WEBSITE_UNAVAILABLE | INVALID_EMAIL | ERROR  (spec-defined enums)
    email_status = Column(String(30), default="NOT_ANALYZED", index=True)
    email = Column(String(320), nullable=True)
    email_source_page = Column(String(500), nullable=True)
    emails_json = Column(Text, nullable=True)                        # JSON array of candidates
    analysis_error = Column(String(300), nullable=True)

    lead_id = Column(String(12), ForeignKey("leads.lead_id", ondelete="SET NULL"), nullable=True, index=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "place_id": self.place_id,
            "business_name": self.business_name,
            "business_type": self.business_type or "",
            "address": self.address or "",
            "country_code": self.country_code or "",
            "country_name": self.country_name or "",
            "region": self.region or "",
            "city": self.city or "",
            "postal_code": self.postal_code or "",
            "phone_raw": self.phone_raw or "",
            "phone_intl": self.phone_intl or "",
            "website_url": self.website_url or "",
            "has_website": bool(self.has_website),
            "website_status": self.website_status or "WEBSITE_UNKNOWN",
            "maps_url": self.maps_url or "",
            "rating": self.rating,
            "review_count": self.review_count,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "business_status": self.business_status or "",
            "opening_hours": json.loads(self.opening_hours_json) if self.opening_hours_json else [],
            "job_id": self.job_id or "",
            "email_status": self.email_status or "NOT_ANALYZED",
            "email": self.email or "",
            "email_source_page": self.email_source_page or "",
            "emails": json.loads(self.emails_json) if self.emails_json else [],
            "analysis_error": self.analysis_error or "",
            "lead_id": self.lead_id or "",
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
