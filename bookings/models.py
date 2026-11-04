import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


def generate_booking_id():
    return f"BK-{timezone.now():%y%m%d}-{secrets.token_hex(3).upper()}"


class Booking(models.Model):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (PENDING, "Pending approval"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (CANCELLED, "Cancelled"),
    ]

    booking_id = models.CharField(max_length=20, unique=True, default=generate_booking_id, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    product = models.ForeignKey("inventory.Product", on_delete=models.CASCADE, related_name="bookings")
    quantity = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    note = models.CharField("customer note", max_length=255, blank=True)
    staff_note = models.CharField(max_length=255, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="reviewed_bookings")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "status", "start_date", "end_date"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="booking_end_after_start"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="booking_quantity_positive"),
        ]

    def __str__(self):
        return f"{self.booking_id} – {self.product} ×{self.quantity}"

    def get_absolute_url(self):
        return reverse("bookings:detail", args=[self.booking_id])

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def estimated_value(self):
        return self.product.price * self.quantity

    @property
    def can_cancel(self):
        return self.status in (self.PENDING, self.APPROVED) and self.end_date >= timezone.localdate()
