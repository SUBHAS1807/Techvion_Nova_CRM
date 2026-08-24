"""
TechvionNova CRM — Worldwide Global Lead Collector
===================================================
Discovers businesses anywhere on Earth through Google Places (New),
analyzes their public websites for REAL contact emails using the shared
email-extraction pipeline, and promotes ONLY verified-email businesses
into the CRM leads table.

Hard rule enforced throughout this module:  NO EMAIL = NO LEAD.
"""

import re
import json
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
from flask import Blueprint, request, jsonify
from sqlalchemy import func

from backend.database import SessionLocal
from backend.models import (
    Lead,
    CollectionJob,
    CollectionLog,
    ApiUsageRecord,
    DiscoveredBusiness,
    OutreachActivity,
)
from backend.routes.google_places import (
    get_api_key,
    PLACES_TEXT_SEARCH_URL,
    FIELD_MASK as BASE_FIELD_MASK,
    record_api_usage,
    translate_google_error,
    check_duplicate_lead,
    _next_lead_id,
    normalize_domain,
)
from backend.routes.analyzer import fetch_analysis
from backend.geo_data import (
    COUNTRIES,
    WORLDWIDE_PRESET,
    BUSINESS_CATEGORIES,
    find_country,
    get_regions,
    get_city_suggestions,
    normalize_intl_phone,
    build_search_chunks,
)

global_bp = Blueprint("global_collect", __name__)

# regularOpeningHours is the Text Search (New) field name for public business hours
FIELD_MASK = BASE_FIELD_MASK + ",places.regularOpeningHours"

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

# ── Website status taxonomy (stored in DB, never derived in the frontend) ──
WS_NO_WEBSITE = "NO_WEBSITE"                    # business source provides no URL — the 🎯 target
WS_HAS_WEBSITE = "HAS_WEBSITE"                  # a real website URL exists
WS_INACCESSIBLE = "WEBSITE_INACCESSIBLE"        # URL exists but unreachable/blocked (NOT the same as no website)
WS_UNKNOWN = "WEBSITE_UNKNOWN"                  # not yet determined

WEBSITE_STATUSES = [WS_NO_WEBSITE, WS_HAS_WEBSITE, WS_INACCESSIBLE, WS_UNKNOWN]

# Display labels used by exports / UI fallbacks
WS_LABELS = {
    WS_NO_WEBSITE: "No Website",
    WS_HAS_WEBSITE: "Has Website",
    WS_INACCESSIBLE: "Website Inaccessible",
    WS_UNKNOWN: "Unknown",
}


def classify_website_status(website_url: str | None) -> str:
    """
    Classify from what the BUSINESS SOURCE (Google Places) reports:
      - URL present and non-empty  -> HAS_WEBSITE
      - URL null/empty/whitespace  -> NO_WEBSITE   (the opportunity target)
    Reachability is NEVER part of this initial classification — an unreachable
    site is still a HAS_WEBSITE business until analysis proves otherwise.
    """
    if website_url and str(website_url).strip():
        return WS_HAS_WEBSITE
    return WS_NO_WEBSITE

# Pause / Stop control flags for running workers
global_active_jobs: dict[str, dict] = {}

MAX_WORKERS = 4          # parallel website analyses (polite crawl)
PAGE_DELAY_S = 1.5       # delay between Places pagination calls
CHUNK_DELAY_S = 1.2      # delay between country chunks
RETRY_BACKOFF_S = [3, 6, 12]


def _utcnow():
    return datetime.now(timezone.utc)


def _log(db, job_id: str, level: str, message: str):
    db.add(CollectionLog(job_id=job_id, level=level, message=message))


# ══════════════════════════════════════════════════════════════════════════
# GOOGLE PLACES HELPERS
# ══════════════════════════════════════════════════════════════════════════

def places_text_search(api_key: str, text_query: str, page_size: int,
                       page_token: str | None = None):
    """
    Single Text Search call with retry/backoff on 429 & 5xx.
    Returns (places:list, next_page_token:str|None, error:str|None).
    """
    body = {"textQuery": text_query, "pageSize": min(page_size, 20), "languageCode": "en"}
    if page_token:
        body["pageToken"] = page_token

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
        "Content-Type": "application/json",
    }

    last_err = ""
    for delay in [0] + RETRY_BACKOFF_S:
        if delay:
            time.sleep(delay)
        try:
            resp = requests.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers, timeout=25)
        except requests.exceptions.RequestException as e:
            last_err = f"Network error: {e}"
            continue
        record_api_usage("places:searchText", "global_search", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("places", []), data.get("nextPageToken"), None
        if resp.status_code == 429 or resp.status_code >= 500:
            last_err = translate_google_error(resp.status_code, resp.text[:400])
            continue
        # Non-retryable client error
        return [], None, translate_google_error(resp.status_code, resp.text[:400])
    return [], None, f"Gave up after retries — {last_err}"


def parse_address_components(place: dict) -> dict:
    """Derive country/region/city/postal from Google addressComponents."""
    out = {"country_code": None, "region": None, "city": None, "postal_code": None}
    for comp in place.get("addressComponents") or []:
        types = comp.get("types", [])
        if "country" in types:
            out["country_code"] = (comp.get("shortText") or "").upper() or None
        elif "administrative_area_level_1" in types and not out["region"]:
            out["region"] = comp.get("longText")
        elif ("locality" in types or "postal_town" in types) and not out["city"]:
            out["city"] = comp.get("longText")
        elif "administrative_area_level_2" in types and not out["city"]:
            out["city"] = comp.get("longText")
        elif "postal_code" in types and not out["postal_code"]:
            out["postal_code"] = comp.get("longText")
    return out


# ══════════════════════════════════════════════════════════════════════════
# QUALIFICATION  (the NO EMAIL = NO LEAD gatekeeper)
# ══════════════════════════════════════════════════════════════════════════

def upsert_qualified_lead(db, disc: DiscoveredBusiness, analysis: dict | None) -> tuple[Lead, str]:
    """
    Promote an EMAIL_FOUND discovery into the leads table.
    Updates an existing matching lead instead of duplicating it.
    Returns (lead, action) where action ∈ {"created", "updated"}.
    """
    country = find_country(disc.country_code)
    currency = country["currency"] if country else None

    norm_item = {
        "google_place_id": disc.place_id,
        "current_website": disc.website_url,
        "phone": disc.phone_raw or disc.phone_intl,
        "business_name": disc.business_name,
        "city": disc.city or "",
        "email": disc.email,
    }
    is_dup, existing_lead, reason = check_duplicate_lead(db, norm_item)

    socials_list = []
    if analysis:
        socials_map = analysis.get("socials") or {}
        socials_list = sorted({u for u in socials_map.values() if isinstance(u, str)})

    if is_dup and existing_lead:
        # Enrich the existing lead — never duplicate
        if not (existing_lead.email or "").strip():
            existing_lead.email = disc.email
            existing_lead.email_source = "Business Website"
            existing_lead.email_source_url = disc.email_source_page or ""
            existing_lead.email_status = "Found"
        if not existing_lead.current_website and disc.website_url:
            existing_lead.current_website = disc.website_url
            existing_lead.website_status = "Good"
        if disc.website_status:
            # Keep the machine status in sync with the freshest source data
            existing_lead.website_status_code = disc.website_status
            if disc.website_status == WS_NO_WEBSITE:
                existing_lead.website_status = "No Website"
        if not existing_lead.phone and (disc.phone_intl or disc.phone_raw):
            existing_lead.phone = disc.phone_intl or disc.phone_raw
        if not existing_lead.country:
            existing_lead.country = disc.country_name
            existing_lead.country_code = disc.country_code
            existing_lead.currency = currency
        if not existing_lead.region:
            existing_lead.region = disc.region
            existing_lead.state_province = disc.region
        if not existing_lead.postal_code:
            existing_lead.postal_code = disc.postal_code
        if socials_list and not existing_lead.other_socials:
            existing_lead.other_socials = json.dumps(socials_list)
        if analysis and analysis.get("phones") and not existing_lead.phone:
            existing_lead.phone = analysis["phones"][0]
        existing_lead.updated_at = _utcnow()
        db.add(existing_lead)
        return existing_lead, "updated"

    lead_id = _next_lead_id(db)
    no_website_lead = disc.website_status == WS_NO_WEBSITE
    new_lead = Lead(
        lead_id=lead_id,
        business_name=disc.business_name or "Unknown Business",
        owner_name="Unknown",
        business_type=disc.business_type or "Business",
        city=disc.city or disc.region or disc.country_name or "Unknown",
        country=disc.country_name,
        country_code=disc.country_code,
        region=disc.region,
        state_province=disc.region,
        postal_code=disc.postal_code,
        currency=currency,
        other_socials=json.dumps(socials_list) if socials_list else None,
        opening_hours=disc.opening_hours_json,
        lead_source="Global Collection (Google Places)",
        phone=disc.phone_intl or disc.phone_raw or "",
        email=disc.email,
        email_source="Business Website" if not no_website_lead else "Public Source",
        email_source_url=disc.email_source_page or "",
        email_status="Found",
        current_website="" if no_website_lead else (disc.website_url or ""),
        website_status="No Website" if no_website_lead else "Good",
        website_status_code=disc.website_status or WS_UNKNOWN,
        address=disc.address or "",
        rating=disc.rating,
        google_rating=disc.rating,
        review_count=disc.review_count,
        google_reviews=disc.review_count,
        latitude=disc.latitude,
        longitude=disc.longitude,
        google_place_id=disc.place_id,
        google_maps_url=disc.maps_url or "",
        source_url=disc.maps_url or "",
        business_status=disc.business_status or "OPERATIONAL",
        lead_score=65 if not no_website_lead else 75,   # no-site + email = prime opportunity
        remarks=("🎯 WEBSITE OPPORTUNITY — no website but public email available. "
                 f"Job {disc.job_id}" if no_website_lead
                 else f"Qualified worldwide discovery (public email verified) — Job {disc.job_id}"),
    )
    db.add(new_lead)
    db.flush()
    db.add(OutreachActivity(
        lead_id=lead_id,
        activity_type="Lead Created",
        description=f"Worldwide collection: qualified via public email ({disc.email})",
        result="New Qualified Lead",
        created_by="Global Collector",
    ))
    return new_lead, "created"


def _apply_analysis_result(db, disc: DiscoveredBusiness, result: dict, job: CollectionJob):
    """Map one fetch_analysis result onto a DiscoveredBusiness row + counters."""
    disc.processed_at = _utcnow()

    if result.get("blocked"):
        # URL exists but the site refused automated access — NOT "no website"
        disc.email_status = "WEBSITE_UNAVAILABLE"
        disc.website_status = WS_INACCESSIBLE
        disc.analysis_error = (result.get("error") or "")[:300]
        return

    if result.get("error") and not result.get("status_code"):
        # DNS failure / timeout / connection refused — site unreachable
        disc.email_status = "WEBSITE_UNAVAILABLE"
        disc.website_status = WS_INACCESSIBLE
        disc.analysis_error = (result.get("error") or "")[:300]
        return

    if result.get("error"):
        disc.email_status = "ERROR"
        disc.analysis_error = (result.get("error") or "")[:300]
        job.errors += 1
        return

    # Site reachable — classification confirmed
    disc.website_status = WS_HAS_WEBSITE

    primary = (result.get("primary_email") or "").strip()
    if primary and EMAIL_RE.match(primary):
        disc.email_status = "EMAIL_FOUND"
        disc.email = primary.lower()
        disc.email_source_page = (result.get("email_source_url") or "")[:500]
        disc.emails_json = json.dumps(result.get("emails") or [])
        job.emails_found += 1
        return

    candidates = result.get("emails") or []
    if candidates:
        first = str(candidates[0]).strip().lower()
        if EMAIL_RE.match(first):
            disc.email_status = "EMAIL_FOUND"
            disc.email = first
            disc.email_source_page = (result.get("email_source_url") or "")[:500]
            disc.emails_json = json.dumps(candidates)
            job.emails_found += 1
        else:
            disc.email_status = "INVALID_EMAIL"
            disc.analysis_error = "Email-like strings found but none syntactically valid"
    else:
        disc.email_status = "EMAIL_NOT_FOUND"
        disc.analysis_error = None


def _analyze_site_task(disc_id: int, website_url: str) -> dict:
    """
    Runs INSIDE worker threads. Read-only DB access; the actual HTTP crawl;
    returns results so the main thread performs every write (SQLite-safe).
    """
    time.sleep(random.uniform(0.2, 0.7))   # polite jitter under concurrency
    try:
        result = fetch_analysis(website_url)
    except Exception as e:                      # noqa: BLE001 - worker must survive
        return {"disc_id": disc_id, "url": website_url, "error": f"Analysis exception: {e}", "status_code": 0}
    clean = {k: v for k, v in result.items() if not k.startswith("_")}
    clean["disc_id"] = disc_id
    return clean


# ══════════════════════════════════════════════════════════════════════════
# GLOBAL WORKER  (chunked, pausable, stoppable, resumable)
# ══════════════════════════════════════════════════════════════════════════

def _save_remaining_chunks(job: CollectionJob, remaining: list[dict]):
    job.pending_chunks = json.dumps(remaining)


def _run_global_worker(job_id: str):
    control = global_active_jobs.setdefault(job_id, {"stop": False, "pause": False})
    db = SessionLocal()
    job = None
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            return

        api_key = get_api_key()
        if not api_key:
            job.status = "Failed"
            job.errors += 1
            _log(db, job_id, "ERROR", "Google Places API key not configured.")
            db.commit()
            return

        job.status = "Running"
        job.started_at = job.started_at or _utcnow()
        db.commit()

        chunks = json.loads(job.pending_chunks) if job.pending_chunks else []
        if not chunks and job.is_global:
            chunks = build_search_chunks(
                job.countries_json and json.loads(job.countries_json) or [],
                job.region, job.city, job.business_type or "Cafe", job.keyword,
            )
            _save_remaining_chunks(job, chunks)
            db.commit()

        total_chunks = len(chunks)
        # Website-status targeting for this job
        ws_target = (job.website_status_filter or "ALL").upper()

        while chunks:
            if control.get("stop"):
                job.status = "Stopped"
                job.completed_at = _utcnow()
                _save_remaining_chunks(job, chunks)
                _log(db, job_id, "WARN", f"Job stopped by user. {len(chunks)} chunk(s) remain unprocessed.")
                db.commit()
                return
            if control.get("pause"):
                job.status = "Paused"
                _save_remaining_chunks(job, chunks)
                _log(db, job_id, "INFO", f"Job paused. {len(chunks)} chunk(s) queued for resume.")
                db.commit()
                return

            chunk = chunks[0]
            job.current_chunk = chunk.get("query", "")
            db.commit()

            iso2 = chunk["country_iso2"]
            country = COUNTRIES.get(iso2, {})
            log_prefix = f"[{country.get('name', iso2)}]"

            # ── Discovery phase: paginate Places results ─────────────────
            per_chunk_limit = min(int(chunk.get("limit") or 20), 100)
            page_token = None
            seen_this_chunk = set()
            chunk_new = 0

            for _page in range(3):  # Google caps text search at ~3 usable pages
                if control.get("stop") or control.get("pause"):
                    break
                if chunk_new >= per_chunk_limit:
                    break
                places, page_token, err = places_text_search(
                    api_key, chunk["query"], 20, page_token
                )
                if err:
                    job.errors += 1
                    _log(db, job_id, "ERROR", f"{log_prefix} Places search failed: {err}")
                    break

                for p in places:
                    if control.get("stop") or control.get("pause"):
                        break
                    if chunk_new >= per_chunk_limit:
                        break
                    pid = p.get("id")
                    if not pid or pid in seen_this_chunk:
                        continue
                    seen_this_chunk.add(pid)

                    geo = parse_address_components(p)
                    cc = geo["country_code"] or iso2
                    display_name = ((p.get("displayName") or {}).get("text") or "").strip() or "Unknown Business"
                    website = (p.get("websiteUri") or "").strip()
                    hours = (p.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []
                    loc = p.get("location") or {}
                    raw_phone = p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber") or ""

                    existing = db.query(DiscoveredBusiness).filter(
                        DiscoveredBusiness.place_id == pid
                    ).first()

                    if existing:
                        # Duplicate place — refresh classification instead of duplicating.
                        # If a previously NO_WEBSITE business now has a site, upgrade it.
                        if website and existing.website_status in (WS_NO_WEBSITE, WS_UNKNOWN):
                            existing.website_url = website
                            existing.has_website = True
                            existing.website_status = WS_HAS_WEBSITE
                            if existing.lead_id:
                                lead_row = db.query(Lead).filter(
                                    Lead.lead_id == existing.lead_id).first()
                                if lead_row and not (lead_row.current_website or "").strip():
                                    lead_row.current_website = website
                                    lead_row.website_status = "Good"
                                    lead_row.website_status_code = WS_HAS_WEBSITE
                            _log(db, job_id, "INFO",
                                 f"{log_prefix} ↻ {existing.business_name} gained a website — "
                                 f"upgraded {existing.website_status}")
                        # Requeue only transient analysis failures
                        if existing.email_status in ("NOT_ANALYZED", "ERROR", "ANALYZING") and website:
                            existing.job_id = job_id
                        continue

                    disc = DiscoveredBusiness(
                        place_id=pid,
                        business_name=display_name,
                        business_type=(chunk.get("category") or "Business"),
                        address=p.get("formattedAddress") or "",
                        country_code=cc,
                        country_name=(COUNTRIES.get(cc) or {}).get("name") or "",
                        region=geo["region"],
                        city=geo["city"] or chunk.get("city") or "",
                        postal_code=geo["postal_code"],
                        phone_raw=raw_phone,
                        phone_intl=normalize_intl_phone(raw_phone, cc),
                        website_url=website or None,
                        has_website=bool(website),
                        website_status=classify_website_status(website),
                        maps_url=p.get("googleMapsUri") or "",
                        rating=p.get("rating"),
                        review_count=p.get("userRatingCount"),
                        latitude=loc.get("latitude"),
                        longitude=loc.get("longitude"),
                        business_status=p.get("businessStatus") or "OPERATIONAL",
                        opening_hours_json=json.dumps(hours) if hours else None,
                        job_id=job_id,
                        email_status="NOT_ANALYZED",
                    )
                    db.add(disc)
                    job.discovered += 1
                    chunk_new += 1
                    if website:
                        job.websites_found += 1
                    db.flush()

                if err or not page_token:
                    break
                time.sleep(PAGE_DELAY_S)

            db.commit()

            # ── Analysis phase: parallel website email discovery ─────────
            # Website-status targeting decides what gets crawled & promoted.
            if ws_target == WS_NO_WEBSITE:
                # No websites exist for these businesses — there is nothing to
                # crawl. Close them out honestly instead of leaving them queued.
                no_site_rows = db.query(DiscoveredBusiness).filter(
                    DiscoveredBusiness.job_id == job_id,
                    DiscoveredBusiness.has_website.is_(False),
                    DiscoveredBusiness.email_status == "NOT_ANALYZED",
                ).all()
                for row in no_site_rows:
                    row.email_status = ("EMAIL_FOUND" if (row.email or "").strip()
                                        else "EMAIL_NOT_FOUND")
                    row.analysis_error = None if (row.email or "").strip() else \
                        "No website provided by business source — nothing to analyze"
                    row.processed_at = _utcnow()
                db.commit()
                _log(db, job_id, "INFO",
                     f"{log_prefix} 🎯 No-website targeting: {len(no_site_rows)} business(es) "
                     f"classified NO_WEBSITE (sites never assumed missing due to errors).")
            else:
                pending_rows = db.query(DiscoveredBusiness).filter(
                    DiscoveredBusiness.job_id == job_id,
                    DiscoveredBusiness.has_website.is_(True),
                    DiscoveredBusiness.website_status.in_([WS_HAS_WEBSITE, WS_UNKNOWN]),
                    DiscoveredBusiness.email_status.in_(["NOT_ANALYZED", "ERROR"]),
                ).limit(per_chunk_limit * 2).all()

                if pending_rows and not control.get("stop") and not control.get("pause"):
                    _log(db, job_id, "INFO",
                         f"{log_prefix} Analyzing {len(pending_rows)} website(s) for public emails...")
                    db.commit()
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                        futures = {
                            pool.submit(_analyze_site_task, d.id, d.website_url): d.id
                            for d in pending_rows if d.website_url
                        }
                        for fut in as_completed(futures):
                            if control.get("stop"):
                                for f in futures:
                                    f.cancel()
                                break
                            try:
                                res = fut.result()
                            except Exception as e:                   # noqa: BLE001
                                _log(db, job_id, "ERROR", f"Analysis thread crash: {e}")
                                continue
                            row = db.query(DiscoveredBusiness).filter(
                                DiscoveredBusiness.id == res["disc_id"]).first()
                            if row is None:
                                continue
                            row.email_status = "ANALYZING"
                            _apply_analysis_result(db, row, res, job)
                            if row.email_status == "EMAIL_FOUND":
                                _log(db, job_id, "SUCCESS",
                                     f"{log_prefix} ✓ {row.business_name}: {row.email}")
                            db.commit()

                # ── Qualification phase: NO EMAIL = NO LEAD (+ status gate) ──
                qual_query = db.query(DiscoveredBusiness).filter(
                    DiscoveredBusiness.job_id == job_id,
                    DiscoveredBusiness.email_status == "EMAIL_FOUND",
                    DiscoveredBusiness.lead_id.is_(None),
                )
                if ws_target == WS_NO_WEBSITE:
                    qual_query = qual_query.filter(
                        DiscoveredBusiness.website_status == WS_NO_WEBSITE)
                elif ws_target == WS_HAS_WEBSITE:
                    qual_query = qual_query.filter(
                        DiscoveredBusiness.website_status == WS_HAS_WEBSITE)
                newly_found = qual_query.all()

                for row in newly_found:
                    try:
                        lead, action = upsert_qualified_lead(db, row, None)
                        row.lead_id = lead.lead_id
                        job.qualified_leads += 1
                        tag = "🎯 OPPORTUNITY" if row.website_status == WS_NO_WEBSITE else "★"
                        _log(db, job_id, "INFO",
                             f"{log_prefix} {tag} Qualified as {lead.lead_id} ({action}) — {row.business_name}")
                    except Exception as e:                           # noqa: BLE001
                        db.rollback()
                        _log(db, job_id, "ERROR", f"Qualification failed for {row.place_id}: {e}")
                    db.commit()

            # Count skips for this chunk's unresolved rows
            unresolved = db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.job_id == job_id,
                DiscoveredBusiness.processed_at.isnot(None),
                DiscoveredBusiness.email_status.notin_(["EMAIL_FOUND"]),
                DiscoveredBusiness.lead_id.is_(None),
            ).count()
            job.skipped_no_email = max(job.skipped_no_email, unresolved)

            # Chunk complete → dequeue
            chunks.pop(0)
            _save_remaining_chunks(job, chunks)
            job.current_chunk = ""
            db.commit()
            if chunks:
                time.sleep(CHUNK_DELAY_S)

        if job.status == "Running":
            job.status = "Completed"
            job.completed_at = _utcnow()
            job.pending_chunks = None
            _log(db, job_id, "INFO",
                 f"Job completed ✓ — discovered {job.discovered}, websites {job.websites_found}, "
                 f"emails {job.emails_found}, QUALIFIED {job.qualified_leads}, "
                 f"skipped(no email) {job.skipped_no_email}.")
        db.commit()

    except Exception as e:                                       # noqa: BLE001
        try:
            _log(db, job_id, "ERROR", f"Worker exception: {e}")
            if job:
                job.status = "Failed"
                job.errors += 1
            db.commit()
        except Exception:
            pass
    finally:
        global_active_jobs.pop(job_id, None)
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════

@global_bp.route("/api/global/meta", methods=["GET"])
def global_meta():
    """Countries, regions, cities, categories for the worldwide collector UI."""
    country_param = request.args.get("country")
    countries = sorted(COUNTRIES.values(), key=lambda c: c["name"])

    payload = {
        "countries": countries,
        "worldwide_preset": WORLDWIDE_PRESET,
        "preset_names": [COUNTRIES[c]["name"] for c in WORLDWIDE_PRESET],
        "categories": BUSINESS_CATEGORIES,
        "regions": [],
        "cities": [],
        "website_statuses": [
            {"value": "ALL", "label": "All"},
            {"value": WS_NO_WEBSITE, "label": "🚫 No Website"},
            {"value": WS_HAS_WEBSITE, "label": "🌐 Has Website"},
            {"value": WS_INACCESSIBLE, "label": "⚠ Website Inaccessible"},
            {"value": WS_UNKNOWN, "label": "❓ Unknown"},
        ],
    }
    if country_param:
        c = find_country(country_param)
        if c:
            payload["selected"] = c
            payload["regions"] = get_regions(c["iso2"])
            payload["cities"] = get_city_suggestions(c["iso2"])
    return jsonify(payload)


@global_bp.route("/api/global/jobs/start", methods=["POST"])
def start_global_job():
    data = request.get_json(force=True) or {}

    worldwide = bool(data.get("worldwide"))
    country_input = (data.get("country") or "").strip()
    region = (data.get("region") or "").strip()
    city = (data.get("city") or "").strip()
    category = (data.get("category") or "Cafe").strip()
    keyword = (data.get("keyword") or "").strip()
    radius_km = data.get("radius_km") or data.get("radiusKm")
    per_chunk = min(int(data.get("max_results") or 20), 100)

    # Website-status targeting: ALL | NO_WEBSITE | HAS_WEBSITE | WEBSITE_INACCESSIBLE
    ws_filter = str(data.get("website_status") or "ALL").strip().upper()
    if ws_filter not in ("ALL",) + tuple(WEBSITE_STATUSES):
        return jsonify({"error": f"Invalid website_status '{ws_filter}'"}), 400

    # Resolve target countries
    if worldwide:
        iso_list = list(WORLDWIDE_PRESET)
    elif data.get("countries"):
        # Explicit multi-country list (ISO2 / ISO3 / names)
        iso_list = []
        for entry in data["countries"]:
            c = find_country(str(entry))
            if c and c["iso2"] not in iso_list:
                iso_list.append(c["iso2"])
            elif not c:
                return jsonify({"error": f"Unknown country '{entry}'"}), 400
    elif country_input:
        c = find_country(country_input)
        if not c:
            return jsonify({"error": f"Unknown country '{country_input}'"}), 400
        iso_list = [c["iso2"]]
    else:
        return jsonify({"error": "Provide a country or enable worldwide mode."}), 400

    if len(iso_list) > 30:
        iso_list = iso_list[:30]

    chunks = build_search_chunks(iso_list, region, city, category, keyword, max_chunks=30)
    for ch in chunks:
        ch["limit"] = per_chunk
        if radius_km:
            try:
                ch["radius_km"] = int(radius_km)
            except (TypeError, ValueError):
                pass

    if not chunks:
        return jsonify({"error": "Could not build any search targets."}), 400

    db = SessionLocal()
    try:
        job_id = f"GJOB-{int(time.time())}"
        label_countries = ", ".join(COUNTRIES[i]["name"] for i in iso_list[:6])
        if len(iso_list) > 6:
            label_countries += f" +{len(iso_list) - 6} more"
        scope = "🌎 Worldwide" if worldwide else label_countries
        query_label = f"{keyword or category} @ {scope}" + (f" / {city}" if city else "")
        if ws_filter != "ALL":
            query_label += f" [{WS_LABELS.get(ws_filter, ws_filter)}]"

        job = CollectionJob(
            job_id=job_id,
            query=query_label[:255],
            city=city or None,
            business_type=category,
            requested_results=per_chunk * len(chunks),
            status="Pending",
            is_global=True,
            country=("Worldwide" if worldwide else (find_country(iso_list[0]) or {}).get("name")),
            countries_json=json.dumps(iso_list),
            region=region or None,
            keyword=keyword or None,
            radius_km=int(radius_km) if radius_km else None,
            website_status_filter=(None if ws_filter == "ALL" else ws_filter),
        )
        _save_remaining_chunks(job, chunks)
        db.add(job)
        _log(db, job_id, "INFO",
             f"Global job created — {len(chunks)} target(s): {query_label}. "
             + ("Campaign: 🎯 Website Opportunity Leads. " if ws_filter == WS_NO_WEBSITE else "")
             + "Rule active: NO EMAIL = NO LEAD.")
        db.commit()

        global_active_jobs[job_id] = {"stop": False, "pause": False}
        threading.Thread(target=_run_global_worker, args=(job_id,), daemon=True).start()

        return jsonify({"ok": True, "job_id": job_id, "chunks": len(chunks), "job": job.to_dict()}), 201
    finally:
        db.close()


@global_bp.route("/api/global/jobs", methods=["GET"])
def list_global_jobs():
    limit = min(int(request.args.get("limit") or 25), 100)
    db = SessionLocal()
    try:
        jobs = db.query(CollectionJob).filter(
            CollectionJob.is_global.is_(True)
        ).order_by(CollectionJob.created_at.desc()).limit(limit).all()
        return jsonify([j.to_dict() for j in jobs])
    finally:
        db.close()


@global_bp.route("/api/global/jobs/<job_id>", methods=["GET"])
def get_global_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            return jsonify({"error": "Job not found"}), 404
        logs = db.query(CollectionLog).filter(
            CollectionLog.job_id == job_id
        ).order_by(CollectionLog.timestamp.desc()).limit(150).all()
        payload = job.to_dict()
        payload["logs"] = [l.to_dict() for l in logs]
        payload["live"] = job_id in global_active_jobs
        return jsonify(payload)
    finally:
        db.close()


@global_bp.route("/api/global/jobs/<job_id>/pause", methods=["POST"])
def pause_global_job(job_id: str):
    if job_id in global_active_jobs:
        global_active_jobs[job_id]["pause"] = True
    db = SessionLocal()
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            return jsonify({"error": "Job not found"}), 404
        if job.status == "Running":
            job.status = "Paused"   # worker will persist remaining chunks before exiting
            db.commit()
        return jsonify({"ok": True, "status": job.status})
    finally:
        db.close()


@global_bp.route("/api/global/jobs/<job_id>/resume", methods=["POST"])
def resume_global_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            return jsonify({"error": "Job not found"}), 404
        if job.status != "Paused":
            return jsonify({"error": f"Only paused jobs can resume (current: {job.status})"}), 400
        if not job.pending_chunks:
            return jsonify({"error": "No pending work left for this job."}), 400

        job.status = "Running"
        db.commit()
        global_active_jobs[job_id] = {"stop": False, "pause": False}
        threading.Thread(target=_run_global_worker, args=(job_id,), daemon=True).start()
        return jsonify({"ok": True, "status": "Running"})
    finally:
        db.close()


@global_bp.route("/api/global/jobs/<job_id>/stop", methods=["POST"])
def stop_global_job(job_id: str):
    if job_id in global_active_jobs:
        global_active_jobs[job_id]["stop"] = True
    db = SessionLocal()
    try:
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            return jsonify({"error": "Job not found"}), 404
        if job.status in ("Pending", "Running", "Paused"):
            job.status = "Stopped"
            job.completed_at = _utcnow()
            db.commit()
        return jsonify({"ok": True, "status": job.status,
                        "message": "Collected data is preserved."})
    finally:
        db.close()


@global_bp.route("/api/global/discoveries", methods=["GET"])
def list_discoveries():
    job_id = request.args.get("job_id")
    status = request.args.get("email_status") or request.args.get("status")
    ws_filter = (request.args.get("website_status") or "").strip().upper()
    q = (request.args.get("q") or "").strip()
    country = (request.args.get("country") or "").strip()
    limit = min(int(request.args.get("limit") or 50), 200)
    skip = max(int(request.args.get("skip") or 0), 0)

    db = SessionLocal()
    try:
        query = db.query(DiscoveredBusiness)
        if job_id:
            query = query.filter(DiscoveredBusiness.job_id == job_id)
        if status:
            query = query.filter(DiscoveredBusiness.email_status == status.upper())
        if ws_filter and ws_filter != "ALL":
            query = query.filter(DiscoveredBusiness.website_status == ws_filter)
        if country:
            query = query.filter(DiscoveredBusiness.country_code == country.upper())
        if q:
            like = f"%{q}%"
            query = query.filter(DiscoveredBusiness.business_name.ilike(like) |
                                 DiscoveredBusiness.email.ilike(like))
        total = query.count()
        rows = query.order_by(DiscoveredBusiness.created_at.desc()).offset(skip).limit(limit).all()
        return jsonify({
            "total": total,
            "count": len(rows),
            "discoveries": [d.to_dict() for d in rows],
        })
    finally:
        db.close()


@global_bp.route("/api/global/stats", methods=["GET"])
def global_stats():
    db = SessionLocal()
    try:
        base = db.query(DiscoveredBusiness)
        funnel = {
            "discovered": base.count(),
            "websites": db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.has_website.is_(True)).count(),
            "emails_found": db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.email_status == "EMAIL_FOUND").count(),
            "qualified": db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.lead_id.isnot(None)).count(),
            "no_email": db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.email_status == "EMAIL_NOT_FOUND").count(),
            "website_unavailable": db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.email_status == "WEBSITE_UNAVAILABLE").count(),
            "invalid_email": db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.email_status == "INVALID_EMAIL").count(),
            "errors": db.query(DiscoveredBusiness).filter(
                DiscoveredBusiness.email_status == "ERROR").count(),
        }

        by_country = (
            db.query(DiscoveredBusiness.country_name,
                     func.count(DiscoveredBusiness.id))
            .filter(DiscoveredBusiness.lead_id.isnot(None))
            .group_by(DiscoveredBusiness.country_name)
            .order_by(func.count(DiscoveredBusiness.id).desc())
            .limit(15)
            .all()
        )
        emails_by_country = (
            db.query(DiscoveredBusiness.country_name,
                     func.count(DiscoveredBusiness.id))
            .filter(DiscoveredBusiness.email_status == "EMAIL_FOUND")
            .group_by(DiscoveredBusiness.country_name)
            .order_by(func.count(DiscoveredBusiness.id).desc())
            .limit(15)
            .all()
        )

        # Website-opportunity metrics (real data only)
        no_website_total = db.query(DiscoveredBusiness).filter(
            DiscoveredBusiness.website_status == WS_NO_WEBSITE).count()
        emails_no_website = db.query(DiscoveredBusiness).filter(
            DiscoveredBusiness.website_status == WS_NO_WEBSITE,
            DiscoveredBusiness.email_status == "EMAIL_FOUND").count()
        opportunity_leads = db.query(DiscoveredBusiness).filter(
            DiscoveredBusiness.website_status == WS_NO_WEBSITE,
            DiscoveredBusiness.lead_id.isnot(None)).count()

        crm_global_leads = db.query(Lead).filter(Lead.country.isnot(None)).count()
        api_calls = db.query(ApiUsageRecord).count()

        return jsonify({
            "funnel": funnel,
            "website_opportunity": {
                "businesses_without_website": no_website_total,
                "emails_found_without_website": emails_no_website,
                "opportunity_leads": opportunity_leads,
                "by_website_status": {
                    ws: db.query(DiscoveredBusiness)
                        .filter(DiscoveredBusiness.website_status == ws).count()
                    for ws in WEBSITE_STATUSES
                },
            },
            "crm_global_leads": crm_global_leads,
            "by_country": [{"name": n or "Unknown", "count": c} for n, c in by_country],
            "emails_by_country": [{"name": n or "Unknown", "count": c} for n, c in emails_by_country],
            "total_api_calls": api_calls,
        })
    finally:
        db.close()
