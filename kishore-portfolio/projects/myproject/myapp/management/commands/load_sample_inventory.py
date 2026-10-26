from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import UserProfile
from inventory.models import Category, InventoryItem
from myapp.management.demo_catalog import SAMPLE_ITEMS


class Command(BaseCommand):
    help = 'Create ten sample event-rental inventory items for an owner.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--owner',
            help='Username of the owner who should own the sample inventory.',
        )

    def handle(self, *args, **options):
        users = get_user_model().objects
        username = options['owner']
        if username:
            try:
                owner = users.get(username=username)
            except get_user_model().DoesNotExist as exc:
                raise CommandError(f'No user named "{username}" exists.') from exc
            if not UserProfile.objects.filter(
                user=owner,
                role=UserProfile.Role.OWNER,
            ).exists():
                raise CommandError(f'"{username}" does not have the owner role.')
        else:
            owner_profile = UserProfile.objects.filter(
                role=UserProfile.Role.OWNER
            ).select_related('user').first()
            if owner_profile is None:
                raise CommandError(
                    'Create an owner account in the app first, or pass --owner USERNAME.'
                )
            owner = owner_profile.user

        created = 0
        for category_name, name, quantity, price in SAMPLE_ITEMS:
            category, _ = Category.objects.get_or_create(name=category_name)
            _, was_created = InventoryItem.objects.get_or_create(
                owner=owner,
                name=name,
                defaults={
                    'category': category,
                    'stock': quantity,
                    'price_per_day': Decimal(price),
                    'description': f'{name} available for event rental.',
                },
            )
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(f'Loaded {created} new sample item(s) for {owner.username}.')
        )
