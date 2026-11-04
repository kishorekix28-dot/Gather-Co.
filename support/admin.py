from django.contrib import admin

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "subject", "user", "status", "priority", "source", "created_at")
    list_filter = ("status", "priority", "source")
    search_fields = ("ticket_id", "subject", "description")
    readonly_fields = ("ticket_id", "conversation_id", "question_hash", "created_at", "updated_at")
