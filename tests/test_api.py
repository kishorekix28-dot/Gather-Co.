from django.db import connection
from django.test import TestCase

from assistant.models import FAQ, ErrorCode

from .helpers import PASSWORD, make_product, make_user

REQUIRED_CODES = [400, 401, 403, 404, 405, 408, 429, 500]


class FAQApiTests(TestCase):
    def test_faqs_are_stored_in_sql(self):
        self.assertGreaterEqual(FAQ.objects.filter(is_active=True).count(), 10)
        with connection.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {FAQ._meta.db_table} WHERE is_active = %s", [True])
            self.assertGreaterEqual(cur.fetchone()[0], 10)

    def test_list_faqs(self):
        resp = self.client.get("/api/faqs/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(len(data), 10)
        self.assertEqual(set(data[0]), {"id", "question", "answer", "category", "is_active", "created_at", "updated_at"})
        db_questions = set(FAQ.objects.filter(is_active=True).values_list("question", flat=True))
        self.assertEqual({f["question"] for f in data}, db_questions)

    def test_faq_detail_and_404(self):
        faq = FAQ.objects.first()
        resp = self.client.get(f"/api/faqs/{faq.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["question"], faq.question)
        self.assertEqual(self.client.get("/api/faqs/999999/").status_code, 404)

    def test_faq_search(self):
        resp = self.client.get("/api/faqs/search/", {"q": "stock"})
        data = resp.json()
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(data["count"], 0)
        for item in data["results"]:
            blob = (item["question"] + item["answer"] + item["category"]).lower()
            self.assertTrue("stock" in blob or FAQ.objects.get(pk=item["id"]).keywords.lower().count("stock"))

    def test_faq_changes_are_reflected(self):
        FAQ.objects.create(question="Brand new question about pallets?", answer="Pallet answer", category="Stock")
        questions = [f["question"] for f in self.client.get("/api/faqs/").json()]
        self.assertIn("Brand new question about pallets?", questions)

    def test_faq_write_requires_admin(self):
        payload = {"question": "Q?", "answer": "A", "category": "General"}
        self.assertIn(self.client.post("/api/faqs/", payload).status_code, (401, 403))
        make_user("staff")
        self.client.login(username="staff", password=PASSWORD)
        self.assertEqual(self.client.post("/api/faqs/", payload).status_code, 403)
        make_user("boss", "ADMIN")
        self.client.login(username="boss", password=PASSWORD)
        self.assertEqual(self.client.post("/api/faqs/", payload).status_code, 201)

    def test_faq_page_uses_api_not_hardcoded_content(self):
        resp = self.client.get("/faq/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "js/faq.js")
        for faq in FAQ.objects.all():
            self.assertNotContains(resp, faq.answer[:40])


class ErrorCodeApiTests(TestCase):
    def test_all_required_error_codes_exist(self):
        codes = [e["code"] for e in self.client.get("/api/errors/").json()]
        for code in REQUIRED_CODES:
            self.assertIn(code, codes)
        self.assertGreaterEqual(ErrorCode.objects.count(), 8)

    def test_error_detail(self):
        for code in REQUIRED_CODES:
            resp = self.client.get(f"/api/errors/{code}/")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["code"], code)
            for field in ("title", "description", "possible_causes", "recommended_solution", "created_at"):
                self.assertTrue(data[field])
        self.assertEqual(self.client.get("/api/errors/404/").json()["title"], "Page Not Found")
        self.assertEqual(self.client.get("/api/errors/499/").status_code, 404)

    def test_error_search(self):
        data = self.client.get("/api/errors/search/", {"q": "unauthorized"}).json()
        self.assertEqual([r["code"] for r in data["results"]], [401])
        data = self.client.get("/api/errors/search/", {"q": "500"}).json()
        self.assertIn(500, [r["code"] for r in data["results"]])


class SecuredApiTests(TestCase):
    def test_inventory_api_requires_authentication(self):
        for url in ("/api/products/", "/api/inventory/summary/", "/api/tickets/"):
            self.assertIn(self.client.get(url).status_code, (401, 403), url)

    def test_inventory_api_for_staff(self):
        make_user("staff")
        make_product(sku="API-1", qty=3)
        self.client.login(username="staff", password=PASSWORD)
        data = self.client.get("/api/products/", {"q": "API"}).json()
        self.assertEqual(data[0]["sku"], "API-1")
        self.assertEqual(self.client.get("/api/inventory/summary/").json()["total_products"], 1)
