"""Assistant, ticket and MongoDB tests. Uses the MongoDB server from MONGODB_URI
with an isolated test database (dropped after the run)."""
import json
import os
import unittest

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from pymongo import MongoClient

from assistant import mongo
from assistant.engine import answer
from assistant.models import ErrorCode
from support.models import Ticket

from .helpers import PASSWORD, make_user

TEST_MONGO_DB = "inventory_assistant_test"
MONGO_URI = os.environ.get("MONGODB_URI", "")


def mongo_available():
    if not MONGO_URI:
        return False
    try:
        MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500).admin.command("ping")
        return True
    except Exception:
        return False


class EngineTests(TestCase):
    FAQ_QUESTIONS = {
        "How do I add a product?": "How do I add a new product?",
        "How do I book an item?": "How do I book or reserve items?",
        "How do I update stock?": "How do I record stock-in?",
        "How do I check low-stock products?": "How do I check low-stock products?",
        "How do I export inventory?": "How do I export inventory reports?",
        "How do I add a supplier?": "How do I add a supplier?",
        "How do I change my password?": "How do I change my password?",
        "How do I view inventory history?": "How do I view inventory history?",
        "How do I delete a product?": "How do I delete a product?",
    }

    def test_faq_questions_answered_from_database(self):
        for asked, expected in self.FAQ_QUESTIONS.items():
            result = answer(asked)
            self.assertEqual(result.source, "faq", asked)
            self.assertEqual(result.matched["question"], expected, asked)
            self.assertFalse(result.needs_ticket)

    def test_help_documentation(self):
        result = answer("Why is my product not appearing?")
        self.assertEqual(result.source, "help_docs")
        self.assertIn("filters", result.answer)

    def test_error_code_explanations_from_database(self):
        for code in (400, 401, 403, 404, 405, 408, 429, 500):
            result = answer(f"What does error {code} mean?")
            err = ErrorCode.objects.get(code=code)
            self.assertEqual(result.source, "error_database")
            self.assertIn(err.title, result.answer)
            self.assertIn(err.recommended_solution, result.answer)
        self.assertEqual(answer("what does unauthorized error mean").matched["code"], 401)

    def test_database_changes_drive_answers(self):
        ErrorCode.objects.filter(code=404).update(recommended_solution="UNIQUE-SOLUTION-TEXT")
        self.assertIn("UNIQUE-SOLUTION-TEXT", answer("error 404?").answer)

    def test_unknown_questions_need_ticket(self):
        for q in ("What is the weather in Paris?", "How do I integrate with SAP ERP?", "What does error 418 mean?"):
            result = answer(q)
            self.assertTrue(result.needs_ticket, q)
            self.assertEqual(result.source, "ai_fallback")


@unittest.skipUnless(mongo_available(), "MongoDB server not reachable")
@override_settings(MONGODB_URI=MONGO_URI, MONGODB_DB_NAME=TEST_MONGO_DB)
class ChatEndpointTests(TestCase):
    def setUp(self):
        mongo.reset_client()
        self.raw = MongoClient(MONGO_URI)[TEST_MONGO_DB]
        for name in ("conversations", "messages", "feedback"):
            self.raw[name].delete_many({})

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        MongoClient(MONGO_URI).drop_database(TEST_MONGO_DB)
        mongo.reset_client()

    def chat(self, message, client=None):
        client = client or self.client
        return client.post(reverse("assistant:chat"), json.dumps({"message": message}), content_type="application/json")

    def test_faq_answer_is_stored_in_mongodb(self):
        resp = self.chat("How do I add a product?")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["source"], "faq")
        self.assertTrue(data["stored"])
        msg = self.raw.messages.find_one({"conversation_id": data["conversation_id"]})
        self.assertEqual(msg["user_message"], "How do I add a product?")
        self.assertEqual(msg["assistant_response"], data["reply"])
        self.assertEqual(msg["source"], "faq")
        self.assertIn("timestamp", msg)
        conv = self.raw.conversations.find_one({"conversation_id": data["conversation_id"]})
        self.assertIsNotNone(conv["session_id"])
        self.assertIsNone(conv["user_id"])
        self.assertIn("created_at", conv)
        self.assertIn("updated_at", conv)

    def test_logged_in_user_id_recorded(self):
        user = make_user("staff")
        self.client.login(username="staff", password=PASSWORD)
        data = self.chat("What does error 500 mean?").json()
        self.assertEqual(data["source"], "error_database")
        conv = self.raw.conversations.find_one({"conversation_id": data["conversation_id"]})
        self.assertEqual(conv["user_id"], user.pk)

    def test_unknown_question_creates_single_ticket(self):
        user = make_user("staff")
        self.client.login(username="staff", password=PASSWORD)
        first = self.chat("How do I connect the warehouse forklift telemetry?").json()
        self.assertEqual(first["source"], "ai_fallback")
        self.assertTrue(first["ticket"]["created"])
        ticket = Ticket.objects.get(ticket_id=first["ticket"]["ticket_id"])
        self.assertEqual(ticket.user, user)
        self.assertEqual(ticket.source, "ASSISTANT")
        self.assertIn("forklift telemetry", ticket.description)
        self.assertIn(ticket.ticket_id, first["reply"])
        # Same question in same conversation -> no duplicate
        second = self.chat("how do i connect the warehouse  forklift telemetry").json()
        self.assertFalse(second["ticket"]["created"])
        self.assertEqual(second["ticket"]["ticket_id"], ticket.ticket_id)
        self.assertEqual(Ticket.objects.count(), 1)
        stored = self.raw.messages.find_one({"ticket_id": ticket.ticket_id})
        self.assertEqual(stored["source"], "ai_fallback")

    def test_feedback_stored_in_mongodb(self):
        data = self.chat("How do I add a supplier?").json()
        resp = self.client.post(reverse("assistant:feedback"), json.dumps(
            {"message_id": data["message_id"], "rating": "up", "feedback_text": "Great"}), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        fb = self.raw.feedback.find_one({"message_id": data["message_id"]})
        self.assertEqual(fb["rating"], 1)
        self.assertEqual(fb["feedback_text"], "Great")
        self.assertEqual(fb["conversation_id"], data["conversation_id"])
        self.assertIn("timestamp", fb)

    def test_feedback_validation(self):
        data = self.chat("hello").json()
        bad_rating = self.client.post(reverse("assistant:feedback"), json.dumps(
            {"message_id": data["message_id"], "rating": "meh"}), content_type="application/json")
        self.assertEqual(bad_rating.status_code, 400)
        foreign = self.client.post(reverse("assistant:feedback"), json.dumps(
            {"message_id": "0" * 24, "rating": "up"}), content_type="application/json")
        self.assertEqual(foreign.status_code, 404)

    def test_history_endpoint(self):
        self.chat("How do I add a product?")
        self.chat("What does error 404 mean?")
        history = self.client.get(reverse("assistant:history")).json()
        self.assertEqual([m["source"] for m in history["messages"]], ["faq", "error_database"])

    def test_input_validation_and_rate_limit(self):
        self.assertEqual(self.chat("").status_code, 400)
        self.assertEqual(self.chat("x" * 1001).status_code, 400)
        bad = self.client.post(reverse("assistant:chat"), "not-json", content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        from django.core.cache import cache
        cache.clear()
        codes = [self.chat("hello").status_code for _ in range(32)]
        self.assertIn(429, codes)
        cache.clear()


@override_settings(MONGODB_URI="mongodb://127.0.0.1:1", MONGODB_TIMEOUT_MS=300)
class MongoFailureTests(TestCase):
    def setUp(self):
        mongo.reset_client()

    def tearDown(self):
        mongo.reset_client()

    def test_chat_still_works_when_mongodb_down(self):
        resp = self.client.post(reverse("assistant:chat"), json.dumps({"message": "How do I add a product?"}),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["source"], "faq")
        self.assertFalse(resp.json()["stored"])

    def test_feedback_reports_unavailable(self):
        self.client.post(reverse("assistant:chat"), json.dumps({"message": "hi"}), content_type="application/json")
        resp = self.client.post(reverse("assistant:feedback"), json.dumps({"message_id": "a" * 24, "rating": "up"}),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 503)

    def test_health_reports_degraded(self):
        data = self.client.get("/health/").json()
        self.assertEqual(data["status"], "degraded")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["mongodb"], "unavailable")


class TicketCrudTests(TestCase):
    def setUp(self):
        self.user = make_user("staff")
        self.other = make_user("other")
        self.admin = make_user("boss", "ADMIN")

    def test_user_ticket_lifecycle(self):
        self.client.login(username="staff", password=PASSWORD)
        resp = self.client.post(reverse("support:create"), {"subject": "Scanner not working", "description": "Details",
                                                             "priority": "HIGH"})
        ticket = Ticket.objects.get()
        self.assertRedirects(resp, ticket.get_absolute_url())
        self.assertRegex(ticket.ticket_id, r"^TKT-\d{8}-[0-9A-F]{6}$")
        self.assertContains(self.client.get(reverse("support:list")), ticket.ticket_id)
        self.client.post(reverse("support:update", args=[ticket.ticket_id]),
                         {"subject": "Scanner still not working", "description": "More", "priority": "LOW"})
        ticket.refresh_from_db()
        self.assertEqual(ticket.subject, "Scanner still not working")
        # users cannot change status / respond
        self.assertEqual(self.client.post(reverse("support:detail", args=[ticket.ticket_id]),
                                          {"status": "CLOSED"}).status_code, 403)
        self.client.post(reverse("support:delete", args=[ticket.ticket_id]))
        self.assertFalse(Ticket.objects.exists())

    def test_users_cannot_see_others_tickets(self):
        ticket = Ticket.objects.create(user=self.other, subject="Private issue", description="x")
        self.client.login(username="staff", password=PASSWORD)
        self.assertEqual(self.client.get(ticket.get_absolute_url()).status_code, 403)
        self.assertNotContains(self.client.get(reverse("support:list")), ticket.ticket_id)

    def test_resolved_ticket_cannot_be_edited_by_user(self):
        ticket = Ticket.objects.create(user=self.user, subject="Done issue", description="x", status=Ticket.RESOLVED)
        self.client.login(username="staff", password=PASSWORD)
        self.client.post(reverse("support:update", args=[ticket.ticket_id]),
                         {"subject": "Changed subject", "description": "y", "priority": "LOW"})
        ticket.refresh_from_db()
        self.assertEqual(ticket.subject, "Done issue")

    def test_admin_manages_all_tickets(self):
        ticket = Ticket.objects.create(user=self.user, subject="Need help with export", description="x")
        self.client.login(username="boss", password=PASSWORD)
        resp = self.client.get(reverse("support:list"), {"q": "export"})
        self.assertContains(resp, ticket.ticket_id)
        self.client.post(ticket.get_absolute_url(), {"status": "IN_PROGRESS", "priority": "URGENT",
                                                     "admin_response": "Looking into it"})
        ticket.refresh_from_db()
        self.assertEqual((ticket.status, ticket.priority, ticket.admin_response),
                         ("IN_PROGRESS", "URGENT", "Looking into it"))
        self.client.post(reverse("support:close", args=[ticket.ticket_id]))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "CLOSED")
        self.assertEqual(len(dict(Ticket.STATUS_CHOICES)), 5)
