from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Booking, Payment, Product, UserProfile


class StockReservationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='Test-password-123!',
        )
        UserProfile.objects.create(user=self.owner, role=UserProfile.Role.OWNER)
        self.customer = User.objects.create_user(
            username='customer',
            password='Test-password-123!',
        )
        UserProfile.objects.create(user=self.customer, role=UserProfile.Role.CUSTOMER)
        self.product = Product.objects.create(
            owner=self.owner,
            name='Camera',
            description='A test camera',
            price_per_day=Decimal('10.00'),
            stock=2,
        )
        self.start = timezone.localdate() + timedelta(days=1)
        self.end = self.start + timedelta(days=1)

    def create_booking(self, customer, start, end, quantity):
        return Booking.objects.create(
            customer=customer,
            owner=self.owner,
            product=self.product,
            start_date=start,
            end_date=end,
            quantity=quantity,
            price_per_day=self.product.price_per_day,
        )

    def test_customer_signup_creates_profile_and_logs_in(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'new-customer',
                'email': 'customer@example.com',
                'role': UserProfile.Role.CUSTOMER,
                'password1': 'Another-safe-pass-123!',
                'password2': 'Another-safe-pass-123!',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(
            UserProfile.objects.get(user__username='new-customer').role,
            UserProfile.Role.CUSTOMER,
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_redirects_to_local_next_page(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': self.customer.username,
                'password': 'Test-password-123!',
                'next': reverse('my-bookings'),
            },
        )

        self.assertRedirects(response, reverse('my-bookings'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_owner_can_add_stock_but_customer_cannot(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('add-product'),
            {
                'name': 'Tripod',
                'description': 'A sturdy tripod',
                'price_per_day': '4.50',
                'security_deposit': '0.00',
                'stock': 3,
            },
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(Product.objects.filter(owner=self.owner, name='Tripod').exists())

        self.client.force_login(self.customer)
        response = self.client.get(reverse('add-product'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_owner_can_update_inventory(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('edit-product', args=[self.product.pk]),
            {
                'name': 'Updated Camera',
                'description': 'Updated description',
                'image_url': '',
                'price_per_day': '12.50',
                'security_deposit': '25.00',
                'stock': 4,
                'category': '',
                'new_category': '',
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Camera')
        self.assertEqual(self.product.stock, 4)

    def test_booking_records_advance_due_without_claiming_payment(self):
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse('book-product', args=[self.product.pk]),
            {
                'event_name': 'Birthday Party',
                'event_type': 'Birthday',
                'event_location': 'Chennai',
                'start_date': self.start.isoformat(),
                'end_date': self.end.isoformat(),
                'quantity': 2,
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        booking = Booking.objects.get(customer=self.customer)
        self.assertEqual(booking.total_amount, Decimal('40.00'))
        self.assertEqual(booking.advance_due, Decimal('8.00'))
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_overlapping_reservations_cannot_exceed_stock(self):
        self.create_booking(self.customer, self.start, self.end, 2)
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('book-product', args=[self.product.pk]),
            {
                'event_name': 'Wedding',
                'start_date': self.start.isoformat(),
                'end_date': self.end.isoformat(),
                'quantity': 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Only 0 item(s) are available')
        self.assertEqual(Booking.objects.count(), 1)

    def test_stock_availability_uses_peak_overlap_not_sum_of_dates(self):
        next_day = self.start + timedelta(days=1)
        self.create_booking(self.customer, self.start, self.start, 1)
        other_customer = User.objects.create_user(
            username='other',
            password='Test-password-123!',
        )
        UserProfile.objects.create(
            user=other_customer,
            role=UserProfile.Role.CUSTOMER,
        )
        self.create_booking(other_customer, next_day, next_day, 1)
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse('book-product', args=[self.product.pk]),
            {
                'event_name': 'Community Event',
                'start_date': self.start.isoformat(),
                'end_date': next_day.isoformat(),
                'quantity': 1,
            },
        )

        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(Booking.objects.count(), 3)

    def test_owner_can_confirm_only_their_pending_reservations(self):
        booking = self.create_booking(self.customer, self.start, self.end, 1)
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse('reservation-action', args=[booking.pk]),
            {'action': 'confirm'},
        )

        self.assertRedirects(response, reverse('dashboard'))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PAYMENT_PENDING)
        self.assertTrue(booking.hold_expires_at)

    def test_successful_demo_advance_payment_confirms_booking(self):
        booking = self.create_booking(self.customer, self.start, self.end, 1)
        booking.status = Booking.Status.PAYMENT_PENDING
        booking.hold_expires_at = timezone.now() + timedelta(minutes=15)
        booking.save(update_fields=['status', 'hold_expires_at'])
        self.client.force_login(self.customer)

        response = self.client.post(reverse('mock-payment', args=[booking.pk]))

        self.assertRedirects(response, reverse('receipt', args=[booking.pk]))
        booking.refresh_from_db()
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertEqual(payment.amount, booking.advance_due)
        self.assertTrue(payment.reference_id.startswith('DEMO-'))

    def test_dashboard_and_booking_pages_render_for_signed_in_users(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('book-product', args=[self.product.pk])).status_code,
            200,
        )
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('owner-calendar')).status_code, 200)

    def test_owner_can_deactivate_stock(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('deactivate-product', args=[self.product.pk])
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)

    def test_demo_data_command_is_repeatable(self):
        call_command('load_demo_data', stdout=StringIO())
        call_command('load_demo_data', stdout=StringIO())

        self.assertEqual(
            Product.objects.filter(owner__username='demo_owner').count(),
            30,
        )
        demo_booking = Booking.objects.get(event_name='Demo Wedding')
        self.assertEqual(demo_booking.status, Booking.Status.PENDING)
        self.assertEqual(demo_booking.customer.username, 'demo_customer')

    def test_seeded_demo_booking_works_through_approval_payment_and_receipt(self):
        call_command('load_demo_data', stdout=StringIO())
        owner = User.objects.get(username='demo_owner')
        customer = User.objects.get(username='demo_customer')
        booking = Booking.objects.get(event_name='Demo Wedding')

        self.client.force_login(owner)
        response = self.client.post(
            reverse('reservation-action', args=[booking.pk]),
            {'action': 'confirm'},
        )
        self.assertRedirects(response, reverse('dashboard'))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PAYMENT_PENDING)

        self.client.force_login(customer)
        response = self.client.get(reverse('payment-checkout', args=[booking.pk]))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('mock-payment', args=[booking.pk]))
        self.assertRedirects(response, reverse('receipt', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(
            self.client.get(reverse('receipt', args=[booking.pk])).status_code,
            200,
        )
