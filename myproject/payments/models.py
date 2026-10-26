from django.db import models

from bookings.models import Booking


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        ADVANCE = 'advance', 'Advance'
        BALANCE = 'balance', 'Balance'
        REFUND = 'refund', 'Refund'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Successful'
        FAILED = 'failed', 'Failed'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reference_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_payment_type_display()} for booking {self.booking_id}'
