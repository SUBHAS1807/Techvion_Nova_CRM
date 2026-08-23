"""
TechvionNova CRM - Website Analyzer & Public Business Email Discovery Engine
Performs deep multi-page crawl of homepage, contact, and about pages to discover
public business email addresses, phone numbers, SSL status, and digital footprint.
"""

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

# Assets and dummy patterns to ignore
IGNORE_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js",
    ".woff", ".woff2", ".ttf", ".eot", ".ico", ".mp4", ".mp3", ".pdf", ".zip"
)

IGNORE_EMAIL_PREFIXES = (
    "noreply", "no-reply", "donotreply", "do-not-reply", "privacy", "sentry",
    "mailer-daemon", "postmaster", "webmaster", "security"
)

IGNORE_EMAIL_DOMAINS = (
    "example.com", "domain.com", "yourdomain.com", "yoursite.com", "email.com",
    "test.com", "sample.com", "wixpress.com", "wix.com", "squarespace.com",
    "weebly.com", "godaddy.com", "cloudflare.com", "schema.org", "sentry.io",
    "wordpress.com", "shopify.com", "google.com", "facebook.com", "instagram.com",
    "github.com", "twitter.com", "linkedin.com", "gravatar.com"
)

PRIORITY_PREFIXES = (
    "info@", "contact@", "hello@", "sales@", "office@", "booking@",
    "reservations@", "enquiry@", "inquiry@", "admin@", "support@", "help@", "service@"
)


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


def _clean_and_rank_emails(email_records: list[tuple[str, str]]) -> tuple[list[str], str | None, str | None]:
    """
    Given a list of (email_candidate, source_page_url) tuples:
    1. Normalize to lowercase and strip.
    2. Filter out false-positive file extensions.
    3. Filter out system / placeholder / dummy emails.
    4. Prioritize canonical business contact addresses.
    Returns: (cleaned_unique_emails, best_primary_email, best_email_source_url)
    """
    valid_map: dict[str, str] = {}  # email -> source_url

    for raw_email, src_url in email_records:
        em = raw_email.strip().lower()
        # Strip trailing punctuation
        em = re.sub(r"[^\w@.-]+$", "", em)
        em = re.sub(r"^[^\w@.-]+", "", em)

        if "@" not in em or em.count("@") != 1:
            continue

        local_part, domain_part = em.split("@", 1)
        if not local_part or not domain_part or "." not in domain_part:
            continue

        # Ignore asset extension false positives
        if any(em.endswith(ext) for ext in IGNORE_EXTENSIONS):
            continue

        # Ignore dummy / system prefixes
        if any(local_part == p or local_part.startswith(p + "@") or local_part.startswith(p + "-") for p in IGNORE_EMAIL_PREFIXES):
            continue

        # Ignore template / placeholder domains
        if any(domain_part == d or domain_part.endswith("." + d) for d in IGNORE_EMAIL_DOMAINS):
            continue

        if em not in valid_map:
            valid_map[em] = src_url

    if not valid_map:
        return [], None, None

    # Ranking function
    def score_email(item: tuple[str, str]) -> int:
        email_str = item[0]
        score = 0
        for idx, pref in enumerate(PRIORITY_PREFIXES):
            if email_str.startswith(pref):
                score += (len(PRIORITY_PREFIXES) - idx) * 10
                break
        return score

    sorted_pairs = sorted(valid_map.items(), key=score_email, reverse=True)
    cleaned_list = [p[0] for p in sorted_pairs][:5]
    primary_email = sorted_pairs[0][0]
    primary_source_url = sorted_pairs[0][1]

    return cleaned_list, primary_email, primary_source_url


def _extract_page_emails(soup: BeautifulSoup, html: str, page_url: str) -> list[tuple[str, str]]:
    """Extract raw email candidates from text, HTML, and mailto: links."""
    candidates = []
    # 1. mailto: links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            email_part = href[7:].split("?")[0].strip()
            if email_part:
                candidates.append((email_part, page_url))

    # 2. Text regex
    for m in EMAIL_RE.findall(html):
        candidates.append((m, page_url))

    return candidates


def _extract_page_phones(soup: BeautifulSoup) -> list[str]:
    found = set()
    for a in soup.find_all("a", href=True):
        if a["href"].lower().startswith("tel:"):
            phone_val = a["href"][4:].strip()
            if phone_val:
                found.add(phone_val)
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

    if analysis.get("primary_email") or (analysis.get("emails") and len(analysis["emails"]) > 0):
        score += 5
        breakdown.append("+5 Public Business Email Discovered")

    final_score = min(score, 100)
    return final_score, breakdown


def fetch_analysis(url: str) -> dict:
    """
    Crawl website homepage and relevant subpages (Contact, About)
    to discover public contact details, SSL certificate, responsiveness.
    """
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

    # Collect email candidates from homepage
    all_raw_emails = _extract_page_emails(soup, html, resp.url)
    all_raw_phones = _extract_page_phones(soup)

    # Search contact / about subpages
    subpages_checked = 0
    max_subpages = 2
    seen_urls = {resp.url.rstrip("/")}

    for a in soup.find_all("a", href=True):
        if subpages_checked >= max_subpages:
            break
        href = a["href"].strip().lower()
        # Identify contact / about / reach-us links
        if any(w in href for w in ["contact", "reach", "about", "get-in-touch", "location"]):
            target_sub = urljoin(resp.url, a["href"].strip())
            norm_target = target_sub.rstrip("/")
            if norm_target in seen_urls:
                continue
            # Keep within same domain
            if urlparse(target_sub).netloc.lower() == urlparse(resp.url).netloc.lower():
                seen_urls.add(norm_target)
                try:
                    sub_resp = requests.get(target_sub, headers=HEADERS, timeout=6)
                    if sub_resp.status_code == 200:
                        sub_soup = BeautifulSoup(sub_resp.text[:1_000_000], "html.parser")
                        all_raw_emails.extend(_extract_page_emails(sub_soup, sub_resp.text, target_sub))
                        all_raw_phones.extend(_extract_page_phones(sub_soup))
                        subpages_checked += 1
                except Exception:
                    pass

    # Clean, rank, and prioritize emails
    cleaned_emails, primary_email, email_source_url = _clean_and_rank_emails(all_raw_emails)
    all_phones = sorted(set(all_raw_phones))[:5]

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
        "emails": cleaned_emails,
        "primary_email": primary_email,
        "email_source": "Business Website" if primary_email else None,
        "email_source_url": email_source_url if primary_email else None,
        "phones": all_phones,
        "socials": _find_socials(html),
        "_soup": soup,
        "_html": html,
    }


def save_to_lead(lead_id: str, url: str, result: dict) -> bool:
    """
    Persist website analysis record and update EXISTING lead in-place.
    Never creates a duplicate lead.
    """
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.lead_id == lead_id).first()
        if not lead:
            return False

        # Save analysis history record
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

            # Update socials if discovered and not already present
            socials = result.get("socials") or {}
            if socials.get("instagram") and not lead.instagram:
                lead.instagram = socials["instagram"]
            if socials.get("facebook") and not lead.facebook:
                lead.facebook = socials["facebook"]

            # Save discovered email to the existing lead
            primary_email = result.get("primary_email") or (result.get("emails") or [None])[0]
            if primary_email:
                lead.email = primary_email
                lead.email_source = "Business Website"
                lead.email_source_url = result.get("email_source_url") or url
                lead.email_verification_status = "Valid Format"
            elif not lead.email:
                lead.email_verification_status = "Not Checked"

        # Log timeline
        db.add(OutreachActivity(
            lead_id=lead_id,
            activity_type="Website Analyzed",
            description=f"Analyzed {url} — Status: {lead.website_status}, Score: {lead.lead_score}/100" + (f", Email: {lead.email}" if lead.email else ""),
            result=lead.website_status,
            created_by="Website Analyzer",
        ))

        db.commit()
        return True
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════

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


@analyzer_bp.route("/api/analyze/bulk", methods=["POST"])
@analyzer_bp.route("/api/website/analyze-batch", methods=["POST"])
def analyze_bulk():
    """
    Bulk analyze website for a list of lead IDs.
    Returns structured stats: processed, emails_found, no_email, errors.
    """
    data = request.get_json(force=True) or {}
    lead_ids = data.get("lead_ids") or []

    if not lead_ids:
        return jsonify({"error": "lead_ids list is required"}), 400

    db = SessionLocal()
    leads_to_process = []
    try:
        leads = db.query(Lead).filter(Lead.lead_id.in_(lead_ids)).all()
        for l in leads:
            if l.current_website and l.current_website.strip():
                leads_to_process.append({"lead_id": l.lead_id, "website": l.current_website})
    finally:
        db.close()

    processed_count = 0
    emails_found_count = 0
    no_email_count = 0
    errors_count = 0
    results = []

    for item in leads_to_process:
        lid = item["lead_id"]
        web = normalize_url(item["website"])
        if not web:
            errors_count += 1
            continue

        try:
            res = fetch_analysis(web)
            if res.get("error"):
                errors_count += 1
                save_to_lead(lid, web, res)
            else:
                ws, feat = classify_website(res["_soup"], res["_html"], res["status_code"])
                res["website_status"] = ws
                res["features"] = feat
                sc, brk = compute_lead_score(ws, res)
                res["lead_score"] = sc
                res["score_breakdown"] = brk

                res.pop("_soup", None)
                res.pop("_html", None)
                save_to_lead(lid, web, res)

                if res.get("primary_email") or (res.get("emails") and len(res["emails"]) > 0):
                    emails_found_count += 1
                else:
                    no_email_count += 1

            processed_count += 1
            results.append({
                "lead_id": lid,
                "website": web,
                "email": res.get("primary_email"),
                "status": res.get("website_status", "Broken"),
            })
        except Exception as e:
            errors_count += 1
            results.append({"lead_id": lid, "website": web, "error": str(e)})

    return jsonify({
        "total_requested": len(lead_ids),
        "processed": processed_count,
        "emails_found": emails_found_count,
        "no_email": no_email_count,
        "errors": errors_count,
        "results": results,
    })
