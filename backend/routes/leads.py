import os
import json
import time
import io
import csv
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc, asc

from backend.database import SessionLocal
from backend.models import (
    Lead,
    OutreachActivity,
    FollowUp,
    WebsiteAnalysisRecord,
)

leads_bp = Blueprint("leads", __name__)

# Machine website-status code -> human display label (exports & filters)
WS_CODE_LABELS = {
    "NO_WEBSITE": "No Website",
    "HAS_WEBSITE": "Has Website",
    "WEBSITE_INACCESSIBLE": "Website Inaccessible",
    "WEBSITE_UNKNOWN": "Unknown",
}


def _website_status_label(lead) -> str:
    """Prefer the machine code's label; fall back to legacy human value."""
    code = getattr(lead, "website_status_code", None)
    if code and code in WS_CODE_LABELS:
        return WS_CODE_LABELS[code]
    return lead.website_status or "Unknown"


def _next_lead_id(db: Session) -> str:
    """Generate the next TVN-XXXXXX id by finding the current max."""
    last = db.query(Lead.lead_id).order_by(Lead.lead_id.desc()).first()
    if last is None or not last[0]:
        return "TVN-000001"
    try:
        num = int(last[0].split("-")[1]) + 1
    except Exception:
        num = db.query(Lead).count() + 1
    return f"TVN-{num:06d}"


LEAD_FIELDS = [
    "is_marked", "business_name", "owner_name", "business_type", "city",
    "country", "country_code", "region", "state_province", "postal_code",
    "currency",
    "lead_source", "phone", "email", "email_source", "email_source_url", "images", "current_website",
    "instagram", "facebook", "website_status", "preferred_contact_channel",
    "first_contact_date", "outreach_status", "response_status",
    "interested_agreed", "website_requirement", "estimated_budget",
    "proposal_status", "deal_status", "project_status",
    "next_followup_date", "remarks", "source_url", "google_maps_url",
    "google_place_id", "email_verification_status", "email_status", "website_analysis",
    "lead_score", "address", "rating", "google_rating", "review_count",
    "google_reviews", "latitude", "longitude", "business_status", "is_demo",
    "contact_method", "last_contacted_date", "followup_count", "next_action",
]

DATE_FIELDS = {"first_contact_date", "next_followup_date", "last_contacted_date"}


def classify_followup_status(next_date: datetime | None, now: datetime | None = None) -> str:
    """Classify follow-up date into human status: Overdue, Due Today, Tomorrow, This Week, Upcoming, No Follow-Up Date."""
    if not next_date:
        return "No Follow-Up Date"
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Normalize comparison timezone
    if next_date.tzinfo is None:
        next_date = next_date.replace(tzinfo=timezone.utc)

    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_end = today_start + timedelta(days=1)
    tomorrow_end = today_start + timedelta(days=2)
    week_end = today_start + timedelta(days=7)

    if next_date < today_start:
        return "Overdue"
    elif today_start <= next_date < today_end:
        return "Due Today"
    elif today_end <= next_date < tomorrow_end:
        return "Tomorrow"
    elif today_end <= next_date < week_end:
        return "This Week"
    else:
        return "Upcoming"


def _parse_payload(data: dict) -> dict:
    """Whitelist and coerce incoming JSON into ORM-safe values."""
    clean = {}
    for f in LEAD_FIELDS:
        if f in data:
            val = data[f]
            if f in DATE_FIELDS:
                if isinstance(val, str) and val.strip():
                    try:
                        clean[f] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    except Exception:
                        clean[f] = None
                else:
                    clean[f] = val if isinstance(val, datetime) else None
            elif f == "is_marked" or f == "is_demo":
                clean[f] = bool(val)
            elif f in ("lead_score", "followup_count"):
                try:
                    clean[f] = int(val)
                except (ValueError, TypeError):
                    clean[f] = 0
            elif f in ("rating", "google_rating", "latitude", "longitude"):
                try:
                    clean[f] = float(val) if val is not None and val != "" else None
                except (ValueError, TypeError):
                    clean[f] = None
            elif f in ("review_count", "google_reviews"):
                try:
                    clean[f] = int(val) if val is not None and val != "" else None
                except (ValueError, TypeError):
                    clean[f] = None
            else:
                clean[f] = val
    return clean


def _apply_crm_filters(query, args: dict):
    """Apply combined multi-dimensional CRM filters to an ORM query."""
    # 1. Section Pipeline Filter
    section = (args.get("section") or "").strip().lower()
    if section == "collection":
        query = query.filter(Lead.outreach_status == "Not Contacted")
    elif section == "contacted":
        query = query.filter(Lead.outreach_status != "Not Contacted")
    elif section == "followup":
        query = query.filter(
            or_(
                Lead.next_followup_date.isnot(None),
                Lead.outreach_status.in_(["Follow-Up Required", "Contacted", "No Response", "Replied"])
            )
        )
    elif section == "interested":
        query = query.filter(
            or_(
                Lead.outreach_status.in_(["Interested", "Meeting Scheduled", "Proposal Sent", "Negotiation"]),
                Lead.interested_agreed.in_(["Interested", "Agreed"])
            )
        )
    elif section == "converted":
        query = query.filter(or_(Lead.outreach_status == "Converted", Lead.deal_status == "Won"))
    elif section == "lost":
        query = query.filter(or_(Lead.outreach_status == "Lost", Lead.deal_status == "Lost"))

    # 2. Search Query (q)
    q = (args.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Lead.business_name.ilike(like),
                Lead.owner_name.ilike(like),
                Lead.lead_id.ilike(like),
                Lead.city.ilike(like),
                Lead.state_province.ilike(like),
                Lead.region.ilike(like),
                Lead.country.ilike(like),
                Lead.phone.ilike(like),
                Lead.email.ilike(like),
                Lead.current_website.ilike(like),
                Lead.address.ilike(like),
                Lead.google_place_id.ilike(like),
            )
        )

    # 3. Follow-Up Timing Status Filter
    fu_status = (args.get("followup_status") or args.get("followup_filter") or args.get("filter") or "").strip().lower()
    if fu_status and fu_status != "all":
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        today_end = today_start + timedelta(days=1)
        tomorrow_end = today_start + timedelta(days=2)
        week_end = today_start + timedelta(days=7)

        if fu_status in ("today", "due_today", "due today"):
            query = query.filter(Lead.next_followup_date >= today_start, Lead.next_followup_date < today_end)
        elif fu_status == "overdue":
            query = query.filter(Lead.next_followup_date < today_start)
        elif fu_status == "tomorrow":
            query = query.filter(Lead.next_followup_date >= today_end, Lead.next_followup_date < tomorrow_end)
        elif fu_status in ("this_week", "this week", "week"):
            query = query.filter(Lead.next_followup_date >= today_start, Lead.next_followup_date < week_end)
        elif fu_status == "upcoming":
            query = query.filter(Lead.next_followup_date >= week_end)
        elif fu_status in ("no_date", "no_followup", "no follow-up date", "none"):
            query = query.filter(Lead.next_followup_date.is_(None))

    # 4. Contact Status / Outreach Status Filter
    outreach_status = (args.get("outreach_status") or args.get("contact_status") or "").strip()
    if outreach_status and outreach_status.lower() != "all":
        query = query.filter(Lead.outreach_status.ilike(outreach_status))

    # 5. Contact Method Filter
    contact_method = (args.get("contact_method") or "").strip()
    if contact_method and contact_method.lower() != "all":
        query = query.filter(Lead.contact_method.ilike(contact_method))

    # 6. Follow-Up Count Filter
    fu_count = (args.get("followup_count") or "").strip().lower()
    if fu_count and fu_count != "all":
        if fu_count in ("1", "first", "first follow-up", "first follow-ups"):
            query = query.filter(Lead.followup_count == 1)
        elif fu_count in ("2", "second", "second follow-up", "second follow-ups"):
            query = query.filter(Lead.followup_count == 2)
        elif fu_count in ("3", "third", "third follow-up", "third follow-ups"):
            query = query.filter(Lead.followup_count == 3)
        elif fu_count in ("4+", "4", "plus", "4+ follow-ups", "4+ followups"):
            query = query.filter(Lead.followup_count >= 4)

    # 7. Date Filter (today, yesterday, last_7_days, last_30_days, custom)
    date_filter = (args.get("date_filter") or "").strip().lower()
    if date_filter and date_filter != "all":
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        # Target date column: last_contacted_date preferred, then first_contact_date, then created_at
        date_col = func.coalesce(Lead.last_contacted_date, Lead.first_contact_date, Lead.created_at)

        if date_filter == "today":
            query = query.filter(date_col >= today_start)
        elif date_filter == "yesterday":
            query = query.filter(date_col >= today_start - timedelta(days=1), date_col < today_start)
        elif date_filter in ("last_7_days", "7days", "7_days"):
            query = query.filter(date_col >= today_start - timedelta(days=7))
        elif date_filter in ("last_30_days", "30days", "30_days"):
            query = query.filter(date_col >= today_start - timedelta(days=30))
        elif date_filter == "custom":
            start_str = args.get("start_date")
            end_str = args.get("end_date")
            if start_str:
                try:
                    s_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    query = query.filter(date_col >= s_dt)
                except Exception:
                    pass
            if end_str:
                try:
                    e_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")) + timedelta(days=1)
                    query = query.filter(date_col < e_dt)
                except Exception:
                    pass

    # 8. City, Business Type, Lead Source, Website Status
    city = (args.get("city") or "").strip()
    if city:
        query = query.filter(Lead.city.ilike(city))

    business_type = (args.get("business_type") or "").strip()
    if business_type:
        query = query.filter(Lead.business_type.ilike(business_type))

    lead_source = (args.get("lead_source") or "").strip()
    if lead_source:
        query = query.filter(Lead.lead_source.ilike(lead_source))

    website_status = (args.get("website_status") or "").strip()
    if website_status:
        machine_codes = {"NO_WEBSITE", "HAS_WEBSITE", "WEBSITE_INACCESSIBLE", "WEBSITE_UNKNOWN"}
        if website_status.upper() in machine_codes:
            query = query.filter(Lead.website_status_code == website_status.upper())
        else:
            query = query.filter(Lead.website_status == website_status)

    response_status = (args.get("response_status") or "").strip()
    if response_status:
        query = query.filter(Lead.response_status == response_status)

    deal_status = (args.get("deal_status") or "").strip()
    if deal_status:
        query = query.filter(Lead.deal_status == deal_status)

    is_marked = args.get("is_marked")
    if is_marked is not None and is_marked != "":
        query = query.filter(Lead.is_marked == (is_marked.lower() in ("true", "1")))

    is_demo = args.get("is_demo")
    if is_demo is not None and is_demo != "":
        query = query.filter(Lead.is_demo == (is_demo.lower() in ("true", "1")))

    return query


# ── LIST (Server-side paginated, filterable, sortable) ───────────────────

@leads_bp.route("/api/leads", methods=["GET"])
def list_leads():
    db = SessionLocal()
    try:
        skip = request.args.get("skip", 0, type=int)
        limit = request.args.get("limit", 50, type=int)
        limit = min(max(limit, 1), 500)  # capped safety

        sort_by = request.args.get("sort_by", "lead_id")
        sort_order = request.args.get("sort_order", "desc")

        query = db.query(Lead)
        query = _apply_crm_filters(query, request.args)

        total = query.count()

        # Sorting
        sort_col = getattr(Lead, sort_by, Lead.lead_id)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        leads = query.offset(skip).limit(limit).all()

        leads_list = []
        for l in leads:
            d = l.to_dict()
            d["followup_timing_status"] = classify_followup_status(l.next_followup_date)
            leads_list.append(d)

        return jsonify({
            "total": total,
            "skip": skip,
            "limit": limit,
            "leads": leads_list,
        })
    finally:
        db.close()


# ── GET ONE LEAD ────────────────────────────────────────────────────────

@leads_bp.route("/api/leads/<lead_id>", methods=["GET"])
def get_lead(lead_id: str):
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        return jsonify(lead.to_dict())
    finally:
        db.close()


# ── CREATE LEAD ─────────────────────────────────────────────────────────

@leads_bp.route("/api/leads", methods=["POST"])
def create_lead():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    required = ["business_name", "business_type", "city"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    db = SessionLocal()
    try:
        clean = _parse_payload(data)
        if "lead_source" not in clean or not clean["lead_source"]:
            clean["lead_source"] = "Manual Entry"
        if "website_status" not in clean or not clean["website_status"]:
            clean["website_status"] = "Good" if clean.get("current_website") else "No Website"

        lead_id = _next_lead_id(db)
        lead = Lead(**clean, lead_id=lead_id)
        db.add(lead)

        # Log timeline
        activity = OutreachActivity(
            lead_id=lead_id,
            activity_type="Lead Created",
            description=f"Lead created via {clean.get('lead_source')}",
            result="Created",
            created_by="User",
        )
        db.add(activity)

        db.commit()
        db.refresh(lead)
        return jsonify(lead.to_dict()), 201
    finally:
        db.close()


# ── UPDATE LEAD ─────────────────────────────────────────────────────────

@leads_bp.route("/api/leads/<lead_id>", methods=["PUT"])
def update_lead(lead_id: str):
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        data = request.get_json(force=True)
        clean = _parse_payload(data)

        # Detect status changes to record timeline
        old_outreach = lead.outreach_status
        old_response = lead.response_status
        old_deal = lead.deal_status

        for key, val in clean.items():
            setattr(lead, key, val)

        lead.updated_at = datetime.now(timezone.utc)

        # Add timeline entry if key milestones changed
        if clean.get("outreach_status") and clean["outreach_status"] != old_outreach:
            db.add(OutreachActivity(
                lead_id=lead_id,
                activity_type="Outreach Status Changed",
                description=f"Status changed from '{old_outreach}' to '{clean['outreach_status']}'",
                result=clean["outreach_status"],
                created_by="User",
            ))
        if clean.get("deal_status") and clean["deal_status"] != old_deal:
            db.add(OutreachActivity(
                lead_id=lead_id,
                activity_type="Deal Status Changed",
                description=f"Deal status changed from '{old_deal}' to '{clean['deal_status']}'",
                result=clean["deal_status"],
                created_by="User",
            ))

        db.commit()
        db.refresh(lead)
        return jsonify(lead.to_dict())
    finally:
        db.close()


# ── DELETE SECURITY & RATE LIMITING ─────────────────────────────────────

DELETE_PASSWORD_CONFIG = os.environ.get("DELETE_PASSWORD", "Tech@1807")
_failed_delete_attempts = {}
MAX_FAILED_DELETE_ATTEMPTS = 5
DELETE_LOCKOUT_SECONDS = 300  # 5 minutes lockout


def _verify_delete_auth(pw: str | None, client_ip: str) -> tuple[bool, str | None, int]:
    """
    Validates delete password against server configuration with brute-force protection.
    Returns: (is_valid, error_message, http_status_code)

    Security design:
    - A correct password ALWAYS clears the lockout and succeeds immediately.
    - The lockout only prevents further wrong-password attempts once the threshold is hit.
    - This ensures legitimate users are never permanently locked out by an attacker on
      the same shared IP, while still protecting against brute-force guessing.
    """
    import time
    now = time.time()
    attempts = _failed_delete_attempts.get(client_ip, [])
    recent_attempts = [t for t in attempts if now - t < DELETE_LOCKOUT_SECONDS]
    _failed_delete_attempts[client_ip] = recent_attempts

    expected_pw = (os.environ.get("DELETE_PASSWORD") or DELETE_PASSWORD_CONFIG).strip()
    submitted = (pw or "").strip()

    if not submitted:
        return False, "Deletion password is required.", 400

    # Correct password always wins -- clears any lockout immediately
    if submitted == expected_pw:
        _failed_delete_attempts.pop(client_ip, None)
        return True, None, 200

    # Wrong password: enforce lockout to block brute-force attempts
    if len(recent_attempts) >= MAX_FAILED_DELETE_ATTEMPTS:
        return False, "Too many incorrect attempts. Please try again later.", 429

    _failed_delete_attempts[client_ip].append(now)
    return False, "Incorrect deletion password.", 401


# ── DELETE LEAD (PASSWORD PROTECTED) ───────────────────────────────────

@leads_bp.route("/api/leads/<lead_id>", methods=["DELETE"])
@leads_bp.route("/api/leads/<lead_id>/delete", methods=["POST"])
def delete_lead(lead_id: str):
    data = request.get_json(force=True, silent=True) or {}
    password = data.get("password")
    client_ip = request.remote_addr or "127.0.0.1"

    valid, err_msg, status_code = _verify_delete_auth(password, client_ip)
    if not valid:
        return jsonify({"success": False, "error": err_msg}), status_code

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return jsonify({"success": False, "error": "Lead not found", "message": "Lead not found"}), 404

        biz_name = lead.business_name
        db.query(OutreachActivity).filter(OutreachActivity.lead_id == lead_id).delete()
        db.query(FollowUp).filter(FollowUp.lead_id == lead_id).delete()
        db.query(WebsiteAnalysisRecord).filter(WebsiteAnalysisRecord.lead_id == lead_id).delete()
        db.delete(lead)
        db.commit()

        return jsonify({
            "success": True,
            "deleted": 1,
            "lead_id": lead_id,
            "business_name": biz_name,
            "message": "Lead deleted successfully."
        }), 200
    finally:
        db.close()


# ── BULK DELETE (PASSWORD PROTECTED) ───────────────────────────────────

@leads_bp.route("/api/leads/bulk-delete", methods=["POST"])
def bulk_delete():
    data = request.get_json(force=True, silent=True) or {}
    password = data.get("password")
    client_ip = request.remote_addr or "127.0.0.1"

    valid, err_msg, status_code = _verify_delete_auth(password, client_ip)
    if not valid:
        return jsonify({"success": False, "error": err_msg}), status_code

    ids = data.get("ids") or data.get("lead_ids") or []
    if not ids:
        return jsonify({"success": False, "error": "No lead IDs provided"}), 400

    db = SessionLocal()
    try:
        db.query(OutreachActivity).filter(OutreachActivity.lead_id.in_(ids)).delete(synchronize_session=False)
        db.query(FollowUp).filter(FollowUp.lead_id.in_(ids)).delete(synchronize_session=False)
        db.query(WebsiteAnalysisRecord).filter(WebsiteAnalysisRecord.lead_id.in_(ids)).delete(synchronize_session=False)
        deleted = db.query(Lead).filter(Lead.lead_id.in_(ids)).delete(synchronize_session="fetch")
        db.commit()

        return jsonify({
            "success": True,
            "deleted": deleted,
            "message": f"{deleted} leads deleted successfully."
        }), 200
    finally:
        db.close()


# ── BULK ACTIONS ────────────────────────────────────────────────────────

@leads_bp.route("/api/leads/bulk-action", methods=["POST"])
def bulk_action():
    data = request.get_json(force=True) or {}
    ids = data.get("lead_ids", [])
    action = data.get("action")
    value = data.get("value")

    if not ids or not action:
        return jsonify({"error": "lead_ids and action are required"}), 400

    db = SessionLocal()
    try:
        leads = db.query(Lead).filter(Lead.lead_id.in_(ids)).all()
        count = 0
        for lead in leads:
            if action == "move_to_contacted":
                lead.outreach_status = "Contacted"
                if not lead.first_contact_date:
                    lead.first_contact_date = datetime.now(timezone.utc)
                lead.last_contacted_date = datetime.now(timezone.utc)
                if value:
                    lead.contact_method = value
                db.add(OutreachActivity(
                    lead_id=lead.lead_id,
                    activity_type="Moved to Contacted Section",
                    description=f"Lead moved to Contacted Leads (Contact Method: {lead.contact_method or 'General'})",
                    result="Contacted",
                    created_by="Bulk Action",
                ))
            elif action == "outreach_status":
                lead.outreach_status = value
                if value != "Not Contacted" and not lead.first_contact_date:
                    lead.first_contact_date = datetime.now(timezone.utc)
                if value != "Not Contacted":
                    lead.last_contacted_date = datetime.now(timezone.utc)
                db.add(OutreachActivity(
                    lead_id=lead.lead_id,
                    activity_type="Outreach Status Updated (Bulk)",
                    description=f"Updated outreach status to {value}",
                    result=value,
                    created_by="Bulk Action",
                ))
            elif action == "response_status":
                lead.response_status = value
            elif action == "followup_date":
                if value:
                    try:
                        f_date = datetime.fromisoformat(value)
                        lead.next_followup_date = f_date
                        db.add(FollowUp(lead_id=lead.lead_id, scheduled_date=f_date, notes="Set via bulk action"))
                    except Exception:
                        pass
                else:
                    lead.next_followup_date = None
            elif action == "contact_method":
                lead.contact_method = value
            elif action == "mark":
                lead.is_marked = bool(value)
            elif action == "website_requirement":
                lead.website_requirement = value
            lead.updated_at = datetime.now(timezone.utc)
            count += 1

        db.commit()
        return jsonify({"ok": True, "updated": count})
    finally:
        db.close()


# ── TIMELINE / OUTREACH ─────────────────────────────────────────────────

@leads_bp.route("/api/leads/<lead_id>/timeline", methods=["GET"])
def get_timeline(lead_id: str):
    db = SessionLocal()
    try:
        activities = db.query(OutreachActivity).filter(
            OutreachActivity.lead_id == lead_id
        ).order_by(OutreachActivity.date.desc()).all()
        return jsonify([a.to_dict() for a in activities])
    finally:
        db.close()


@leads_bp.route("/api/leads/<lead_id>/timeline", methods=["POST"])
@leads_bp.route("/api/outreach", methods=["POST"])
def add_timeline_entry(lead_id: str = None):
    data = request.get_json(force=True) or {}
    target_id = lead_id or data.get("lead_id")
    if not target_id:
        return jsonify({"error": "lead_id is required"}), 400

    activity_type = data.get("activity_type") or "Outreach Log"
    description = data.get("description") or ""
    result = data.get("result") or ""
    created_by = data.get("created_by") or "User"

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == target_id).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        act = OutreachActivity(
            lead_id=target_id,
            activity_type=activity_type,
            description=description,
            result=result,
            created_by=created_by,
        )
        db.add(act)

        # Update lead contact dates/statuses if relevant
        if "contact" in activity_type.lower() or "call" in activity_type.lower() or "email" in activity_type.lower():
            if not lead.first_contact_date:
                lead.first_contact_date = datetime.now(timezone.utc)
            if lead.outreach_status == "Not Contacted":
                lead.outreach_status = "Contacted"
        if data.get("next_followup_date"):
            try:
                f_date = datetime.fromisoformat(data["next_followup_date"])
                lead.next_followup_date = f_date
                db.add(FollowUp(lead_id=target_id, scheduled_date=f_date, notes=description))
            except Exception:
                pass

        lead.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(act)
        return jsonify(act.to_dict()), 201
    finally:
        db.close()


# ── SCHEDULE FOLLOW-UP ──────────────────────────────────────────────────

@leads_bp.route("/api/leads/<lead_id>/schedule-followup", methods=["POST"])
def schedule_followup(lead_id: str):
    data = request.get_json(force=True) or {}
    f_date_str = data.get("followup_date") or data.get("next_followup_date")
    f_time_str = data.get("followup_time", "09:00")
    method = data.get("contact_method") or "Phone Call"
    notes = data.get("notes") or data.get("followup_note") or ""
    next_action = data.get("next_action") or ""
    outreach_status = data.get("outreach_status")

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        dt = None
        if f_date_str:
            try:
                full_str = f"{f_date_str}T{f_time_str}:00" if "T" not in f_date_str else f_date_str
                dt = datetime.fromisoformat(full_str.replace("Z", "+00:00"))
            except Exception:
                try:
                    dt = datetime.fromisoformat(f_date_str)
                except Exception:
                    dt = None

        now_utc = datetime.now(timezone.utc)

        lead.next_followup_date = dt
        lead.contact_method = method
        if next_action:
            lead.next_action = next_action
        lead.last_contacted_date = now_utc
        lead.followup_count = (lead.followup_count or 0) + 1

        if not lead.first_contact_date:
            lead.first_contact_date = now_utc

        if outreach_status:
            lead.outreach_status = outreach_status
        elif lead.outreach_status in ("Not Contacted", None, ""):
            lead.outreach_status = "Follow-Up Required"

        if notes:
            lead.remarks = notes if not lead.remarks else f"{lead.remarks}\n[{now_utc.strftime('%Y-%m-%d')}] {notes}"

        lead.updated_at = now_utc

        if dt:
            db.add(FollowUp(
                lead_id=lead_id,
                scheduled_date=dt,
                status="Pending",
                notes=notes or next_action or f"Follow-up via {method}"
            ))

        act = OutreachActivity(
            lead_id=lead_id,
            activity_type=f"Follow-Up Scheduled ({method})",
            description=f"Follow-up scheduled for {dt.strftime('%Y-%m-%d %H:%M') if dt else 'unspecified date'}. Note: {notes}. Next Action: {next_action}",
            result=lead.outreach_status,
            created_by="User",
        )
        db.add(act)

        db.commit()
        db.refresh(lead)

        res_dict = lead.to_dict()
        res_dict["followup_timing_status"] = classify_followup_status(lead.next_followup_date)
        return jsonify(res_dict), 200
    finally:
        db.close()


# ── FOLLOW-UPS ──────────────────────────────────────────────────────────

@leads_bp.route("/api/followups", methods=["GET"])
def get_followups():
    db = SessionLocal()
    try:
        skip = request.args.get("skip", 0, type=int)
        limit = request.args.get("limit", 100, type=int)
        limit = min(max(limit, 1), 500)

        # Clone request args to apply section = followup if no section provided
        args = dict(request.args)
        if "section" not in args and "followup_status" not in args and "filter" not in args:
            args["section"] = "followup"

        query = db.query(Lead)
        query = _apply_crm_filters(query, args)

        sort_by = request.args.get("sort_by", "next_followup_date")
        sort_order = request.args.get("sort_order", "asc")
        sort_col = getattr(Lead, sort_by, Lead.next_followup_date)

        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_col))
        else:
            query = query.order_by(asc(sort_col))

        total = query.count()
        leads = query.offset(skip).limit(limit).all()

        result_leads = []
        for l in leads:
            d = l.to_dict()
            d["followup_timing_status"] = classify_followup_status(l.next_followup_date)
            result_leads.append(d)

        return jsonify({
            "total": total,
            "skip": skip,
            "limit": limit,
            "count": len(result_leads),
            "filter": args.get("followup_status") or args.get("filter") or "all",
            "followups": result_leads,
            "leads": result_leads,
        })
    finally:
        db.close()


# ── CSV EXPORT ──────────────────────────────────────────────────────────

# ── EXPORT LEADS (CSV & EXCEL .XLSX) ────────────────────────────────────

@leads_bp.route("/api/leads/export", methods=["GET"])
@leads_bp.route("/api/leads/export/csv", methods=["GET"])
@leads_bp.route("/api/leads/export/excel", methods=["GET"])
def export_leads():
    # Detect format from URL path or query parameter
    if request.path.endswith("/excel"):
        export_format = "excel"
    elif request.path.endswith("/csv"):
        export_format = "csv"
    else:
        export_format = request.args.get("format", "csv").lower()

    mode = request.args.get("mode", "all")  # all, filtered, selected
    ids_param = request.args.get("ids", "")

    db = SessionLocal()
    try:
        query = db.query(Lead)
        if mode == "selected" and ids_param:
            ids = [i.strip() for i in ids_param.split(",") if i.strip()]
            query = query.filter(Lead.lead_id.in_(ids))
        else:
            query = _apply_crm_filters(query, request.args)

        leads = query.order_by(Lead.lead_id.asc()).all()
        date_str = datetime.now().strftime("%Y-%m-%d")

        # ── Handle Excel (.xlsx) Export ─────────────────────────────────
        if export_format in ("excel", "xlsx"):
            from backend.routes.export_excel import create_excel_report
            xlsx_bytes = create_excel_report(leads)
            filename = f"TechvionNova_Leads_{date_str}.xlsx"
            return Response(
                xlsx_bytes,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-Total-Count": str(len(leads)),
                },
            )

        # ── Handle CSV Export (with UTF-8 BOM) ──────────────────────────
        output = io.StringIO()
        # Write UTF-8 BOM so Excel on Windows/Mac properly parses Unicode text
        output.write("\ufeff")
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        headers = [
            "Marked",
            "Lead ID",
            "Business Name",
            "Owner Name",
            "Business Type",
            "City",
            "State / Province",
            "Country",
            "Lead Source",
            "Phone",
            "Email",
            "Current Website",
            "Website Status",
            "Contact Status (Outreach)",
            "Contact Method",
            "Response Status",
            "Follow-Up Date",
            "Follow-Up Count",
            "Last Contacted",
            "Next Action",
            "Remarks",
            "Google Place ID",
            "Google Maps URL",
            "Address",
            "Rating",
            "Review Count",
            "Lead Score",
            "Created At",
        ]
        writer.writerow(headers)

        for l in leads:
            writer.writerow([
                "Yes" if l.is_marked else "No",
                l.lead_id,
                l.business_name or "",
                l.owner_name or "Unknown",
                l.business_type or "",
                l.city or "",
                l.state_province or l.region or "",
                l.country or "",
                l.lead_source or "Google Places API",
                l.phone or "",
                l.email or "",
                l.current_website or "",
                _website_status_label(l),
                l.outreach_status or "Not Contacted",
                l.contact_method or "",
                l.response_status or "No Response",
                l.next_followup_date.strftime("%Y-%m-%d %H:%M") if l.next_followup_date else "",
                l.followup_count or 0,
                l.last_contacted_date.strftime("%Y-%m-%d %H:%M") if l.last_contacted_date else "",
                l.next_action or "",
                l.remarks or "",
                l.google_place_id or "",
                l.google_maps_url or l.source_url or "",
                l.address or "",
                l.rating or l.google_rating or "",
                l.review_count or l.google_reviews or "",
                l.lead_score or 0,
                l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "",
            ])

        csv_content = output.getvalue()
        filename = f"TechvionNova_Leads_{date_str}.csv"
        return Response(
            csv_content.encode("utf-8-sig"),
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Total-Count": str(len(leads)),
            },
        )
    finally:
        db.close()


# ── QUALIFIED WORLDWIDE EXPORT (email-verified leads only) ──────────────

@leads_bp.route("/api/leads/export/global", methods=["GET"])
@leads_bp.route("/api/leads/export/global/csv", methods=["GET"])
@leads_bp.route("/api/leads/export/global/excel", methods=["GET"])
def export_global_qualified():
    """
    Export ONLY qualified worldwide leads — businesses that carry a real,
    publicly discovered email address. NO EMAIL = NOT EXPORTED. Ever.
    """
    if request.path.endswith("/excel"):
        export_format = "excel"
    else:
        export_format = "csv"

    country = request.args.get("country", "").strip()
    db = SessionLocal()
    try:
        query = db.query(Lead).filter(
            Lead.email.isnot(None), Lead.email != ""
        )
        if country:
            query = query.filter(Lead.country_code == country.upper())
        leads = query.order_by(Lead.country.asc(), Lead.lead_id.asc()).all()
        date_str = datetime.now().strftime("%Y-%m-%d")

        if export_format == "excel":
            from backend.routes.export_excel import create_excel_report
            xlsx_bytes = create_excel_report(leads)
            filename = f"TechvionNova_Global_Leads_{date_str}.xlsx"
            return Response(
                xlsx_bytes,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "X-Total-Count": str(len(leads)),
                },
            )

        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "Lead ID", "Business Name", "Business Type", "Email",
            "Email Source Page", "Phone", "Website",
            "City", "State / Province", "Region", "Country",
            "Postal Code", "Currency", "Address",
            "Website Status",
            "Google Rating", "Reviews", "Google Maps URL",
            "Instagram / Socials", "Opening Hours",
            "Lead Score", "Exported At",
        ])
        exported_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        for l in leads:
            socials = []
            if l.other_socials:
                try:
                    socials = json.loads(l.other_socials)
                except Exception:
                    socials = []
            hours = []
            if l.opening_hours:
                try:
                    hours = json.loads(l.opening_hours)
                except Exception:
                    hours = []
            writer.writerow([
                l.lead_id,
                l.business_name or "",
                l.business_type or "",
                l.email or "",
                getattr(l, "email_source_url", "") or "",
                l.phone or "",
                l.current_website or "",
                l.city or "",
                l.state_province or "",
                l.region or "",
                l.country or "",
                l.postal_code or "",
                l.currency or "",
                l.address or "",
                _website_status_label(l),
                l.rating or l.google_rating or "",
                l.review_count or l.google_reviews or "",
                l.google_maps_url or l.source_url or "",
                " | ".join(socials),
                " | ".join(hours),
                l.lead_score or 0,
                exported_at,
            ])

        csv_content = output.getvalue()
        filename = f"TechvionNova_Global_Leads_{date_str}.csv"
        return Response(
            csv_content.encode("utf-8-sig"),
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Total-Count": str(len(leads)),
            },
        )
    finally:
        db.close()


# ── CSV IMPORT ──────────────────────────────────────────────────────────

@leads_bp.route("/api/leads/import-csv", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return jsonify({"error": "No CSV file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "File must be a .csv"}), 400

    content = file.stream.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    db = SessionLocal()
    total_rows = 0
    imported = 0
    duplicates = 0
    failed = 0

    try:
        for row in reader:
            total_rows += 1
            name = (row.get("Business Name") or row.get("business_name") or row.get("name") or "").strip()
            city = (row.get("City") or row.get("city") or "Unknown").strip()
            btype = (row.get("Business Type") or row.get("business_type") or row.get("type") or "Cafe").strip()
            phone = (row.get("Phone") or row.get("phone") or "").strip()
            email = (row.get("Email") or row.get("email") or "").strip()
            website = (row.get("Website") or row.get("current_website") or row.get("website") or "").strip()
            place_id = (row.get("Google Place ID") or row.get("google_place_id") or "").strip()

            if not name:
                failed += 1
                continue

            # Duplicate check
            is_dup = False
            if place_id:
                if db.query(Lead).filter(Lead.google_place_id == place_id).first():
                    is_dup = True
            if not is_dup and phone:
                digits = re.sub(r"\D", "", phone)
                if len(digits) >= 7:
                    all_phones = [re.sub(r"\D", "", p[0]) for p in db.query(Lead.phone).all() if p[0]]
                    if digits in all_phones:
                        is_dup = True
            if not is_dup and website:
                raw_dom = urlparse(website if "://" in website else "http://" + website).netloc.lower()
                all_webs = [urlparse(w[0] if "://" in w[0] else "http://" + w[0]).netloc.lower() for w in db.query(Lead.current_website).all() if w[0]]
                if raw_dom and raw_dom in all_webs:
                    is_dup = True

            if is_dup:
                duplicates += 1
                continue

            lead_id = _next_lead_id(db)
            # Only keep syntactically valid, actually-provided emails; never fabricate
            email_valid = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)) if email else False
            lead = Lead(
                lead_id=lead_id,
                business_name=name,
                owner_name=row.get("Owner Name") or row.get("owner_name") or "Unknown",
                business_type=btype,
                city=city,
                lead_source=row.get("Lead Source") or "CSV Import",
                phone=phone,
                email=email if email_valid else "",
                email_source="CSV Import" if email_valid else None,
                email_status="Found" if email_valid else ("Invalid" if email else "Not Analyzed"),
                email_verification_status="Valid Format" if email_valid else ("Invalid Format" if email else "Not Checked"),
                current_website=website,
                website_status=row.get("Website Status") or ("Good" if website else "No Website"),
                outreach_status=row.get("Outreach Status") or "Not Contacted",
                response_status=row.get("Response Status") or "No Response",
                remarks=row.get("Remarks") or "Imported via CSV",
            )
            db.add(lead)
            imported += 1
            db.flush()

        db.commit()
    finally:
        db.close()

    return jsonify({
        "total_rows": total_rows,
        "valid": imported + duplicates,
        "invalid": failed,
        "duplicates": duplicates,
        "imported": imported,
        "failed": failed,
    })


# ── DASHBOARD / ANALYTICS ───────────────────────────────────────────────

@leads_bp.route("/api/analytics", methods=["GET"])
def get_analytics():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        today_end = today_start + timedelta(days=1)

        total_leads = db.query(Lead).count()
        new_leads = db.query(Lead).filter(Lead.outreach_status == "Not Contacted").count()
        contacted = db.query(Lead).filter(Lead.outreach_status != "Not Contacted").count()
        marked_leads = db.query(Lead).filter(Lead.is_marked == True).count()
        no_website = db.query(Lead).filter(or_(Lead.website_status == "No Website", Lead.website_status_code == "NO_WEBSITE")).count()
        outdated_websites = db.query(Lead).filter(Lead.website_status == "Outdated").count()
        public_emails = db.query(Lead).filter(Lead.email.isnot(None), Lead.email != "").count()

        followups_due = db.query(Lead).filter(Lead.next_followup_date >= today_start, Lead.next_followup_date < today_end).count()
        overdue_followups = db.query(Lead).filter(Lead.next_followup_date < today_start).count()

        interested = db.query(Lead).filter(
            or_(
                Lead.outreach_status.in_(["Interested", "Meeting Scheduled", "Proposal Sent", "Negotiation"]),
                Lead.interested_agreed.in_(["Interested", "Agreed"])
            )
        ).count()

        meetings = db.query(Lead).filter(Lead.outreach_status == "Meeting Scheduled").count()
        proposals_sent = db.query(Lead).filter(or_(Lead.proposal_status.in_(["Sent", "Accepted"]), Lead.outreach_status == "Proposal Sent")).count()
        converted = db.query(Lead).filter(or_(Lead.outreach_status == "Converted", Lead.deal_status == "Won")).count()
        lost_leads = db.query(Lead).filter(or_(Lead.outreach_status == "Lost", Lead.deal_status == "Lost")).count()

        deals_won = converted
        active_projects = db.query(Lead).filter(Lead.project_status.in_(["Development", "Testing", "UI/UX Design", "Planning"])).count()
        delivered = db.query(Lead).filter(Lead.project_status == "Delivered").count()

        funnel = [
            {"stage": "Total Leads", "count": total_leads, "pct": 100.0},
            {"stage": "Contacted", "count": contacted, "pct": round((contacted / total_leads * 100), 1) if total_leads else 0.0},
            {"stage": "Interested", "count": interested, "pct": round((interested / total_leads * 100), 1) if total_leads else 0.0},
            {"stage": "Converted", "count": converted, "pct": round((converted / total_leads * 100), 1) if total_leads else 0.0},
        ]

        # Breakdown aggregations
        def count_by_group(col):
            res = db.query(col, func.count(col)).filter(col.isnot(None), col != "").group_by(col).all()
            return [{"name": r[0], "count": r[1]} for r in res]

        by_city = count_by_group(Lead.city)[:10]
        by_type = count_by_group(Lead.business_type)[:10]
        by_website_status = count_by_group(Lead.website_status)
        by_outreach = count_by_group(Lead.outreach_status)
        by_response = count_by_group(Lead.response_status)
        by_deal = count_by_group(Lead.deal_status)
        by_project = count_by_group(Lead.project_status)
        by_country = count_by_group(Lead.country)[:12]

        # Worldwide discovery funnel (real data from discovered_businesses)
        global_funnel = {"discovered": 0, "websites": 0, "emails": 0,
                         "qualified": 0, "no_email": 0, "errors": 0}
        try:
            from backend.models import DiscoveredBusiness
            d = DiscoveredBusiness
            global_funnel = {
                "discovered": db.query(d).count(),
                "websites": db.query(d).filter(d.has_website.is_(True)).count(),
                "emails": db.query(d).filter(d.email_status == "EMAIL_FOUND").count(),
                "qualified": db.query(d).filter(d.lead_id.isnot(None)).count(),
                "no_email": db.query(d).filter(d.email_status == "EMAIL_NOT_FOUND").count(),
                "errors": db.query(d).filter(
                    d.email_status.in_(["ERROR", "WEBSITE_UNAVAILABLE", "INVALID_EMAIL"])).count(),
                # 🎯 Website-opportunity metrics
                "businesses_without_website": db.query(d).filter(
                    d.website_status == "NO_WEBSITE").count(),
                "emails_found_without_website": db.query(d).filter(
                    d.website_status == "NO_WEBSITE",
                    d.email_status == "EMAIL_FOUND").count(),
                "opportunity_leads": db.query(d).filter(
                    d.website_status == "NO_WEBSITE",
                    d.lead_id.isnot(None)).count(),
            }
        except Exception:
            pass

        return jsonify({
            "cards": {
                "total_leads": total_leads,
                "new_leads": new_leads,
                "marked_leads": marked_leads,
                "no_website": no_website,
                "outdated_websites": outdated_websites,
                "public_emails": public_emails,
                "contacted": contacted,
                "followups_due": followups_due,
                "followups_due_today": followups_due,
                "overdue_followups": overdue_followups,
                "interested": interested,
                "interested_leads": interested,
                "meetings": meetings,
                "proposals_sent": proposals_sent,
                "converted_clients": converted,
                "deals_won": deals_won,
                "lost_leads": lost_leads,
                "active_projects": active_projects,
                "delivered": delivered,
            },
            "funnel": funnel,
            "charts": {
                "by_city": by_city,
                "by_type": by_type,
                "by_website_status": by_website_status,
                "by_outreach": by_outreach,
                "by_response": by_response,
                "by_deal": by_deal,
                "by_project": by_project,
                "by_country": by_country,
            },
            "global_funnel": global_funnel,
        })
    finally:
        db.close()
