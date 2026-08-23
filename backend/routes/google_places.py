import os
import re
import time
import json
import threading
from urllib.parse import urlparse
from datetime import datetime, timezone

import requests
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv

from backend.database import SessionLocal
from backend.models import (
    Lead,
    OutreachActivity,
    CollectionJob,
    CollectionLog,
    ApiUsageRecord,
)

# Load .env variables
load_dotenv()

google_places_bp = Blueprint("google_places", __name__)

KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "google_api_key.txt")
PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.addressComponents,"
    "places.nationalPhoneNumber,places.internationalPhoneNumber,"
    "places.websiteUri,places.rating,places.userRatingCount,places.businessStatus,"
    "places.googleMapsUri,places.location,nextPageToken"
)

CITIES = [
    "Kolkata", "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai",
    "Pune", "Surat", "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane",
    "Bhopal", "Visakhapatnam", "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra",
    "Nashik", "Faridabad", "Meerut", "Rajkot", "Varanasi", "Srinagar", "Aurangabad",
    "Dhanbad", "Amritsar", "Navi Mumbai", "Allahabad", "Ranchi", "Howrah", "Coimbatore",
    "Jabalpur", "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur", "Kota",
    "Guwahati", "Chandigarh", "Solapur", "Hubballi", "Tiruchirappalli", "Bareilly",
    "Mysuru", "Noida", "Gurugram", "Mohali", "Dehradun", "Kochi", "Goa", "Manali",
    "Shimla", "Udaipur", "Bhubaneswar",
]

BUSINESS_TYPES = [
    "Cafe", "Coffee Shop", "Bakery", "Restaurant", "Bistro", "Cloud Kitchen",
    "Fast Food Restaurant", "Tea Shop", "Dessert Shop", "Salon", "Spa", "Gym",
    "Yoga Studio", "Dental Clinic", "Hospital", "Diagnostic Lab", "Pharmacy",
    "Coaching Center", "Play School", "Real Estate Agency", "Construction Company",
    "Interior Designer", "Hotel", "Resort", "Hostel", "Banquet Hall", "Event Planner",
    "Wedding Photographer", "Boutique", "Clothing Store", "Jewellery Store",
    "Electronics Store", "Furniture Store", "Mobile Phone Shop", "Car Dealer",
    "Bike Dealer", "Car Service Center", "Travel Agency", "Packers and Movers",
    "CA Firm", "Law Firm", "Insurance Agent", "Digital Marketing Agency",
    "IT Company", "Printing Press", "Sweet Shop", "Ice Cream Parlor", "Food Truck",
]

# Track active background jobs
active_jobs = {}


def get_api_key() -> str | None:
    """Retrieve Google Places API Key from environment or local key file."""
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if key and key.strip() and not key.startswith("YOUR_API_KEY"):
        return key.strip()
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "r") as f:
                k = f.read().strip()
                if k and not k.startswith("YOUR_API_KEY"):
                    return k
        except Exception:
            pass
    return None


def mask_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        raw = url.strip()
        if not re.match(r"^https?://", raw, re.I):
            raw = "https://" + raw
        parsed = urlparse(raw)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or None
    except Exception:
        return None


def clean_phone_digits(phone: str | None) -> str:
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)


def _next_lead_id(db) -> str:
    """Generate next unique TVN-XXXXXX Lead ID."""
    last = db.query(Lead.lead_id).order_by(Lead.lead_id.desc()).first()
    if last is None or not last[0]:
        return "TVN-000001"
    try:
        num = int(last[0].split("-")[1]) + 1
    except Exception:
        num = db.query(Lead).count() + 1
    return f"TVN-{num:06d}"


def record_api_usage(endpoint: str, req_type: str = "search", status_code: int = 200):
    """Log API usage into SQLite."""
    try:
        db = SessionLocal()
        record = ApiUsageRecord(
            endpoint=endpoint,
            request_type=req_type,
            status_code=status_code,
            cost_estimate=0.032 if "searchText" in endpoint else 0.017,
        )
        db.add(record)
        db.commit()
        db.close()
    except Exception:
        pass


def translate_google_error(status_code: int, err_data: dict | str) -> str:
    """Convert raw Google Cloud API error responses into clear, actionable messages."""
    if isinstance(err_data, dict):
        error_obj = err_data.get("error", {})
        message = error_obj.get("message", "")
        status = error_obj.get("status", "")
        details = error_obj.get("details", [])
    else:
        message = str(err_data)
        status = ""
        details = []

    if status_code == 400:
        return f"Invalid request parameters: {message or 'Check search query and field mask.'}"
    if status_code == 401 or "API_KEY_INVALID" in str(err_data) or status == "UNAUTHENTICATED":
        return "API key invalid. Please verify your Google Cloud API key."
    if status_code == 403:
        if "SERVICE_DISABLED" in str(err_data) or "Places API has not been used" in message or "not enabled" in message.lower():
            return "Places API (New) is not enabled in your Google Cloud Console. Go to APIs & Services → Library and enable 'Places API (New)'."
        if "BILLING_NOT_ENABLED" in str(err_data) or "billing" in message.lower():
            return "Billing/account configuration required. Google Places API requires an active billing account linked to the project in Google Cloud Console."
        return f"Permission denied (403): {message or 'API key does not have access to Places API (New).'}"
    if status_code == 429 or "RESOURCE_EXHAUSTED" in status:
        return "Quota exceeded (429). Daily or per-minute rate limits reached on Google Cloud."
    return f"Google Places API returned status {status_code}: {message or 'Unknown error'}"


def check_duplicate_lead(db, place_data: dict) -> tuple[bool, Lead | None, str]:
    """
    Check 5-level duplicate criteria:
    1. Google Place ID
    2. Website domain
    3. Phone digits (at least 7 digits match)
    4. Email
    5. Business Name + City
    Returns (is_duplicate, existing_lead_obj, match_reason)
    """
    place_id = place_data.get("google_place_id") or place_data.get("id")
    if place_id:
        existing = db.query(Lead).filter(Lead.google_place_id == place_id).first()
        if existing:
            return True, existing, f"Matched Google Place ID ({place_id})"

    website = place_data.get("current_website") or place_data.get("websiteUri")
    norm_dom = normalize_domain(website)
    if norm_dom:
        all_leads_web = db.query(Lead).filter(Lead.current_website.isnot(None)).all()
        for l in all_leads_web:
            if l.current_website and normalize_domain(l.current_website) == norm_dom:
                return True, l, f"Matched Website Domain ({norm_dom})"

    phone = place_data.get("phone") or place_data.get("nationalPhoneNumber") or place_data.get("internationalPhoneNumber")
    digits = clean_phone_digits(phone)
    if digits and len(digits) >= 7:
        all_phones = db.query(Lead).filter(Lead.phone.isnot(None)).all()
        for l in all_phones:
            l_digits = clean_phone_digits(l.phone)
            if l_digits and (l_digits == digits or digits.endswith(l_digits[-10:]) or l_digits.endswith(digits[-10:])):
                return True, l, f"Matched Phone ({phone})"

    email = place_data.get("email")
    if email and email.strip():
        existing = db.query(Lead).filter(Lead.email.ilike(email.strip())).first()
        if existing:
            return True, existing, f"Matched Email ({email})"

    biz_name = (place_data.get("business_name") or (place_data.get("displayName") or {}).get("text") or "").strip()
    city = (place_data.get("city") or "").strip()
    if biz_name and city:
        existing = db.query(Lead).filter(
            Lead.business_name.ilike(biz_name),
            Lead.city.ilike(city),
        ).first()
        if existing:
            return True, existing, f"Matched Business Name '{biz_name}' in {city}"

    return False, None, ""


# ══════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════

@google_places_bp.route("/api/google-places/status", methods=["GET"])
@google_places_bp.route("/api/collect/meta", methods=["GET"])
def get_status():
    """Check API key status and return metadata."""
    key = get_api_key()
    db = SessionLocal()
    try:
        total_api_calls = db.query(ApiUsageRecord).count()
        total_leads = db.query(Lead).count()
    finally:
        db.close()

    return jsonify({
        "configured": key is not None,
        "api_key_configured": key is not None,
        "masked_key": mask_key(key),
        "cities": CITIES,
        "business_types": BUSINESS_TYPES,
        "total_api_calls": total_api_calls,
        "total_leads": total_leads,
    })


@google_places_bp.route("/api/google-places/test", methods=["POST"])
def test_connection():
    """Verify that Google Places API key is valid, enabled, and billing is active."""
    api_key = get_api_key()
    if not api_key:
        return jsonify({
            "ok": False,
            "error": "Google Places API key is not configured.",
            "reason": "Missing GOOGLE_MAPS_API_KEY in environment/.env",
        }), 400

    try:
        resp = requests.post(
            PLACES_TEXT_SEARCH_URL,
            json={"textQuery": "cafe", "pageSize": 1},
            headers={
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.id,places.displayName",
            },
            timeout=10,
        )
        record_api_usage("places:searchText", "test", resp.status_code)

        if resp.status_code == 200:
            return jsonify({
                "ok": True,
                "message": "✓ Google Places API connection successful",
                "status": "active",
            })

        err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        human_error = translate_google_error(resp.status_code, err_json)
        return jsonify({
            "ok": False,
            "error": "✗ Google Places API connection failed",
            "reason": human_error,
            "status_code": resp.status_code,
        }), 200  # Return 200 with ok: false for frontend UI handling

    except requests.exceptions.Timeout:
        return jsonify({
            "ok": False,
            "error": "✗ Connection timed out",
            "reason": "Request to Google Places API timed out after 10s. Check internet connection.",
        }), 200
    except requests.exceptions.RequestException as e:
        return jsonify({
            "ok": False,
            "error": "✗ Network error",
            "reason": str(e),
        }), 200


@google_places_bp.route("/api/google-places/config", methods=["POST"])
@google_places_bp.route("/api/collect/config", methods=["POST"])
def save_api_key():
    """Save API key to .env and local key file."""
    data = request.get_json(force=True) or {}
    key = (data.get("api_key") or data.get("apiKey") or "").strip()
    if not key:
        return jsonify({"error": "API key is required"}), 400

    # Save to KEY_FILE
    try:
        with open(KEY_FILE, "w") as f:
            f.write(key)
    except Exception as e:
        return jsonify({"error": f"Failed to write key file: {e}"}), 500

    # Update .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        env_lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GOOGLE_MAPS_API_KEY="):
                        env_lines.append(f"GOOGLE_MAPS_API_KEY={key}\n")
                        found = True
                    else:
                        env_lines.append(line)
        if not found:
            env_lines.append(f"GOOGLE_MAPS_API_KEY={key}\n")
        with open(env_path, "w") as f:
            f.writelines(env_lines)
    except Exception:
        pass

    os.environ["GOOGLE_MAPS_API_KEY"] = key
    return jsonify({"ok": True, "masked_key": mask_key(key)})


@google_places_bp.route("/api/google-places/search", methods=["POST"])
def search_places():
    """
    Search Google Places API (New) and return formatted results for preview.
    Does NOT save to database directly.
    Checks each result against database for duplicate status.
    """
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    city = (data.get("city") or "").strip()
    business_type = (data.get("business_type") or data.get("businessType") or "").strip()
    page_size = min(int(data.get("pageSize") or data.get("page_size") or 20), 20)
    page_token = data.get("pageToken")

    if not query:
        if business_type and city:
            query = f"{business_type} in {city}"
        elif city:
            query = f"cafes in {city}"
        else:
            return jsonify({"error": "Search query or City/Business Type is required"}), 400

    api_key = get_api_key()
    if not api_key:
        return jsonify({"error": "Google Places API key is not configured. Please add your key in Settings."}), 400

    body = {"textQuery": query, "pageSize": page_size}
    if page_token:
        body["pageToken"] = page_token

    # Add optional location bias / language if available
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers, timeout=20)
        record_api_usage("places:searchText", "search", resp.status_code)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Google Places API request failed: {e}"}), 502

    if resp.status_code != 200:
        err_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        msg = translate_google_error(resp.status_code, err_data)
        return jsonify({"error": msg, "status_code": resp.status_code}), resp.status_code

    result = resp.json()
    raw_places = result.get("places", [])
    next_page_token = result.get("nextPageToken")

    db = SessionLocal()
    formatted_places = []
    try:
        for p in raw_places:
            place_id = p.get("id")
            display_name = (p.get("displayName") or {}).get("text") or "Unknown Business"
            address = p.get("formattedAddress") or ""
            phone = p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber") or ""
            website = p.get("websiteUri") or ""
            rating = p.get("rating")
            review_count = p.get("userRatingCount")
            business_status = p.get("businessStatus") or "OPERATIONAL"
            maps_url = p.get("googleMapsUri") or (f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "")
            location = p.get("location") or {}
            lat = location.get("latitude")
            lng = location.get("longitude")

            # Duplicate check
            norm_item = {
                "google_place_id": place_id,
                "current_website": website,
                "phone": phone,
                "business_name": display_name,
                "city": city or extract_city_from_address(address),
            }
            is_dup, existing_lead, dup_reason = check_duplicate_lead(db, norm_item)

            formatted_places.append({
                "place_id": place_id,
                "google_place_id": place_id,
                "business_name": display_name,
                "address": address,
                "phone": phone,
                "current_website": website,
                "website": website,
                "rating": rating,
                "review_count": review_count,
                "business_status": business_status,
                "google_maps_url": maps_url,
                "latitude": lat,
                "longitude": lng,
                "city": city or extract_city_from_address(address),
                "business_type": business_type or "Cafe",
                "is_duplicate": is_dup,
                "duplicate_reason": dup_reason,
                "existing_lead_id": existing_lead.lead_id if existing_lead else None,
                "import_status": "Imported" if is_dup else "Not Imported",
            })
    finally:
        db.close()

    return jsonify({
        "query": query,
        "count": len(formatted_places),
        "places": formatted_places,
        "nextPageToken": next_page_token,
    })


def extract_city_from_address(address: str) -> str:
    """Best-effort fallback extractor for city name from Indian or global formatted addresses."""
    if not address:
        return "Unknown"
    parts = [p.strip() for p in address.split(",") if p.strip()]
    for city in CITIES:
        for part in parts:
            if city.lower() in part.lower():
                return city
    if len(parts) >= 3:
        return parts[-3]
    if len(parts) >= 2:
        return parts[-2]
    return "Unknown"


@google_places_bp.route("/api/google-places/import", methods=["POST"])
def import_single_place():
    """
    Import or update a single place from Google Places API preview into CRM.
    Supports force update if update_existing is specified.
    """
    data = request.get_json(force=True) or {}
    place = data.get("place") or data
    update_existing = bool(data.get("update_existing") or data.get("updateExisting"))

    if not place:
        return jsonify({"error": "Place data required"}), 400

    db = SessionLocal()
    try:
        is_dup, existing_lead, dup_reason = check_duplicate_lead(db, place)

        if is_dup and existing_lead and not update_existing:
            return jsonify({
                "duplicate": True,
                "reason": dup_reason,
                "existing_lead": existing_lead.to_dict(),
                "message": f"Duplicate detected: {dup_reason}. Choose Update Existing or Skip.",
            }), 409

        if is_dup and existing_lead and update_existing:
            # Update existing lead with fresh Google data
            if place.get("phone"):
                existing_lead.phone = place.get("phone")
            if place.get("current_website") or place.get("website"):
                existing_lead.current_website = place.get("current_website") or place.get("website")
            if place.get("address"):
                existing_lead.address = place.get("address")
            if place.get("google_place_id") or place.get("place_id"):
                existing_lead.google_place_id = place.get("google_place_id") or place.get("place_id")
            if place.get("rating") is not None:
                existing_lead.rating = place.get("rating")
                existing_lead.google_rating = place.get("rating")
            if place.get("review_count") is not None:
                existing_lead.review_count = place.get("review_count")
                existing_lead.google_reviews = place.get("review_count")
            if place.get("business_status"):
                existing_lead.business_status = place.get("business_status")
            if place.get("google_maps_url"):
                existing_lead.google_maps_url = place.get("google_maps_url")
                existing_lead.source_url = place.get("google_maps_url")

            existing_lead.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing_lead)
            return jsonify({
                "ok": True,
                "action": "updated",
                "lead": existing_lead.to_dict(),
                "message": f"Updated lead {existing_lead.lead_id}",
            })

        # Insert new lead
        lead_id = _next_lead_id(db)
        website = place.get("current_website") or place.get("website") or ""
        website_status = "Good" if website else "No Website"

        # Calculate initial lead score
        initial_score = 30 if not website else 15

        new_lead = Lead(
            lead_id=lead_id,
            business_name=place.get("business_name") or "Unknown Business",
            owner_name="Unknown",  # Strictly never generate fake owner
            business_type=place.get("business_type") or "Cafe",
            city=place.get("city") or "Kolkata",
            lead_source="Google Places API",
            phone=place.get("phone") or "",
            email="",  # Google does not provide email
            current_website=website,
            website_status=website_status,
            address=place.get("address") or "",
            rating=place.get("rating"),
            google_rating=place.get("rating"),
            review_count=place.get("review_count"),
            google_reviews=place.get("review_count"),
            google_place_id=place.get("google_place_id") or place.get("place_id") or "",
            google_maps_url=place.get("google_maps_url") or "",
            source_url=place.get("google_maps_url") or "",
            latitude=place.get("latitude"),
            longitude=place.get("longitude"),
            business_status=place.get("business_status") or "OPERATIONAL",
            lead_score=initial_score,
            remarks=f"Imported from Google Places API search ({place.get('business_type', 'Cafe')} in {place.get('city', '')})",
        )
        db.add(new_lead)

        # Log outreach activity
        activity = OutreachActivity(
            lead_id=lead_id,
            activity_type="Lead Created",
            description="Imported from Google Places API (New)",
            result="New Lead",
            created_by="System",
        )
        db.add(activity)

        db.commit()
        db.refresh(new_lead)

        return jsonify({
            "ok": True,
            "action": "created",
            "lead": new_lead.to_dict(),
            "message": f"Successfully imported as {lead_id}",
        }), 201

    finally:
        db.close()


@google_places_bp.route("/api/google-places/import-all", methods=["POST"])
def import_bulk_places():
    """Import an array of places with duplicate checking."""
    data = request.get_json(force=True) or {}
    places = data.get("places") or []
    update_existing = bool(data.get("update_existing") or data.get("updateExisting"))

    if not places:
        return jsonify({"error": "No places provided for import"}), 400

    db = SessionLocal()
    imported_count = 0
    updated_count = 0
    skipped_count = 0
    results = []

    try:
        for p in places:
            is_dup, existing_lead, dup_reason = check_duplicate_lead(db, p)
            if is_dup and existing_lead:
                if update_existing:
                    if p.get("phone"):
                        existing_lead.phone = p.get("phone")
                    if p.get("current_website") or p.get("website"):
                        existing_lead.current_website = p.get("current_website") or p.get("website")
                    if p.get("address"):
                        existing_lead.address = p.get("address")
                    if p.get("google_place_id") or p.get("place_id"):
                        existing_lead.google_place_id = p.get("google_place_id") or p.get("place_id")
                    if p.get("rating") is not None:
                        existing_lead.rating = p.get("rating")
                        existing_lead.google_rating = p.get("rating")
                    if p.get("review_count") is not None:
                        existing_lead.review_count = p.get("review_count")
                        existing_lead.google_reviews = p.get("review_count")
                    existing_lead.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                    results.append({"place_id": p.get("place_id"), "status": "updated", "lead_id": existing_lead.lead_id})
                else:
                    skipped_count += 1
                    results.append({"place_id": p.get("place_id"), "status": "skipped", "reason": dup_reason})
            else:
                lead_id = _next_lead_id(db)
                website = p.get("current_website") or p.get("website") or ""
                new_lead = Lead(
                    lead_id=lead_id,
                    business_name=p.get("business_name") or "Unknown Business",
                    owner_name="Unknown",
                    business_type=p.get("business_type") or "Cafe",
                    city=p.get("city") or "Kolkata",
                    lead_source="Google Places API",
                    phone=p.get("phone") or "",
                    email="",
                    current_website=website,
                    website_status="Good" if website else "No Website",
                    address=p.get("address") or "",
                    rating=p.get("rating"),
                    google_rating=p.get("rating"),
                    review_count=p.get("review_count"),
                    google_reviews=p.get("review_count"),
                    google_place_id=p.get("google_place_id") or p.get("place_id") or "",
                    google_maps_url=p.get("google_maps_url") or "",
                    source_url=p.get("google_maps_url") or "",
                    latitude=p.get("latitude"),
                    longitude=p.get("longitude"),
                    business_status=p.get("business_status") or "OPERATIONAL",
                    lead_score=30 if not website else 15,
                    remarks=f"Bulk imported via Google Places API",
                )
                db.add(new_lead)
                imported_count += 1
                results.append({"place_id": p.get("place_id"), "status": "imported", "lead_id": lead_id})
                db.flush()

        db.commit()
    finally:
        db.close()

    return jsonify({
        "ok": True,
        "total": len(places),
        "imported": imported_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "results": results,
    })


# ══════════════════════════════════════════════════════════════════════════
# BACKGROUND COLLECTION JOBS
# ══════════════════════════════════════════════════════════════════════════

def _run_collection_worker(job_id: str, city: str, business_type: str, max_results: int):
    """Background worker with timeout, retry, rate limit, and cancellation support."""
    db = SessionLocal()
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            return
        job.status = "Running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        api_key = get_api_key()
        if not api_key:
            job.status = "Failed"
            job.errors += 1
            db.add(CollectionLog(job_id=job_id, level="ERROR", message="API Key not configured"))
            db.commit()
            return

        query = f"{business_type} in {city}"
        page_token = None
        collected_places = []
        max_pages = min((max_results + 19) // 20, 3)  # max 3 pages per Google's limit

        for page in range(max_pages):
            if active_jobs.get(job_id, {}).get("stop_requested"):
                db.add(CollectionLog(job_id=job_id, level="WARN", message="Job stopped by user request"))
                job.status = "Stopped"
                db.commit()
                return

            body = {"textQuery": query, "pageSize": 20}
            if page_token:
                body["pageToken"] = page_token

            headers = {
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            }

            try:
                resp = requests.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers, timeout=20)
                record_api_usage("places:searchText", "job", resp.status_code)
            except Exception as e:
                db.add(CollectionLog(job_id=job_id, level="ERROR", message=f"Request failed: {e}"))
                job.errors += 1
                job.status = "Failed"
                db.commit()
                return

            if resp.status_code != 200:
                err_msg = translate_google_error(resp.status_code, resp.text)
                db.add(CollectionLog(job_id=job_id, level="ERROR", message=err_msg))
                job.errors += 1
                job.status = "Failed"
                db.commit()
                return

            res = resp.json()
            places = res.get("places", [])
            collected_places.extend(places)
            page_token = res.get("nextPageToken")
            job.processed_results = len(collected_places)
            db.commit()

            if not page_token or len(collected_places) >= max_results:
                break
            time.sleep(1.5)  # Respectful rate limiting between pages

        # Save collected places
        for p in collected_places:
            if active_jobs.get(job_id, {}).get("stop_requested"):
                job.status = "Stopped"
                db.commit()
                return

            display_name = (p.get("displayName") or {}).get("text") or "Unknown Business"
            phone = p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber") or ""
            website = p.get("websiteUri") or ""
            place_id = p.get("id")

            norm_item = {
                "google_place_id": place_id,
                "current_website": website,
                "phone": phone,
                "business_name": display_name,
                "city": city,
            }
            is_dup, _, _ = check_duplicate_lead(db, norm_item)
            if is_dup:
                job.duplicates += 1
                continue

            lead_id = _next_lead_id(db)
            lead = Lead(
                lead_id=lead_id,
                business_name=display_name,
                owner_name="Unknown",
                business_type=business_type,
                city=city,
                lead_source="Google Places API",
                phone=phone,
                current_website=website,
                website_status="Good" if website else "No Website",
                address=p.get("formattedAddress"),
                rating=p.get("rating"),
                google_rating=p.get("rating"),
                review_count=p.get("userRatingCount"),
                google_reviews=p.get("userRatingCount"),
                google_place_id=place_id,
                google_maps_url=p.get("googleMapsUri") or "",
                source_url=p.get("googleMapsUri") or "",
                lead_score=30 if not website else 15,
                remarks=f"Collected by Job {job_id} ({business_type}, {city})",
            )
            db.add(lead)
            job.imported += 1
            db.flush()

        job.status = "Completed"
        job.completed_at = datetime.now(timezone.utc)
        db.add(CollectionLog(job_id=job_id, level="INFO", message=f"Job completed: {job.imported} imported, {job.duplicates} duplicates skipped."))
        db.commit()

    except Exception as e:
        db.add(CollectionLog(job_id=job_id, level="ERROR", message=f"Worker exception: {e}"))
        if job:
            job.status = "Failed"
            job.errors += 1
        db.commit()
    finally:
        active_jobs.pop(job_id, None)
        db.close()


@google_places_bp.route("/api/collection-jobs", methods=["GET"])
def list_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(CollectionJob).order_by(CollectionJob.created_at.desc()).limit(50).all()
        return jsonify([j.to_dict() for j in jobs])
    finally:
        db.close()


@google_places_bp.route("/api/collection-jobs/start", methods=["POST"])
def start_job():
    data = request.get_json(force=True) or {}
    city = (data.get("city") or "Kolkata").strip()
    business_type = (data.get("business_type") or "Cafe").strip()
    max_results = min(int(data.get("max_results") or 20), 60)

    db = SessionLocal()
    try:
        job_id = f"JOB-{int(time.time())}"
        job = CollectionJob(
            job_id=job_id,
            query=f"{business_type} in {city}",
            city=city,
            business_type=business_type,
            requested_results=max_results,
            status="Pending",
        )
        db.add(job)
        db.add(CollectionLog(job_id=job_id, level="INFO", message=f"Job initialized for {business_type} in {city}"))
        db.commit()

        active_jobs[job_id] = {"stop_requested": False}
        thread = threading.Thread(
            target=_run_collection_worker,
            args=(job_id, city, business_type, max_results),
            daemon=True,
        )
        thread.start()

        return jsonify({"ok": True, "job_id": job_id, "job": job.to_dict()}), 201
    finally:
        db.close()


@google_places_bp.route("/api/collection-jobs/<job_id>/stop", methods=["POST"])
def stop_job(job_id: str):
    if job_id in active_jobs:
        active_jobs[job_id]["stop_requested"] = True

    db = SessionLocal()
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if job and job.status in ("Pending", "Running"):
            job.status = "Stopped"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return jsonify({"ok": True, "message": f"Job {job_id} stopped."})
        return jsonify({"ok": True, "message": "Job is already completed or stopped."})
    finally:
        db.close()


@google_places_bp.route("/api/collection-jobs/<job_id>/logs", methods=["GET"])
def get_job_logs(job_id: str):
    db = SessionLocal()
    try:
        logs = db.query(CollectionLog).filter(CollectionLog.job_id == job_id).order_by(CollectionLog.timestamp.asc()).all()
        return jsonify([l.to_dict() for l in logs])
    finally:
        db.close()
