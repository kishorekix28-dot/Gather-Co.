import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from inventory.models import Category, InventoryItem

from .models import ErrorCode, FAQ, SupportTicket


class SupportPageTests(TestCase):
    def test_stylesheet_urls_are_absolute_on_home_and_support_pages(self):
        for path in ('/', '/faqs/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'href="/static/myapp/css/site.css"')
                self.assertContains(response, 'href="/static/myapp/css/support.css"')

    def test_seeded_faqs_and_error_codes_are_available(self):
        self.assertGreaterEqual(FAQ.objects.filter(is_active=True).count(), 10)
        self.assertGreaterEqual(ErrorCode.objects.filter(is_active=True).count(), 8)
        self.assertTrue(ErrorCode.objects.filter(code='GAT-001').exists())

    def test_support_pages_render_shared_chat_widget(self):
        for path in ('/faqs/', '/error-codes/', '/health/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Ask the assistant')
                self.assertContains(response, 'assistant-panel')

    @override_settings(DEBUG=False)
    def test_custom_not_found_page_offers_assistant(self):
        response = self.client.get('/definitely-not-a-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Ask the assistant', status_code=404)


class AssistantApiTests(TestCase):
    def test_assistant_answers_from_faq(self):
        with patch('myapp.support_views._save_chat_log', return_value=('log-1', None)):
            response = self.client.post(
                '/api/chat/',
                data=json.dumps({'message': 'How can I cancel a reservation?'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('cancel', response.json()['answer'].lower())
        self.assertIsNone(response.json()['ticket_id'])

    def test_assistant_understands_natural_reservation_question(self):
        with patch('myapp.support_views._save_chat_log', return_value=('log-reserve', None)):
            response = self.client.post(
                '/api/chat/',
                data=json.dumps({'message': 'how can i reserve in this website'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['ticket_id'])
        self.assertIn('choose an item', response.json()['answer'].lower())

    def test_assistant_lists_active_items_from_catalog(self):
        owner = User.objects.create_user(username='catalog-owner', password='safe-test-password')
        category = Category.objects.create(name='Chairs')
        InventoryItem.objects.create(
            owner=owner,
            category=category,
            name='Banquet Chairs',
            price_per_day=Decimal('35.00'),
            stock=20,
        )
        with patch('myapp.support_views._save_chat_log', return_value=('log-items', None)):
            response = self.client.post(
                '/api/chat/',
                data=json.dumps({'message': 'what all items are there'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['ticket_id'])
        self.assertIn('Banquet Chairs', response.json()['answer'])

    def test_assistant_suggests_questions_for_vague_website_doubt(self):
        with patch('myapp.support_views._save_chat_log', return_value=('log-clarify', None)):
            response = self.client.post(
                '/api/chat/',
                data=json.dumps({'message': 'i have a doubt'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['needs_clarification'])
        self.assertIsNone(response.json()['ticket_id'])
        self.assertIn('What items can I rent?', response.json()['suggestions'])

    def test_assistant_asks_which_booking_help_is_needed(self):
        with patch('myapp.support_views._save_chat_log', return_value=('log-booking', None)):
            response = self.client.post(
                '/api/chat/',
                data=json.dumps({'message': 'booking?'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['needs_clarification'])
        self.assertGreaterEqual(len(response.json()['suggestions']), 2)
        self.assertIsNone(response.json()['ticket_id'])

    def test_assistant_explains_an_error_code(self):
        with patch('myapp.support_views._save_chat_log', return_value=('log-2', None)):
            response = self.client.post(
                '/api/chat/',
                data=json.dumps({'message': 'What does error 503 mean?'}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Service temporarily unavailable', response.json()['answer'])

    def test_unknown_question_creates_sql_ticket(self):
        with patch('myapp.support_views._save_chat_log', return_value=('log-3', None)):
            response = self.client.post(
                '/api/chat/',
                data=json.dumps({
                    'message': 'How do I configure a quantum telescope?',
                    'email': 'guest@example.com',
                }),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 200)
        ticket = SupportTicket.objects.get(pk=response.json()['ticket_id'])
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)
        self.assertEqual(ticket.email, 'guest@example.com')

    @patch('myapp.support_views.save_feedback')
    def test_feedback_is_saved_to_mongodb(self, save_feedback):
        response = self.client.post(
            '/api/feedback/',
            data=json.dumps({'rating': 5, 'comment': 'Helpful', 'conversation_id': 'conversation-1'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertEqual(save_feedback.call_args.args[0]['rating'], 5)

    @patch('myapp.support_views.urllib.request.urlopen', side_effect=TimeoutError)
    def test_weather_api_returns_fallback_on_timeout(self, _urlopen):
        response = self.client.get('/api/weather/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['fallback'])
