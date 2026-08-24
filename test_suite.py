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


if __name__ == "__main__":
    unittest.main()
