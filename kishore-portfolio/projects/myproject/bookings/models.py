from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from inventory.models import InventoryItem


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Awaiting owner approval'
        PAYMENT_PENDING = 'payment_pending', 'Advance payment required'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED = 'rejected', 'Declined'
        CANCELLED = 'cancelled', 'Cancelled'
        PAYMENT_FAILED = 'payment_failed', 'Payment failed'

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_bookings',
    )
    product = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    event_name = models.CharField(max_length=120, default='Event')
    event_type = models.CharField(max_length=80, blank=True)
    event_location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    advance_percent = models.PositiveSmallIntegerField(default=20)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name='booking_end_on_or_after_start',
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='booking_quantity_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(advance_percent__lte=100),
                name='booking_advance_percent_lte_100',
            ),
        ]

    def __str__(self):
        return f'{self.product.name} for {self.customer.username}'

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def total_amount(self):
        return self.price_per_day * self.quantity * self.duration_days

    @property
    def advance_due(self):
        amount = self.total_amount * Decimal(self.advance_percent) / Decimal(100)
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def remaining_amount(self):
        return self.total_amount - self.advance_due

    @property
    def payment_status(self):
        if self.status == self.Status.CONFIRMED:
            return 'Advance paid (demo)'
        if self.status == self.Status.PAYMENT_FAILED:
            return 'Payment failed'
        return 'Advance pending'


class BookingItem(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='booking_items',
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_days = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='booking_item_quantity_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(number_of_days__gte=1),
                name='booking_item_days_positive',
            ),
        ]

    def __str__(self):
        return f'{self.quantity} × {self.product.name}'
