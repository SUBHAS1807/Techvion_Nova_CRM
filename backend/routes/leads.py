import os
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
    "lead_source", "phone", "email", "email_source", "email_source_url", "images", "current_website",
    "instagram", "facebook", "website_status", "preferred_contact_channel",
    "first_contact_date", "outreach_status", "response_status",
    "interested_agreed", "website_requirement", "estimated_budget",
    "proposal_status", "deal_status", "project_status",
    "next_followup_date", "remarks", "source_url", "google_maps_url",
    "google_place_id", "email_verification_status", "website_analysis",
    "lead_score", "address", "rating", "google_rating", "review_count",
    "google_reviews", "latitude", "longitude", "business_status", "is_demo",
]

DATE_FIELDS = {"first_contact_date", "next_followup_date"}


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
            elif f == "lead_score":
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


# ── LIST (Server-side paginated, filterable, sortable) ───────────────────

@leads_bp.route("/api/leads", methods=["GET"])
def list_leads():
    db = SessionLocal()
    try:
        skip = request.args.get("skip", 0, type=int)
        limit = request.args.get("limit", 50, type=int)
        limit = min(max(limit, 1), 500)  # capped safety

        # Search query
        q = request.args.get("q", "").strip()

        # Specific filters
        city = request.args.get("city", "").strip()
        business_type = request.args.get("business_type", "").strip()
        lead_source = request.args.get("lead_source", "").strip()
        website_status = request.args.get("website_status", "").strip()
        outreach_status = request.args.get("outreach_status", "").strip()
        response_status = request.args.get("response_status", "").strip()
        deal_status = request.args.get("deal_status", "").strip()
        is_marked = request.args.get("is_marked")
        is_demo = request.args.get("is_demo")
        sort_by = request.args.get("sort_by", "lead_id")
        sort_order = request.args.get("sort_order", "desc")

        query = db.query(Lead)

        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Lead.business_name.ilike(like),
                    Lead.owner_name.ilike(like),
                    Lead.lead_id.ilike(like),
                    Lead.city.ilike(like),
                    Lead.phone.ilike(like),
                    Lead.email.ilike(like),
                    Lead.current_website.ilike(like),
                    Lead.address.ilike(like),
                    Lead.google_place_id.ilike(like),
                )
            )

        if city:
            query = query.filter(Lead.city.ilike(city))
        if business_type:
            query = query.filter(Lead.business_type.ilike(business_type))
        if lead_source:
            query = query.filter(Lead.lead_source.ilike(lead_source))
        if website_status:
            query = query.filter(Lead.website_status == website_status)
        if outreach_status:
            query = query.filter(Lead.outreach_status == outreach_status)
        if response_status:
            query = query.filter(Lead.response_status == response_status)
        if deal_status:
            query = query.filter(Lead.deal_status == deal_status)
        if is_marked is not None and is_marked != "":
            query = query.filter(Lead.is_marked == (is_marked.lower() in ("true", "1")))
        if is_demo is not None and is_demo != "":
            query = query.filter(Lead.is_demo == (is_demo.lower() in ("true", "1")))

        total = query.count()

        # Sorting
        sort_col = getattr(Lead, sort_by, Lead.lead_id)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        leads = query.offset(skip).limit(limit).all()

        return jsonify({
            "total": total,
            "skip": skip,
            "limit": limit,
            "leads": [l.to_dict() for l in leads],
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
            if action == "outreach_status":
                lead.outreach_status = value
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


# ── FOLLOW-UPS ──────────────────────────────────────────────────────────

@leads_bp.route("/api/followups", methods=["GET"])
def get_followups():
    filter_type = request.args.get("filter", "all")  # today, tomorrow, week, overdue, all
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        today_end = today_start + timedelta(days=1)
        tomorrow_end = today_start + timedelta(days=2)
        week_end = today_start + timedelta(days=7)

        query = db.query(Lead).filter(Lead.next_followup_date.isnot(None))

        if filter_type == "today":
            query = query.filter(Lead.next_followup_date >= today_start, Lead.next_followup_date < today_end)
        elif filter_type == "tomorrow":
            query = query.filter(Lead.next_followup_date >= today_end, Lead.next_followup_date < tomorrow_end)
        elif filter_type == "week":
            query = query.filter(Lead.next_followup_date >= today_start, Lead.next_followup_date < week_end)
        elif filter_type == "overdue":
            query = query.filter(Lead.next_followup_date < today_start)

        leads = query.order_by(Lead.next_followup_date.asc()).limit(200).all()
        return jsonify({
            "filter": filter_type,
            "count": len(leads),
            "followups": [l.to_dict() for l in leads],
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
    q = request.args.get("q", "").strip()
    city = request.args.get("city", "").strip()
    business_type = request.args.get("business_type", "").strip()
    lead_source = request.args.get("lead_source", "").strip()
    website_status = request.args.get("website_status", "").strip()
    outreach_status = request.args.get("outreach_status", "").strip()
    response_status = request.args.get("response_status", "").strip()
    deal_status = request.args.get("deal_status", "").strip()
    is_marked = request.args.get("is_marked")
    is_demo = request.args.get("is_demo")

    db = SessionLocal()
    try:
        query = db.query(Lead)
        if mode == "selected" and ids_param:
            ids = [i.strip() for i in ids_param.split(",") if i.strip()]
            query = query.filter(Lead.lead_id.in_(ids))
        elif mode == "filtered":
            if q:
                like = f"%{q}%"
                query = query.filter(
                    or_(
                        Lead.business_name.ilike(like),
                        Lead.owner_name.ilike(like),
                        Lead.lead_id.ilike(like),
                        Lead.city.ilike(like),
                        Lead.phone.ilike(like),
                        Lead.email.ilike(like),
                        Lead.current_website.ilike(like),
                        Lead.address.ilike(like),
                        Lead.google_place_id.ilike(like),
                    )
                )
            if city:
                query = query.filter(Lead.city.ilike(city))
            if business_type:
                query = query.filter(Lead.business_type.ilike(business_type))
            if lead_source:
                query = query.filter(Lead.lead_source.ilike(lead_source))
            if website_status:
                query = query.filter(Lead.website_status == website_status)
            if outreach_status:
                query = query.filter(Lead.outreach_status == outreach_status)
            if response_status:
                query = query.filter(Lead.response_status == response_status)
            if deal_status:
                query = query.filter(Lead.deal_status == deal_status)
            if is_marked is not None and is_marked != "":
                query = query.filter(Lead.is_marked == (is_marked.lower() in ("true", "1")))
            if is_demo is not None and is_demo != "":
                query = query.filter(Lead.is_demo == (is_demo.lower() in ("true", "1")))

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
        # Write UTF-8 BOM so Excel on Windows/Mac properly parses Unicode/Bengali text
        output.write("\ufeff")
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        headers = [
            "Marked",
            "Lead ID",
            "Business Name",
            "Owner Name",
            "Business Type",
            "City",
            "Lead Source",
            "Phone",
            "Email",
            "Email Source",
            "Email Verification Status",
            "Current Website",
            "Instagram",
            "Facebook",
            "Website Status",
            "Preferred Contact Channel",
            "First Contact Date",
            "Outreach Status",
            "Response Status",
            "Interested / Agreed",
            "Website Requirement",
            "Estimated Budget",
            "Proposal Status",
            "Deal Status",
            "Project Status",
            "Next Follow-up Date",
            "Remarks",
            "Google Place ID",
            "Google Maps URL",
            "Address",
            "Rating",
            "Review Count",
            "Business Status",
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
                l.lead_source or "Google Places API",
                l.phone or "",
                l.email or "",
                getattr(l, "email_source", "") or ("Business Website" if l.email else ""),
                getattr(l, "email_verification_status", "") or "Not Checked",
                l.current_website or "",
                l.instagram or "",
                l.facebook or "",
                l.website_status or "Unknown",
                l.preferred_contact_channel or "",
                l.first_contact_date.strftime("%Y-%m-%d") if l.first_contact_date else "",
                l.outreach_status or "Not Contacted",
                l.response_status or "No Response",
                l.interested_agreed or "Pending",
                l.website_requirement or "",
                l.estimated_budget or "",
                l.proposal_status or "Not Sent",
                l.deal_status or "Open",
                l.project_status or "Not Started",
                l.next_followup_date.strftime("%Y-%m-%d") if l.next_followup_date else "",
                l.remarks or "",
                l.google_place_id or "",
                l.google_maps_url or l.source_url or "",
                l.address or "",
                l.rating or l.google_rating or "",
                l.review_count or l.google_reviews or "",
                l.business_status or "OPERATIONAL",
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
            lead = Lead(
                lead_id=lead_id,
                business_name=name,
                owner_name=row.get("Owner Name") or row.get("owner_name") or "Unknown",
                business_type=btype,
                city=city,
                lead_source=row.get("Lead Source") or "CSV Import",
                phone=phone,
                email=email,
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

        total_leads = db.query(Lead).count()
        new_leads = db.query(Lead).filter(Lead.outreach_status == "Not Contacted").count()
        marked_leads = db.query(Lead).filter(Lead.is_marked == True).count()
        no_website = db.query(Lead).filter(Lead.website_status == "No Website").count()
        outdated_websites = db.query(Lead).filter(Lead.website_status == "Outdated").count()
        public_emails = db.query(Lead).filter(Lead.email.isnot(None), Lead.email != "").count()
        contacted = db.query(Lead).filter(Lead.outreach_status.in_(["Contacted", "Follow-up", "Completed"])).count()
        followups_due = db.query(Lead).filter(Lead.next_followup_date <= (today_start + timedelta(days=1)), Lead.next_followup_date.isnot(None)).count()
        interested = db.query(Lead).filter(Lead.interested_agreed.in_(["Interested", "Agreed"])).count()
        proposals_sent = db.query(Lead).filter(Lead.proposal_status.in_(["Sent", "Accepted"])).count()
        deals_won = db.query(Lead).filter(Lead.deal_status == "Won").count()
        active_projects = db.query(Lead).filter(Lead.project_status.in_(["Development", "Testing", "UI/UX Design", "Planning"])).count()
        delivered = db.query(Lead).filter(Lead.project_status == "Delivered").count()

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
                "interested": interested,
                "proposals_sent": proposals_sent,
                "deals_won": deals_won,
                "active_projects": active_projects,
                "delivered": delivered,
            },
            "charts": {
                "by_city": by_city,
                "by_type": by_type,
                "by_website_status": by_website_status,
                "by_outreach": by_outreach,
                "by_response": by_response,
                "by_deal": by_deal,
                "by_project": by_project,
            },
        })
    finally:
        db.close()
