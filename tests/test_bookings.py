from datetime import timedelta

from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings import services
from bookings.models import Booking
from core.templatetags.money import format_inr

from .helpers import PASSWORD, make_product, make_user


def d(days):
    return timezone.localdate() + timedelta(days=days)


class RupeeFormattingTests(TestCase):
    def test_indian_grouping(self):
        self.assertEqual(format_inr(1234567.891), "₹12,34,567.89")
        self.assertEqual(format_inr(999), "₹999.00")
        self.assertEqual(format_inr(100000, 0), "₹1,00,000")
        self.assertEqual(format_inr(0), "₹0.00")
        html = Template("{% load money %}{{ v|inr:0 }}").render(Context({"v": 2500000}))
        self.assertEqual(html, "₹25,00,000")

    def test_pages_show_rupees(self):
        make_user("boss", "ADMIN")
        self.client.login(username="boss", password=PASSWORD)
        p = make_product(sku="INR-1", qty=3)
        for url in ("/dashboard/", "/products/", p.get_absolute_url(), "/reports/"):
            resp = self.client.get(url)
            self.assertContains(resp, "₹", msg_prefix=url)
            self.assertNotContains(resp, "$10.00", msg_prefix=url)


class AvailabilityServiceTests(TestCase):
    def setUp(self):
        self.customer = make_user("cust", "CUSTOMER")
        self.staff = make_user("staffer", "STAFF")
        self.product = make_product(sku="TENT-1", qty=5)

    def book(self, qty, start, end, approve=False):
        b = services.create_booking(customer=self.customer, product=self.product, quantity=qty, start=start, end=end)
        if approve:
            services.approve_booking(b, self.staff)
        return b

    def test_pending_does_not_block_but_approved_does(self):
        self.book(3, d(2), d(4))
        self.assertEqual(services.available_quantity(self.product, d(2), d(4)), 5)
        self.book(3, d(3), d(6), approve=True)
        self.assertEqual(services.available_quantity(self.product, d(2), d(2)), 5)
        self.assertEqual(services.available_quantity(self.product, d(2), d(4)), 2)
        self.assertEqual(services.available_quantity(self.product, d(7), d(9)), 5)

    def test_cannot_request_more_than_free(self):
        self.book(4, d(1), d(3), approve=True)
        with self.assertRaisesMessage(ValidationError, "Only 1 unit"):
            self.book(2, d(3), d(5))

    def test_approval_prevents_double_booking(self):
        first = self.book(4, d(5), d(6))
        second = self.book(4, d(6), d(8))   # both requested while nothing is approved
        services.approve_booking(first, self.staff)
        with self.assertRaisesMessage(ValidationError, "Cannot approve"):
            services.approve_booking(second, self.staff)
        second.refresh_from_db()
        self.assertEqual(second.status, Booking.PENDING)

    def test_date_validation(self):
        with self.assertRaises(ValidationError):
            self.book(1, d(-1), d(2))
        with self.assertRaises(ValidationError):
            self.book(1, d(5), d(2))
        with self.assertRaises(ValidationError):
            self.book(1, d(1), d(80))

    def test_cancel_frees_units(self):
        b = self.book(5, d(1), d(2), approve=True)
        self.assertEqual(services.available_quantity(self.product, d(1), d(2)), 0)
        services.cancel_booking(b, self.customer)
        self.assertEqual(services.available_quantity(self.product, d(1), d(2)), 5)

    def test_month_calendar_marks_blocked_days(self):
        b = self.book(2, d(1), d(2), approve=True)
        target = d(1)
        cal = services.month_calendar(target.year, target.month)
        cells = {c["date"]: c for week in cal["weeks"] for c in week}
        self.assertIn(b, cells[target]["approved"])
        self.assertEqual(cells[target]["units"], 2)


class BookingViewTests(TestCase):
    def setUp(self):
        self.customer = make_user("cust", "CUSTOMER")
        self.other = make_user("other", "CUSTOMER")
        self.staff = make_user("staffer", "STAFF")
        self.product = make_product(sku="CHAIR-1", qty=10, name="Folding Chair")

    def test_customer_dashboard_shows_availability(self):
        services.approve_booking(services.create_booking(customer=self.other, product=self.product, quantity=4,
                                                         start=d(1), end=d(3)), self.staff)
        self.client.login(username="cust", password=PASSWORD)
        resp = self.client.get(reverse("bookings:customer_dashboard"), {"start": d(2).isoformat(),
                                                                        "end": d(2).isoformat()})
        self.assertEqual(resp.status_code, 200)
        row = [r for r in resp.context["catalogue"] if r["product"] == self.product][0]
        self.assertEqual(row["available"], 6)
        self.assertNotContains(resp, "Purchase cost")

    def test_customer_creates_booking_and_staff_approves(self):
        self.client.login(username="cust", password=PASSWORD)
        resp = self.client.post(reverse("bookings:create"), {
            "product": self.product.pk, "start_date": d(3).isoformat(), "end_date": d(4).isoformat(),
            "quantity": 6, "note": "Wedding"})
        booking = Booking.objects.get()
        self.assertRedirects(resp, booking.get_absolute_url())
        self.assertEqual(booking.status, Booking.PENDING)
        self.assertEqual(self.client.post(reverse("bookings:review", args=[booking.booking_id, "approve"])).status_code,
                         403)
        self.client.login(username="staffer", password=PASSWORD)
        self.assertContains(self.client.get(reverse("bookings:manage")), booking.booking_id)
        self.client.post(reverse("bookings:review", args=[booking.booking_id, "approve"]), {"note": "Gate 2"})
        booking.refresh_from_db()
        self.assertEqual((booking.status, booking.staff_note, booking.reviewed_by), (Booking.APPROVED, "Gate 2", self.staff))
        cal = self.client.get(reverse("bookings:calendar"), {"month": d(3).strftime("%Y-%m")})
        self.assertContains(cal, "Folding Chair ×6")
        dash = self.client.get(reverse("inventory:dashboard"))
        self.assertContains(dash, 'data-testid="booking-calendar"')

    def test_overbooking_rejected_in_form(self):
        self.client.login(username="cust", password=PASSWORD)
        resp = self.client.post(reverse("bookings:create"), {
            "product": self.product.pk, "start_date": d(1).isoformat(), "end_date": d(1).isoformat(),
            "quantity": 11})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Only 10 unit")
        self.assertFalse(Booking.objects.exists())

    def test_reject_flow(self):
        b = services.create_booking(customer=self.customer, product=self.product, quantity=1, start=d(1), end=d(1))
        self.client.login(username="staffer", password=PASSWORD)
        self.client.post(reverse("bookings:review", args=[b.booking_id, "reject"]), {"note": "Not available"})
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.REJECTED)

    def test_privacy_and_role_access(self):
        b = services.create_booking(customer=self.other, product=self.product, quantity=1, start=d(1), end=d(1))
        self.client.login(username="cust", password=PASSWORD)
        self.assertEqual(self.client.get(b.get_absolute_url()).status_code, 403)
        for url in ("/products/", "/transactions/", "/categories/", "/bookings/manage/", "/bookings/calendar/",
                    "/api/products/"):
            self.assertIn(self.client.get(url).status_code, (403,), url)
        self.assertRedirects(self.client.get("/dashboard/"), reverse("bookings:customer_dashboard"))
        self.client.login(username="staffer", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("bookings:customer_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(b.get_absolute_url()).status_code, 200)

    def test_customer_cancels(self):
        b = services.create_booking(customer=self.customer, product=self.product, quantity=1, start=d(1), end=d(2))
        self.client.login(username="cust", password=PASSWORD)
        self.client.post(reverse("bookings:cancel", args=[b.booking_id]))
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.CANCELLED)

    def test_widget_on_booking_pages(self):
        self.client.login(username="cust", password=PASSWORD)
        for url in ("/bookings/", "/bookings/new/", "/bookings/mine/"):
            self.assertContains(self.client.get(url), 'id="assistant-widget"', msg_prefix=url)
