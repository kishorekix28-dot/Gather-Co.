from accounts.models import UserProfile
from bookings.models import Booking, BookingItem
from inventory.models import Category, InventoryItem as Product
from payments.models import Payment
from django.conf import settings
from django.db import models


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    keywords = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('question',)
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    code = models.CharField(max_length=12, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField()
    resolution = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('code',)

    def __str__(self):
        return f'{self.code}: {self.title}'


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In progress'
        RESOLVED = 'resolved', 'Resolved'

    subject = models.CharField(max_length=120)
    message = models.TextField()
    email = models.EmailField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='support_tickets',
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'Ticket #{self.pk}: {self.subject}'


__all__ = [
    'Booking',
    'BookingItem',
    'Category',
    'ErrorCode',
    'FAQ',
    'Payment',
    'Product',
    'SupportTicket',
    'UserProfile',
]
