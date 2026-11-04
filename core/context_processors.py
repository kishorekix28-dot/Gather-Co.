from accounts.roles import get_role


def app_context(request):
    """Global template context. Must be defensive: it also renders error pages."""
    ctx = {"APP_NAME": "StockPilot", "APP_TAGLINE": "Inventory Management System", "user_role": None,
           "is_admin_user": False, "stock_alerts": [], "stock_alert_count": 0,
           "pending_booking_count": 0}
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return ctx
    try:
        from inventory.models import Product

        role = get_role(user)
        ctx.update({"user_role": role, "is_admin_user": role == "ADMIN"})
        if role == "CUSTOMER":
            return ctx
        from bookings.models import Booking

        ctx["pending_booking_count"] = Booking.objects.filter(status=Booking.PENDING).count()
        alerts = list(Product.objects.needs_attention().order_by("quantity")[:6])
        ctx.update({
            "user_role": role,
            "is_admin_user": role == "ADMIN",
            "stock_alerts": alerts,
            "stock_alert_count": Product.objects.needs_attention().count(),
        })
    except Exception:
        pass
    return ctx
