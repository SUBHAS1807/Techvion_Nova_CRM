"""
Comprehensive Automated Verification Suite for TechvionNova CRM
Tests Google Places API (New) endpoints, duplicate detection, lead scoring,
website analysis, CSV import/export, and pagination.
"""
import unittest
import json
import io
from backend.app import app
from backend.database import SessionLocal
from backend.models import Lead, CollectionJob

class TestTechvionNovaCRM(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_01_status_endpoint(self):
        resp = self.app.get('/api/google-places/status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("configured", data)
        self.assertIn("cities", data)
        self.assertIn("business_types", data)
        print("[PASS] Test 1: Status endpoint functional")

    def test_02_connection_test(self):
        resp = self.app.post('/api/google-places/test')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("ok", data)
        print(f"[PASS] Test 2: Google API connection test returned ok={data.get('ok')}")

    def test_03_leads_pagination_and_filter(self):
        resp = self.app.get('/api/leads?skip=0&limit=10')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("total", data)
        self.assertIn("leads", data)
        self.assertLessEqual(len(data["leads"]), 10)
        print(f"[PASS] Test 3: Leads pagination returned {len(data['leads'])} of {data['total']} leads")

    def test_04_import_and_duplicate_detection(self):
        # Create a new unique lead via import
        test_place = {
            "google_place_id": "TEST_PLACE_ID_99999",
            "business_name": "Test Speciality Coffee House",
            "business_type": "Cafe",
            "city": "Kolkata",
            "phone": "+91 99999 11111",
            "current_website": "https://testcoffeehouse999.in",
            "address": "123 Park Street, Kolkata",
            "rating": 4.8,
            "review_count": 120,
        }

        # 1. First import should succeed (200 or 201 or 409 if already present)
        resp1 = self.app.post('/api/google-places/import', json={"place": test_place})
        if resp1.status_code == 409:
            data1 = resp1.get_json()
            created_id = data1["existing_lead"]["lead_id"]
        else:
            self.assertIn(resp1.status_code, [200, 201])
            data1 = resp1.get_json()
            self.assertTrue(data1.get("ok"))
            created_id = data1["lead"]["lead_id"]

        # 2. Duplicate import without force should return 409
        resp2 = self.app.post('/api/google-places/import', json={"place": test_place, "update_existing": False})
        self.assertEqual(resp2.status_code, 409)
        data2 = resp2.get_json()
        self.assertTrue(data2.get("duplicate"))
        self.assertEqual(data2["existing_lead"]["lead_id"], created_id)

        # 3. Duplicate import with update_existing=True should succeed
        test_place["rating"] = 4.9
        resp3 = self.app.post('/api/google-places/import', json={"place": test_place, "update_existing": True})
        self.assertEqual(resp3.status_code, 200)
        data3 = resp3.get_json()
        self.assertEqual(data3.get("action"), "updated")

        print("[PASS] Test 4: 5-level duplicate detection and update flow verified")

    def test_05_website_analyzer(self):
        # Analyze a test URL
        resp = self.app.post('/api/website/analyze', json={"url": "https://example.com"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("website_status", data)
        self.assertIn("lead_score", data)
        self.assertIn("score_breakdown", data)
        print(f"[PASS] Test 5: Website analyzer returned status={data['website_status']}, score={data['lead_score']}/100")

    def test_06_csv_export(self):
        resp = self.app.get('/api/leads/export?mode=all')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "text/csv")
        content = resp.data.decode('utf-8')
        self.assertIn("Lead ID", content)
        self.assertIn("Business Name", content)
        print("[PASS] Test 6: CSV Export successfully generated")

    def test_07_analytics_endpoint(self):
        resp = self.app.get('/api/analytics')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("cards", data)
        self.assertIn("charts", data)
        self.assertIn("total_leads", data["cards"])
        print(f"[PASS] Test 7: Analytics endpoint returned {data['cards']['total_leads']} total leads")

    def test_08_collection_jobs(self):
        resp = self.app.get('/api/collection-jobs')
        self.assertEqual(resp.status_code, 200)
        jobs = resp.get_json()
        self.assertIsInstance(jobs, list)
        print(f"[PASS] Test 8: Collection jobs list returned {len(jobs)} jobs")


class TestEmailExtractionPipeline(unittest.TestCase):
    """Offline unit tests for the public-website email discovery engine."""

    def setUp(self):
        from backend.routes.analyzer import (
            _clean_and_rank_emails, strip_invisible_html,
            _extract_page_emails, get_root_domain,
        )
        from bs4 import BeautifulSoup
        self.rank = _clean_and_rank_emails
        self.strip = strip_invisible_html
        self.extract = _extract_page_emails
        self.soup = lambda h: BeautifulSoup(h, "html.parser")
        self.root = get_root_domain
        self.app = app.test_client()
        self.app.testing = True

    def test_10_commented_out_emails_are_stripped(self):
        # Real case: indiancoffeehouse.in ships commented-out theme credits
        html = '<!-- <a href="mailto:info@superv.com">info@superv.com</a> -->' \
               '<a href="mailto:biz1958@gmail.com">biz1958@gmail.com</a>'
        cleaned = self.strip(html)
        emails, primary, _ = self.rank(self.extract(self.soup(cleaned), cleaned, "https://x.in"), site_domain="indiancoffeehouse.in")
        self.assertEqual(primary, "biz1958@gmail.com")
        self.assertNotIn("info@superv.com", emails)
        print("[PASS] Test 10: HTML-comment template credits ignored")

    def test_11_placeholder_domains_rejected(self):
        recs = [("info@mysite.com", "https://site.com/", False),
                ("tch.foods@gmail.com", "https://site.com/contact-us", True)]
        _, primary, src = self.rank(recs, site_domain="thecountryhouse.in")
        self.assertEqual(primary, "tch.foods@gmail.com")
        self.assertIn("contact-us", (src or ""))
        print("[PASS] Test 11: Placeholder domains (mysite.com) rejected; real mailto chosen")

    def test_12_own_domain_email_wins_over_generic_prefix(self):
        recs = [("info@someother.biz", "https://acme.co.in/", True),
                ("hello@acme.co.in", "https://acme.co.in/about", False)]
        _, primary, _ = self.rank(recs, site_domain="www.acme.co.in")
        self.assertEqual(primary, "hello@acme.co.in")
        print("[PASS] Test 12: Business's own-domain email outranks foreign info@ address")

    def test_13_noreply_and_sentry_hashes_filtered(self):
        recs = [("noreply@site.com", "u", False),
                ("no-reply@site.com", "u", False),
                ("9a65e97ebe8141fca0c4fd686f70996b@sentry.wixpress.com", "u", False),
                ("e0b4d631da7b4200828051f7f9c783e3@sentry-next.wixpress.com", "u", False),
                ("office@realbusiness.com", "u", False)]
        _, primary, _ = self.rank(recs)
        self.assertEqual(primary, "office@realbusiness.com")
        print("[PASS] Test 13: noreply / sentry-hash junk filtered")

    def test_14_no_email_generated_from_domain(self):
        recs = []
        emails, primary, _ = self.rank(recs, site_domain="roasterycoffee.co.in")
        self.assertIsNone(primary)
        self.assertEqual(emails, [])
        print("[PASS] Test 14: No candidates => no fabricated email (NULL stays NULL)")

    def test_15_normalization_and_syntax_validation(self):
        recs = [("  HELLO@RealBusiness.COM. ", "u", False), ("bad-email-no-at", "u", False),
                ("a@b", "u", False), ("x.png@2x", "u", False), ("hello@example.com", "u", False)]
        emails, primary, _ = self.rank(recs)
        self.assertEqual(emails, ["hello@realbusiness.com"])
        print("[PASS] Test 15: Lowercase/trim normalization + syntax validation + placeholder rejection")

    def test_16_script_style_js_blobs_never_yield_emails(self):
        html = '<script>var dsn="https://abc123@sentry.io/1";</script>' \
               '<style>.a{content:"x@y.com"}</style><p>Contact: team@realsite.in</p>'
        cleaned = self.strip(html)
        emails, primary, _ = self.rank(self.extract(self.soup(cleaned), cleaned, "https://realsite.in"), site_domain="realsite.in")
        self.assertEqual(primary, "team@realsite.in")
        self.assertNotIn("abc123@sentry.io", emails)
        print("[PASS] Test 16: script/style blobs excluded from email scan")

    def test_17_get_root_domain_handles_coin_suffixes(self):
        self.assertEqual(self.root("www.acme.co.in"), "acme.co.in")
        self.assertEqual(self.root("mail.example.org"), "example.org")
        print("[PASS] Test 17: Root-domain computation handles co.in style suffixes")

    def test_18_leads_api_exposes_email_status_fields(self):
        resp = self.app.get('/api/leads?limit=1')
        data = resp.get_json()
        lead = data["leads"][0]
        for field in ("email", "email_source", "email_source_url", "email_status"):
            self.assertIn(field, lead)
        print("[PASS] Test 18: /api/leads returns email + email_status fields")


class TestWorldwideCollector(unittest.TestCase):
    """Offline unit tests for the global (multi-country) collection engine."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_19_geo_database_integrity_and_lookup(self):
        from backend.geo_data import COUNTRIES, find_country
        required = ("US", "GB", "CA", "AU", "IN", "DE", "FR", "IT", "ES",
                    "BR", "MX", "JP", "KR", "SG", "AE", "SA", "ZA", "NZ")
        for iso in required:
            c = COUNTRIES.get(iso)
            self.assertIsNotNone(c, f"{iso} missing from country DB")
            for key in ("name", "iso2", "iso3", "phone_code", "currency"):
                self.assertTrue(c[key], f"{iso}.{key} empty")
        self.assertEqual(find_country("india")["iso2"], "IN")
        self.assertEqual(find_country("usa")["iso2"], "US")
        self.assertEqual(find_country("GBR")["name"], "United Kingdom")
        print(f"[PASS] Test 19: Geo database integrity ({len(COUNTRIES)} countries, lookups OK)")

    def test_20_international_phone_normalization(self):
        from backend.geo_data import normalize_intl_phone
        self.assertEqual(normalize_intl_phone("020 7946 0958", "GB"), "+442079460958")
        self.assertEqual(normalize_intl_phone("+44 20 7946 0958", "GB"), "+442079460958")
        self.assertEqual(normalize_intl_phone("(415) 555-2671", "US"), "+14155552671")
        self.assertEqual(normalize_intl_phone("+91 98300 12345", "IN"), "+919830012345")
        print("[PASS] Test 20: Phone numbers normalize to international format")

    def test_21_search_chunk_builder_worldwide(self):
        from backend.geo_data import build_search_chunks
        chunks = build_search_chunks(["US", "GB", "JP"], "", "", "Cafe", "")
        self.assertEqual(len(chunks), 3)
        self.assertIn("Cafe in United States", chunks[0]["query"])
        self.assertEqual(chunks[1]["country_iso2"], "GB")
        # city+region refinement lands inside the query
        ch2 = build_search_chunks(["FR"], "Île-de-France", "Paris", "Bakery", "")[0]
        self.assertEqual(ch2["query"], "Bakery in Paris, Île-de-France, France")
        # keyword overrides category
        ch3 = build_search_chunks(["DE"], "", "", "Cafe", "wedding photographer")[0]
        self.assertTrue(ch3["query"].startswith("wedding photographer in Germany"))
        print("[PASS] Test 21: Worldwide chunk builder produces per-country targets")

    def test_22_google_address_component_parser(self):
        from backend.routes.global_collect import parse_address_components
        place = {"addressComponents": [
            {"longText": "1600 Amphitheatre Pkwy", "shortText": "1600 Amphitheatre Pkwy", "types": ["street_number"]},
            {"longText": "Mountain View", "shortText": "Mountain View", "types": ["locality", "political"]},
            {"longText": "California", "shortText": "CA", "types": ["administrative_area_level_1", "political"]},
            {"longText": "94043", "shortText": "94043", "types": ["postal_code"]},
            {"longText": "United States", "shortText": "US", "types": ["country", "political"]},
        ]}
        geo = parse_address_components(place)
        self.assertEqual(geo["country_code"], "US")
        self.assertEqual(geo["region"], "California")
        self.assertEqual(geo["city"], "Mountain View")
        self.assertEqual(geo["postal_code"], "94043")
        print("[PASS] Test 22: addressComponents parsed into country/region/city/postal")

    def test_23_analysis_results_map_to_email_statuses(self):
        from backend.routes.global_collect import _apply_analysis_result
        from backend.models import DiscoveredBusiness

        def make_disc():
            d = DiscoveredBusiness(place_id=f"T{datetime_now_ns()}", business_name="X")
            return d

        class FakeJob:
            emails_found = 0
            errors = 0

        job = FakeJob()

        d1 = make_disc()
        _apply_analysis_result(None, d1, {"status_code": 200,
                                          "primary_email": "Owner@Biz.com ",
                                          "emails": ["owner@biz.com"],
                                          "email_source_url": "https://biz.com/contact"},
                               job)
        self.assertEqual(d1.email_status, "EMAIL_FOUND")
        self.assertEqual(d1.email, "owner@biz.com")

        d2 = make_disc()
        _apply_analysis_result(None, d2, {"status_code": 403, "blocked": True,
                                          "error": "Website refused automated access"}, job)
        self.assertEqual(d2.email_status, "WEBSITE_UNAVAILABLE")

        d3 = make_disc()
        _apply_analysis_result(None, d3, {"status_code": 200, "primary_email": "no-at-sign", "emails": []}, job)
        self.assertEqual(d3.email_status, "EMAIL_NOT_FOUND")

        d4 = make_disc()
        _apply_analysis_result(None, d4, {"status_code": 0, "error": "Connection failed"}, job)
        self.assertEqual(d4.email_status, "WEBSITE_UNAVAILABLE")
        print("[PASS] Test 23: Analysis results map onto spec email_status enums")

    def test_24_qualification_creates_lead_with_global_fields(self):
        from backend.database import SessionLocal
        from backend.models import DiscoveredBusiness, Lead
        from backend.routes.global_collect import upsert_qualified_lead

        db = SessionLocal()
        try:
            disc = DiscoveredBusiness(
                place_id="TEST_QUALI_PLACE_1",
                business_name="Global Test Bakery",
                business_type="Bakery",
                address="1 Rue de Test",
                country_code="FR",
                country_name="France",
                region="Île-de-France",
                city="Paris",
                postal_code="75001",
                phone_raw="01 23 45 67 89",
                phone_intl="+33123456789",
                website_url="https://globaltestbakery.fr",
                has_website=True,
                email="bonjour@globaltestbakery.fr",
                email_source_page="https://globaltestbakery.fr/contact",
                email_status="EMAIL_FOUND",
            )
            lead, action = upsert_qualified_lead(db, disc, None)
            db.rollback()   # never persist test data
            self.assertEqual(action, "created")
            self.assertEqual(lead.email, "bonjour@globaltestbakery.fr")
            self.assertEqual(lead.email_status, "Found")
            self.assertEqual(lead.country, "France")
            self.assertEqual(lead.country_code, "FR")
            self.assertEqual(lead.currency, "EUR")     # derived from geo database
            self.assertEqual(lead.state_province, "Île-de-France")
            self.assertEqual(lead.phone, "+33123456789")
            print("[PASS] Test 24: Qualified promotion fills global fields + currency")
        finally:
            db.close()

    def test_25_global_meta_stats_export_endpoints(self):
        resp = self.app.get('/api/global/meta')
        self.assertEqual(resp.status_code, 200)
        meta = resp.get_json()
        self.assertGreaterEqual(len(meta["countries"]), 70)
        self.assertGreaterEqual(len(meta["categories"]), 30)

        resp_us = self.app.get('/api/global/meta?country=US')
        meta_us = resp_us.get_json()
        self.assertIn("California", meta_us["regions"])
        self.assertIn("New York", meta_us["cities"])

        resp_stats = self.app.get('/api/global/stats')
        self.assertEqual(resp_stats.status_code, 200)
        self.assertIn("funnel", resp_stats.get_json())

        resp_exp = self.app.get('/api/leads/export/global/csv')
        self.assertEqual(resp_exp.status_code, 200)
        content = resp_exp.data.decode("utf-8")
        self.assertIn("Country", content)
        self.assertIn("Currency", content)
        self.assertIn("TechvionNova_Global_Leads", resp_exp.headers.get("Content-Disposition", ""))
        print("[PASS] Test 25: global meta/stats/qualified-export endpoints functional")


class TestWebsiteStatusFilter(unittest.TestCase):
    """Website-status classification, targeting & qualification gating."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_26_website_status_classifier(self):
        from backend.routes.global_collect import (
            classify_website_status, WS_NO_WEBSITE, WS_HAS_WEBSITE,
            WEBSITE_STATUSES,
        )
        self.assertEqual(classify_website_status("https://biz.com"), WS_HAS_WEBSITE)
        self.assertEqual(classify_website_status("  https://biz.com  "), WS_HAS_WEBSITE)
        self.assertEqual(classify_website_status(None), WS_NO_WEBSITE)
        self.assertEqual(classify_website_status(""), WS_NO_WEBSITE)
        self.assertEqual(classify_website_status("   "), WS_NO_WEBSITE)
        # A failed fetch must NEVER classify as NO_WEBSITE — separate enum exists
        self.assertIn(WS_NO_WEBSITE, WEBSITE_STATUSES)
        self.assertNotIn("WEBSITE_ERROR", WEBSITE_STATUSES)
        print("[PASS] Test 26: URL presence classifies HAS/NO_WEBSITE (never guesses)")

    def test_27_analysis_maps_inaccessible_not_no_website(self):
        """Blocked / unreachable sites are WEBSITE_INACCESSIBLE — never NO_WEBSITE."""
        from backend.routes.global_collect import (
            _apply_analysis_result, WS_INACCESSIBLE, WS_HAS_WEBSITE,
        )

        class FakeJob:
            emails_found = 0
            errors = 0

        job = FakeJob()

        d1 = DiscoveredBusinessFactory()
        _apply_analysis_result(None, d1, {"status_code": 403, "blocked": True,
                                          "error": "Cloudflare challenge"}, job)
        self.assertEqual(d1.website_status, WS_INACCESSIBLE)

        d2 = DiscoveredBusinessFactory()
        _apply_analysis_result(None, d2, {"status_code": 0, "error": "DNS failure"}, job)
        self.assertEqual(d2.website_status, WS_INACCESSIBLE)

        d3 = DiscoveredBusinessFactory()
        _apply_analysis_result(None, d3, {"status_code": 200, "primary_email":
                                          "hi@ok.com", "emails": ["hi@ok.com"]}, job)
        self.assertEqual(d3.website_status, WS_HAS_WEBSITE)
        print("[PASS] Test 27: blocked/unreachable → WEBSITE_INACCESSIBLE; reachable → HAS_WEBSITE")

    def test_28_no_website_qualification_and_lead_fields(self):
        """🎯 opportunity path: NO_WEBSITE + public email → qualified lead."""
        from backend.database import SessionLocal
        from backend.models import DiscoveredBusiness
        from backend.routes.global_collect import upsert_qualified_lead, WS_NO_WEBSITE

        db = SessionLocal()
        try:
            disc = DiscoveredBusiness(
                place_id="TEST_NOWS_PLACE_1",
                business_name="No-Site Test Diner",
                country_code="US",
                country_name="United States",
                city="Austin",
                email="owner@nositediner.com",
                email_source_page="https://facebook.com/nositediner",
                email_status="EMAIL_FOUND",
                website_url=None,
                has_website=False,
                website_status=WS_NO_WEBSITE,
            )
            lead, action = upsert_qualified_lead(db, disc, None)
            db.rollback()   # never persist test data
            self.assertEqual(action, "created")
            self.assertEqual(lead.website_status_code, "NO_WEBSITE")
            self.assertEqual(lead.website_status, "No Website")
            self.assertEqual(lead.current_website, "")          # honest empty site field
            self.assertGreaterEqual(lead.lead_score or 0, 75)   # prime prospect score
            self.assertIn("WEBSITE OPPORTUNITY", lead.remarks or "")
            print("[PASS] Test 28: NO_WEBSITE+email promotes as 🎯 website-opportunity lead")
        finally:
            db.close()

    def test_29_leads_filter_by_machine_website_status(self):
        """/api/leads?website_status=NO_WEBSITE routes to website_status_code."""
        resp_all = self.app.get('/api/leads')
        self.assertEqual(resp_all.status_code, 200)
        resp_ws = self.app.get('/api/leads?website_status=NO_WEBSITE')
        self.assertEqual(resp_ws.status_code, 200)
        rows = resp_ws.get_json().get("leads", [])
        for r in rows:
            self.assertEqual(r.get("website_status_code"), "NO_WEBSITE")
        # legacy human value still works unchanged
        resp_legacy = self.app.get('/api/leads?website_status=Good')
        self.assertEqual(resp_legacy.status_code, 200)
        print(f"[PASS] Test 29: CRM filter supports machine codes "
              f"({len(rows)} no-website leads) and legacy values")

    def test_30_stats_meta_export_expose_opportunity_metrics(self):
        resp = self.app.get('/api/global/stats')
        self.assertEqual(resp.status_code, 200)
        stats = resp.get_json()
        wo = stats.get("website_opportunity", {})
        for key in ("businesses_without_website", "emails_found_without_website",
                    "opportunity_leads", "by_website_status"):
            self.assertIn(key, wo)
        self.assertEqual(wo["businesses_without_website"],
                         wo["by_website_status"].get("NO_WEBSITE"))

        meta = self.app.get('/api/global/meta').get_json()
        ws_values = [o["value"] for o in meta.get("website_statuses", [])]
        for v in ("ALL", "NO_WEBSITE", "HAS_WEBSITE",
                  "WEBSITE_INACCESSIBLE", "WEBSITE_UNKNOWN"):
            self.assertIn(v, ws_values)

        csv_exp = self.app.get('/api/leads/export/global/csv')
        content = csv_exp.data.decode("utf-8")
        self.assertIn("Website Status", content)   # export carries the classification
        print("[PASS] Test 30: stats/meta/export expose website-opportunity metrics")


def DiscoveredBusinessFactory():
    from backend.models import DiscoveredBusiness
    return DiscoveredBusiness(place_id=f"T{datetime_now_ns()}",
                              business_name="WS Test Biz")


def datetime_now_ns():
    import time as _t
    return str(_t.time_ns())


if __name__ == "__main__":
    unittest.main()
