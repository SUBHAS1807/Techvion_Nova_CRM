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
    status = Column(String(50), default="Pending", index=True)  # Pending, Running, Completed, Stopped, Failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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
