from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from bookings.models import Booking, BookingItem
from inventory.models import Category, InventoryItem
from myapp.management.demo_catalog import SAMPLE_ITEMS


class Command(BaseCommand):
    help = 'Create demo owner/customer accounts, sample inventory, and a booking.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        with transaction.atomic():
            owner, owner_created = user_model.objects.get_or_create(
                username='demo_owner',
                defaults={'email': 'owner@example.test'},
            )
            customer, customer_created = user_model.objects.get_or_create(
                username='demo_customer',
                defaults={'email': 'customer@example.test'},
            )
            if owner_created:
                owner.set_password('DemoOwner123!')
                owner.save(update_fields=['password'])
            if customer_created:
                customer.set_password('DemoCustomer123!')
                customer.save(update_fields=['password'])

            owner_profile, _ = UserProfile.objects.get_or_create(
                user=owner,
                defaults={'role': UserProfile.Role.OWNER},
            )
            customer_profile, _ = UserProfile.objects.get_or_create(
                user=customer,
                defaults={'role': UserProfile.Role.CUSTOMER},
            )
            if owner_profile.role != UserProfile.Role.OWNER:
                raise ValueError('The existing demo_owner account is not an owner.')
            if customer_profile.role != UserProfile.Role.CUSTOMER:
                raise ValueError('The existing demo_customer account is not a customer.')

            created_items = 0
            sample_product = None
            for category_name, name, quantity, price in SAMPLE_ITEMS:
                category, _ = Category.objects.get_or_create(name=category_name)
                product, created = InventoryItem.objects.get_or_create(
                    owner=owner,
                    name=name,
                    defaults={
                        'category': category,
                        'stock': quantity,
                        'price_per_day': Decimal(price),
                        'description': f'{name} available for event rental.',
                        'security_deposit': Decimal(price) * 2,
                    },
                )
                created_items += int(created)
                if name == 'Plastic Chairs':
                    sample_product = product

            start_date = timezone.localdate() + timedelta(days=7)
            end_date = start_date + timedelta(days=1)
            booking, booking_created = Booking.objects.get_or_create(
                customer=customer,
                product=sample_product,
                event_name='Demo Wedding',
                start_date=start_date,
                defaults={
                    'owner': owner,
                    'event_type': 'Wedding',
                    'event_location': 'Chennai',
                    'end_date': end_date,
                    'quantity': 100,
                    'price_per_day': sample_product.price_per_day,
                    'advance_percent': 20,
                    'status': Booking.Status.PENDING,
                },
            )
            if booking_created:
                BookingItem.objects.create(
                    booking=booking,
                    product=sample_product,
                    quantity=booking.quantity,
                    price_per_day=booking.price_per_day,
                    number_of_days=booking.duration_days,
                    subtotal=booking.total_amount,
                )

        self.stdout.write(self.style.SUCCESS(
            f'Demo data ready: {created_items} new inventory items; '
            f'{"created" if booking_created else "kept existing"} sample booking.'
        ))
        self.stdout.write('Owner login: demo_owner / DemoOwner123!')
        self.stdout.write('Customer login: demo_customer / DemoCustomer123!')
        self.stdout.write(self.style.WARNING(
            'These are development-only demo passwords. Change or remove the accounts before deployment.'
        ))
