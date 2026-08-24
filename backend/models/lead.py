import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, Text, Index, ForeignKey
)
from backend.database import Base


class Lead(Base):
    __tablename__ = "leads"

    # ─── 26 Primary CRM Fields ──────────────────────────────────────────
    # 1. Mark / Unmark
    is_marked = Column(Boolean, default=False)

    # 2. Lead ID (Primary Key: TVN-XXXXXX)
    lead_id = Column(String(12), primary_key=True, index=True)

    # 3. Business Name
    business_name = Column(String(255), nullable=False, index=True)

    # 4. Owner Name (Always 'Unknown' if not publicly verified; never fake)
    owner_name = Column(String(255), default="Unknown", nullable=True)

    # 5. Business Type
    business_type = Column(String(100), nullable=False, index=True)

    # 6. City
    city = Column(String(100), nullable=False, index=True)

    # 7. Lead Source
    lead_source = Column(String(100), nullable=False, default="Google Places API", index=True)

    # 8. Phone
    phone = Column(String(50), nullable=True, index=True)

    # 9. Email
    email = Column(String(255), nullable=True, index=True)

    # 10. Images (JSON array of URL strings)
    images = Column(Text, nullable=True)

    # 11. Current Website
    current_website = Column(String(500), nullable=True, index=True)

    # 12. Instagram
    instagram = Column(String(255), nullable=True)

    # 13. Facebook
    facebook = Column(String(255), nullable=True)

    # 14. Website Status
    # Options: No Website, Good, Outdated, Broken, Under Construction, E-commerce Website, Booking Website, Unknown
    website_status = Column(String(50), nullable=False, default="Unknown", index=True)

    # 15. Preferred Contact Channel
    preferred_contact_channel = Column(String(50), nullable=True)

    # 16. First Contact Date
    first_contact_date = Column(DateTime, nullable=True)

    # 17. Outreach Status
    # Options: Not Contacted, Contacted, Follow-up, Completed, Do Not Contact
    outreach_status = Column(String(50), default="Not Contacted", index=True)

    # 18. Response Status
    # Options: No Response, Replied, Positive, Negative, Interested, Not Interested, Needs Follow-up
    response_status = Column(String(50), default="No Response", index=True)

    # 19. Interested / Agreed
    # Options: Pending, Interested, Agreed, Rejected
    interested_agreed = Column(String(50), default="Pending", index=True)

    # 20. Website Requirement
    # Options: New Website, Website Redesign, Landing Page, Cafe Website, Restaurant Website, E-commerce, Online Ordering, Online Booking, Menu Website, Maintenance, Hosting, SEO, Other
    website_requirement = Column(String(255), nullable=True)

    # 21. Estimated Budget (INR ₹)
    estimated_budget = Column(String(50), nullable=True)

    # 22. Proposal Status
    # Options: Not Sent, Draft, Sent, Follow-up Required, Revised, Accepted, Rejected
    proposal_status = Column(String(50), default="Not Sent", index=True)

    # 23. Deal Status
    # Options: Open, Negotiation, Won, Lost, On Hold
    deal_status = Column(String(50), default="Open", index=True)

    # 24. Project / Delivery Status
    # Options: Not Started, Planning, Requirement Collection, UI/UX Design, Development, Testing, Client Review, Revision, Ready for Delivery, Delivered, Maintenance, Cancelled
    project_status = Column(String(50), default="Not Started", index=True)

    # 25. Next Follow-up Date
    next_followup_date = Column(DateTime, nullable=True, index=True)

    # 26. Remarks
    remarks = Column(Text, nullable=True)

    # ─── Additional Google Places & Internal Fields ─────────────────────
    # Google Place ID (Unique official Place ID)
    google_place_id = Column(String(255), nullable=True, index=True)

    # Google Maps URL
    google_maps_url = Column(String(500), nullable=True)

    # Legacy Source URL
    source_url = Column(String(500), nullable=True)

    # Address
    address = Column(String(500), nullable=True)

    # Rating & Reviews
    rating = Column(Float, nullable=True)
    google_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    google_reviews = Column(Integer, nullable=True)

    # Coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Business Status (e.g. OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY)
    business_status = Column(String(50), nullable=True)

    # Email Verification Status: Not Checked, Valid Format, Invalid Format, Unknown
    email_verification_status = Column(String(30), default="Not Checked")

    # Email Discovery Status: Not Analyzed, Found, Not Found, Invalid, Error
    email_status = Column(String(30), default="Not Analyzed", index=True)

    # Email Source & URL: Google Places, Business Website, Manual, CSV, Other
    email_source = Column(String(100), nullable=True)
    email_source_url = Column(String(500), nullable=True)

    # Website Analysis (JSON blob)
    website_analysis = Column(Text, nullable=True)

    # Lead Score (0–100 rules-based calculation)
    lead_score = Column(Integer, default=0, index=True)

    # Demo record indicator
    is_demo = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        """Serialize the lead to a dictionary for JSON API responses."""
        return {
            "is_marked": bool(self.is_marked),
            "lead_id": self.lead_id,
            "business_name": self.business_name,
            "owner_name": self.owner_name or "Unknown",
            "business_type": self.business_type,
            "city": self.city,
            "lead_source": self.lead_source,
            "phone": self.phone or "",
            "email": self.email or "",
            "email_source": self.email_source or "",
            "email_source_url": self.email_source_url or "",
            "email_status": self.email_status or ("Found" if self.email else "Not Analyzed"),
            "images": self.images,
            "current_website": self.current_website or "",
            "instagram": self.instagram or "",
            "facebook": self.facebook or "",
            "website_status": self.website_status or "Unknown",
            "preferred_contact_channel": self.preferred_contact_channel or "",
            "first_contact_date": self.first_contact_date.isoformat() if self.first_contact_date else None,
            "outreach_status": self.outreach_status or "Not Contacted",
            "response_status": self.response_status or "No Response",
            "interested_agreed": self.interested_agreed or "Pending",
            "website_requirement": self.website_requirement or "",
            "estimated_budget": self.estimated_budget or "",
            "proposal_status": self.proposal_status or "Not Sent",
            "deal_status": self.deal_status or "Open",
            "project_status": self.project_status or "Not Started",
            "next_followup_date": self.next_followup_date.isoformat() if self.next_followup_date else None,
            "remarks": self.remarks or "",
            "google_place_id": self.google_place_id or "",
            "google_maps_url": self.google_maps_url or self.source_url or "",
            "source_url": self.source_url or self.google_maps_url or "",
            "address": self.address or "",
            "rating": self.rating if self.rating is not None else self.google_rating,
            "google_rating": self.google_rating if self.google_rating is not None else self.rating,
            "review_count": self.review_count if self.review_count is not None else self.google_reviews,
            "google_reviews": self.google_reviews if self.google_reviews is not None else self.review_count,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "business_status": self.business_status or "OPERATIONAL",
            "email_verification_status": self.email_verification_status or "Not Checked",
            "website_analysis": self.website_analysis,
            "lead_score": self.lead_score or 0,
            "is_demo": bool(self.is_demo),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
