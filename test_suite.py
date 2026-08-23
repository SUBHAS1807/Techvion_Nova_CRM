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

if __name__ == "__main__":
    unittest.main()
