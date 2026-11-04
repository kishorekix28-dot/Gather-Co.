"""Reservation availability rules.

A product's on-hand quantity can be reserved per day. Only APPROVED bookings
block units; a PENDING request does not hold stock until staff approve it.
Approval re-checks availability inside a transaction with the product row
locked, so two approvals can never over-book the same day.
"""
import calendar
from collections import defaultdict
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.models import Product
from inventory.services import log_activity

from .models import Booking

MAX_BOOKING_DAYS = 60
MAX_ADVANCE_DAYS = 365


def daterange(start, end):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def reserved_by_day(product, start, end, exclude_pk=None):
    """{date: units reserved by approved bookings} for the product within [start, end]."""
    qs = Booking.objects.filter(product=product, status=Booking.APPROVED, start_date__lte=end, end_date__gte=start)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    reserved = defaultdict(int)
    for b in qs.only("quantity", "start_date", "end_date"):
        for day in daterange(max(b.start_date, start), min(b.end_date, end)):
            reserved[day] += b.quantity
    return reserved


def available_quantity(product, start, end, exclude_pk=None):
    """Units free on every day of the range (the minimum across days)."""
    reserved = reserved_by_day(product, start, end, exclude_pk)
    peak = max(reserved.values(), default=0)
    return max(product.quantity - peak, 0)


def availability_for_products(products, start, end):
    """Bulk version for catalogue pages: {product_id: free units}."""
    products = list(products)
    ids = [p.pk for p in products]
    reserved = defaultdict(lambda: defaultdict(int))
    qs = Booking.objects.filter(product_id__in=ids, status=Booking.APPROVED, start_date__lte=end, end_date__gte=start)
    for b in qs.only("product_id", "quantity", "start_date", "end_date"):
        for day in daterange(max(b.start_date, start), min(b.end_date, end)):
            reserved[b.product_id][day] += b.quantity
    return {p.pk: max(p.quantity - max(reserved[p.pk].values(), default=0), 0) for p in products}


def validate_dates(start, end):
    today = timezone.localdate()
    if start < today:
        raise ValidationError("The start date cannot be in the past.")
    if end < start:
        raise ValidationError("The end date must be on or after the start date.")
    if (end - start).days + 1 > MAX_BOOKING_DAYS:
        raise ValidationError(f"Bookings can cover at most {MAX_BOOKING_DAYS} days.")
    if (start - today).days > MAX_ADVANCE_DAYS:
        raise ValidationError("Bookings can be made up to one year in advance.")


def create_booking(*, customer, product, quantity, start, end, note=""):
    validate_dates(start, end)
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")
    free = available_quantity(product, start, end)
    if quantity > free:
        raise ValidationError(f"Only {free} unit(s) of {product.name} are available for those dates.")
    booking = Booking.objects.create(customer=customer, product=product, quantity=quantity,
                                     start_date=start, end_date=end, note=note)
    log_activity(customer, "Booking requested", f"{booking.booking_id}: {product.sku} ×{quantity} {start}→{end}")
    return booking


@transaction.atomic
def approve_booking(booking, staff, note=""):
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != Booking.PENDING:
        raise ValidationError(f"Only pending bookings can be approved (this one is {booking.get_status_display()}).")
    product = Product.objects.select_for_update().get(pk=booking.product_id)
    reserved = reserved_by_day(product, booking.start_date, booking.end_date, exclude_pk=booking.pk)
    for day in daterange(booking.start_date, booking.end_date):
        free = product.quantity - reserved.get(day, 0)
        if booking.quantity > free:
            raise ValidationError(
                f"Cannot approve: only {max(free, 0)} unit(s) of {product.name} are free on {day:%d %b %Y}.")
    booking.status = Booking.APPROVED
    booking.staff_note = note
    booking.reviewed_by = staff
    booking.reviewed_at = timezone.now()
    booking.save()
    log_activity(staff, "Booking approved", f"{booking.booking_id}: {product.sku} ×{booking.quantity} blocked "
                                            f"{booking.start_date}→{booking.end_date}")
    return booking


@transaction.atomic
def reject_booking(booking, staff, note=""):
    booking = Booking.objects.select_for_update().get(pk=booking.pk)
    if booking.status != Booking.PENDING:
        raise ValidationError("Only pending bookings can be rejected.")
    booking.status = Booking.REJECTED
    booking.staff_note = note
    booking.reviewed_by = staff
    booking.reviewed_at = timezone.now()
    booking.save()
    log_activity(staff, "Booking rejected", booking.booking_id)
    return booking


def cancel_booking(booking, user):
    if not booking.can_cancel:
        raise ValidationError("This booking can no longer be cancelled.")
    booking.status = Booking.CANCELLED
    booking.save(update_fields=["status", "updated_at"])
    log_activity(user, "Booking cancelled", booking.booking_id)
    return booking


def month_calendar(year, month, include_pending=True):
    """Weeks of day cells for a month grid with the bookings active on each day."""
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    statuses = [Booking.APPROVED] + ([Booking.PENDING] if include_pending else [])
    bookings = list(Booking.objects.filter(status__in=statuses, start_date__lte=last, end_date__gte=first)
                    .select_related("product", "customer").order_by("start_date", "product__name"))
    today = timezone.localdate()
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
        cells = []
        for day in week:
            items = [b for b in bookings if b.start_date <= day <= b.end_date]
            cells.append({
                "date": day,
                "in_month": day.month == month,
                "is_today": day == today,
                "approved": [b for b in items if b.status == Booking.APPROVED],
                "pending": [b for b in items if b.status == Booking.PENDING],
                "units": sum(b.quantity for b in items if b.status == Booking.APPROVED),
            })
        weeks.append(cells)
    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = last + timedelta(days=1)
    return {"weeks": weeks, "first": first, "prev": prev_month, "next": next_month,
            "approved_count": sum(1 for b in bookings if b.status == Booking.APPROVED),
            "pending_count": sum(1 for b in bookings if b.status == Booking.PENDING)}
