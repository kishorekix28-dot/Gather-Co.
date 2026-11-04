from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_id", "customer", "product", "quantity", "start_date", "end_date", "status")
    list_filter = ("status",)
    search_fields = ("booking_id", "customer__username", "product__sku", "product__name")
    readonly_fields = ("booking_id", "created_at", "updated_at", "reviewed_at")
