import re
import time
import json
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from flask import Blueprint, request, jsonify

from backend.database import SessionLocal
from backend.models import Lead, WebsiteAnalysisRecord, OutreachActivity

analyzer_bp = Blueprint("analyzer", __name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}")

ORDERING_HINTS = ["order online", "swiggy", "zomato", "menu", "order now", "delivery", "food", "cart", "checkout"]
BOOKING_HINTS = ["booking", "book table", "reservation", "book now", "appointment", "reserve", "schedule"]

SOCIAL_PATTERNS = {
    "instagram": re.compile(r"https?://(?:www\.)?instagram\.com/[\w.\-/]+", re.I),
    "facebook": re.compile(r"https?://(?:www\.)?facebook\.com/[\w.\-/]+", re.I),
    "linkedin": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w\-/%]+", re.I),
    "twitter": re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/\w+", re.I),
}


def normalize_url(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc or "." not in parsed.netloc:
        return None
    return raw


def _find_emails(soup, html: str) -> list[str]:
    found = set()
    for m in EMAIL_RE.findall(html):
        # Ignore common asset false positives
        if not any(m.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js"]):
            found.add(m)
    for a in soup.find_all("a", href=True):
        if a["href"].lower().startswith("mailto:"):
            email_part = a["href"][7:].split("?")[0].strip()
            if email_part:
                found.add(email_part)
    return sorted(found)[:5]


def _find_phones(soup) -> list[str]:
    found = set()
    for a in soup.find_all("a", href=True):
        if a["href"].lower().startswith("tel:"):
            found.add(a["href"][4:].strip())
    for el in soup.stripped_strings:
        for m in PHONE_RE.findall(el):
            digits = re.sub(r"\D", "", m)
            if 10 <= len(digits) <= 13:
                found.add(m.strip())
    return sorted(found)[:5]


def _find_socials(html: str) -> dict[str, str]:
    out = {}
    for name, pattern in SOCIAL_PATTERNS.items():
        m = pattern.search(html)
        if m:
            out[name] = m.group(0).rstrip("/")
    return out


def classify_website(soup: BeautifulSoup, html: str, status_code: int) -> tuple[str, dict]:
    if status_code >= 400 or status_code == 0:
        return "Broken", {"broken": True}

    text = soup.get_text(" ", strip=True).lower()
    html_lower = html.lower()

    has_booking = any(h in html_lower or h in text for h in BOOKING_HINTS)
    has_ordering = any(h in html_lower or h in text for h in ORDERING_HINTS)
    has_viewport = soup.find("meta", attrs={"name": "viewport"}) is not None

    year_match = re.search(r"(?:©|&copy;|copyright)\s*(?:\d{4})?", text)
    current_year = time.localtime().tm_year
    stale_copyright = False
    if year_match:
        years = [int(y) for y in re.findall(r"\d{4}", year_match.group(0))]
        if years and max(years) < current_year - 2:
            stale_copyright = True

    uses_tables_layout = bool(soup.find("table")) and "<td" in html_lower
    jquery_old = "jquery-1." in html_lower or "jquery-2." in html_lower

    features = {
        "has_booking": has_booking,
        "has_ordering": has_ordering,
        "has_viewport": has_viewport,
        "stale_copyright": stale_copyright,
        "jquery_old": jquery_old,
    }

    if "woocommerce" in html_lower or "shopify" in html_lower or "add to cart" in html_lower:
        return "E-commerce Website", features

    if has_booking and ("book table" in text or "reservation" in text):
        return "Booking Website", features

    outdated_signals = sum([
        not has_viewport,
        stale_copyright,
        uses_tables_layout,
        jquery_old,
    ])

    if outdated_signals >= 2 or not has_viewport:
        return "Outdated", features

    return "Good", features


def compute_lead_score(website_status: str, analysis: dict) -> tuple[int, list[str]]:
    """
    Transparent rules-based Lead Score (0–100):
    - No Website = +30
    - Broken Website = +25
    - Outdated Website = +20
    - No Online Booking = +10
    - No Online Ordering = +10
    - Public Business Email Found = +5
    Max: 100
    """
    score = 0
    breakdown = []

    if website_status == "No Website":
        score += 30
        breakdown.append("+30 No Website")
    elif website_status == "Broken":
        score += 25
        breakdown.append("+25 Broken Website")
    elif website_status == "Outdated":
        score += 20
        breakdown.append("+20 Outdated Website")
    elif website_status == "Good":
        score += 10
        breakdown.append("+10 Existing Active Website")

    features = analysis.get("features", {})
    if not features.get("has_booking"):
        score += 10
        breakdown.append("+10 No Online Booking")
    if not features.get("has_ordering"):
        score += 10
        breakdown.append("+10 No Online Ordering")

    if analysis.get("emails") and len(analysis["emails"]) > 0:
        score += 5
        breakdown.append("+5 Public Business Email Verified")

    final_score = min(score, 100)
    return final_score, breakdown


@analyzer_bp.route("/api/website/analyze", methods=["POST"])
@analyzer_bp.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True) or {}
    raw_url = data.get("url")
    url = normalize_url(raw_url)
    if not url:
        return jsonify({"error": "A valid website URL is required"}), 400

    lead_id = data.get("lead_id")
    result = fetch_analysis(url)

    if result.get("error"):
        if lead_id:
            save_to_lead(lead_id, url, result)
        return jsonify(result), 200

    website_status, features = classify_website(result["_soup"], result["_html"], result["status_code"])
    result["website_status"] = website_status
    result["features"] = features

    score, breakdown = compute_lead_score(website_status, result)
    result["lead_score"] = score
    result["score_breakdown"] = breakdown

    # Clean internal references before serialization
    result.pop("_soup", None)
    result.pop("_html", None)

    if lead_id:
        result["saved_to_lead"] = save_to_lead(lead_id, url, result)

    return jsonify(result)


@analyzer_bp.route("/api/analyze/lead/<lead_id>", methods=["POST"])
def analyze_lead(lead_id: str):
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        if not lead.current_website:
            return jsonify({"error": "Lead has no website URL to analyze"}), 400
        url = normalize_url(lead.current_website)
        if not url:
            return jsonify({"error": f"Lead website '{lead.current_website}' is not a valid URL"}), 400
    finally:
        db.close()

    result = fetch_analysis(url)
    if not result.get("error"):
        website_status, features = classify_website(result["_soup"], result["_html"], result["status_code"])
        result["website_status"] = website_status
        result["features"] = features
        score, breakdown = compute_lead_score(website_status, result)
        result["lead_score"] = score
        result["score_breakdown"] = breakdown

    result.pop("_soup", None)
    result.pop("_html", None)

    result["saved_to_lead"] = save_to_lead(lead_id, url, result)
    result["lead_id"] = lead_id
    return jsonify(result)


def fetch_analysis(url: str) -> dict:
    start = time.time()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
    except requests.exceptions.SSLError:
        try:
            resp = requests.get(url.replace("https://", "http://"), headers=HEADERS, timeout=12)
        except Exception as e2:
            return {"url": url, "error": f"SSL error and fallback failed: {e2}", "status_code": 0}
    except requests.exceptions.ConnectionError:
        return {"url": url, "error": "Connection failed — site may be down or unreachable", "status_code": 0}
    except requests.exceptions.Timeout:
        return {"url": url, "error": "Request timed out after 12s", "status_code": 0}
    except Exception as e:
        return {"url": url, "error": f"Request failed: {e}", "status_code": 0}

    elapsed = round(time.time() - start, 2)
    html = resp.text[:2_000_000]
    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    description = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else None

    imgs = soup.find_all("img")
    missing_alt = sum(1 for i in imgs if not i.get("alt"))

    # Also inspect public contact links if present on homepage
    extra_emails = set()
    extra_phones = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(w in href for w in ["contact", "about", "reach-us"]):
            target_sub = urljoin(resp.url, a["href"])
            if urlparse(target_sub).netloc == urlparse(resp.url).netloc:
                try:
                    sub_resp = requests.get(target_sub, headers=HEADERS, timeout=5)
                    if sub_resp.status_code == 200:
                        sub_soup = BeautifulSoup(sub_resp.text[:1_000_000], "html.parser")
                        extra_emails.update(_find_emails(sub_soup, sub_resp.text))
                        extra_phones.update(_find_phones(sub_soup))
                except Exception:
                    pass
            break  # Limit to 1 subpage check to remain fast

    all_emails = sorted(set(_find_emails(soup, html)).union(extra_emails))[:5]
    all_phones = sorted(set(_find_phones(soup)).union(extra_phones))[:5]

    return {
        "url": url,
        "final_url": resp.url,
        "status_code": resp.status_code,
        "has_ssl": resp.url.startswith("https://"),
        "load_time_seconds": elapsed,
        "page_size_kb": round(len(resp.content) / 1024, 1),
        "title": title,
        "meta_description": description,
        "h1_count": len(soup.find_all("h1")),
        "images_total": len(imgs),
        "images_missing_alt": missing_alt,
        "has_viewport": soup.find("meta", attrs={"name": "viewport"}) is not None,
        "emails": all_emails,
        "phones": all_phones,
        "socials": _find_socials(html),
        "_soup": soup,
        "_html": html,
    }


def save_to_lead(lead_id: str, url: str, result: dict) -> bool:
    """Persist analysis record and update lead attributes."""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return False

        # Save analysis history
        record = WebsiteAnalysisRecord(
            lead_id=lead_id,
            url=url,
            status_code=result.get("status_code"),
            has_ssl=result.get("has_ssl", False),
            emails=json.dumps(result.get("emails", [])),
            phones=json.dumps(result.get("phones", [])),
            socials=json.dumps(result.get("socials", {})),
            analysis_json=json.dumps({k: v for k, v in result.items() if not k.startswith("_")}),
        )
        db.add(record)

        if result.get("error"):
            lead.website_analysis = json.dumps({"url": url, "error": result["error"]})
            lead.website_status = "Broken"
            lead.lead_score = 25
        else:
            payload = {k: v for k, v in result.items() if not k.startswith("_")}
            lead.website_analysis = json.dumps(payload)
            lead.website_status = result.get("website_status", lead.website_status)
            lead.lead_score = result.get("lead_score", lead.lead_score)
            if not lead.current_website:
                lead.current_website = url

            # Extract socials if not already present
            socials = result.get("socials") or {}
            if socials.get("instagram") and not lead.instagram:
                lead.instagram = socials["instagram"]
            if socials.get("facebook") and not lead.facebook:
                lead.facebook = socials["facebook"]

            # If public business email found and lead had no email, update it
            emails = result.get("emails") or []
            if emails and not lead.email:
                lead.email = emails[0]
                lead.email_verification_status = "Valid"

        # Log timeline
        db.add(OutreachActivity(
            lead_id=lead_id,
            activity_type="Website Analyzed",
            description=f"Analyzed {url} — Status: {lead.website_status}, Score: {lead.lead_score}/100",
            result=lead.website_status,
            created_by="Website Analyzer",
        ))

        db.commit()
        return True
    finally:
        db.close()
