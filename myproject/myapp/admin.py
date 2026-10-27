from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import (
    Booking,
    BookingItem,
    Category,
    ErrorCode,
    FAQ,
    Payment,
    Product,
    SupportTicket,
    UserProfile,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


class ProfileUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, ProfileUserAdmin)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Booking)
admin.site.register(BookingItem)
admin.site.register(Payment)
admin.site.register(FAQ)
admin.site.register(ErrorCode)
admin.site.register(SupportTicket)
