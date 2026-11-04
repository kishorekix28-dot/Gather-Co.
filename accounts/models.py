from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .roles import ADMIN, CUSTOMER, STAFF


class Profile(models.Model):
    ROLE_CHOICES = [(ADMIN, "Admin"), (STAFF, "Staff"), (CUSTOMER, "Customer")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CUSTOMER)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={"role": ADMIN if instance.is_superuser else CUSTOMER})
