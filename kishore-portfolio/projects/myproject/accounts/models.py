from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        CUSTOMER = 'customer', 'Customer'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=10, choices=Role.choices)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'
