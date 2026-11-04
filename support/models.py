import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


def generate_ticket_id():
    return f"TKT-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


class Ticket(models.Model):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    STATUS_CHOICES = [
        (OPEN, "Open"), (IN_PROGRESS, "In Progress"), (WAITING, "Waiting for Response"),
        (RESOLVED, "Resolved"), (CLOSED, "Closed"),
    ]
    LOW, MEDIUM, HIGH, URGENT = "LOW", "MEDIUM", "HIGH", "URGENT"
    PRIORITY_CHOICES = [(LOW, "Low"), (MEDIUM, "Medium"), (HIGH, "High"), (URGENT, "Urgent")]
    SOURCE_CHOICES = [("MANUAL", "Manual"), ("ASSISTANT", "AI Assistant")]

    ticket_id = models.CharField(max_length=24, unique=True, default=generate_ticket_id, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="tickets")
    subject = models.CharField(max_length=160)
    description = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=OPEN, db_index=True)
    priority = models.CharField(max_length=8, choices=PRIORITY_CHOICES, default=MEDIUM)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="MANUAL")
    admin_response = models.TextField(blank=True)
    conversation_id = models.CharField(max_length=64, blank=True, db_index=True)
    question_hash = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation_id", "question_hash"],
                condition=~models.Q(conversation_id="") & ~models.Q(question_hash=""),
                name="unique_assistant_ticket_per_conversation",
            )
        ]

    def __str__(self):
        return f"{self.ticket_id}: {self.subject}"

    def get_absolute_url(self):
        return reverse("support:detail", args=[self.ticket_id])

    @property
    def user_can_edit(self):
        return self.status in (self.OPEN, self.WAITING)

    @property
    def user_can_cancel(self):
        return self.status == self.OPEN
