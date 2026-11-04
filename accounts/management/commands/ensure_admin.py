"""Create or update an administrator from environment variables (used on deploy).

DJANGO_ADMIN_USERNAME, DJANGO_ADMIN_EMAIL, DJANGO_ADMIN_PASSWORD
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile
from accounts.roles import ADMIN


class Command(BaseCommand):
    help = "Ensure an administrator account exists (credentials from environment variables)."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_ADMIN_USERNAME")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD")
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "")
        if not username or not password:
            self.stdout.write("DJANGO_ADMIN_USERNAME/DJANGO_ADMIN_PASSWORD not set; skipping.")
            return
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        if created:
            user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        Profile.objects.update_or_create(user=user, defaults={"role": ADMIN})
        self.stdout.write(self.style.SUCCESS(f"Administrator '{username}' {'created' if created else 'verified'}."))
