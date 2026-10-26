import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_name', models.CharField(default='Event', max_length=120)),
                ('event_type', models.CharField(blank=True, max_length=80)),
                ('event_location', models.CharField(blank=True, max_length=200)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('quantity', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('price_per_day', models.DecimalField(decimal_places=2, max_digits=10)),
                ('advance_percent', models.PositiveSmallIntegerField(default=20)),
                ('hold_expires_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Awaiting owner approval'),
                        ('payment_pending', 'Advance payment required'),
                        ('confirmed', 'Confirmed'),
                        ('rejected', 'Declined'),
                        ('cancelled', 'Cancelled'),
                        ('payment_failed', 'Payment failed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('owner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='received_bookings',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='bookings',
                    to='inventory.inventoryitem',
                )),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddConstraint(
            model_name='booking',
            constraint=models.CheckConstraint(
                condition=models.Q(('end_date__gte', models.F('start_date'))),
                name='booking_end_on_or_after_start',
            ),
        ),
        migrations.AddConstraint(
            model_name='booking',
            constraint=models.CheckConstraint(
                condition=models.Q(('quantity__gte', 1)),
                name='booking_quantity_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='booking',
            constraint=models.CheckConstraint(
                condition=models.Q(('advance_percent__lte', 100)),
                name='booking_advance_percent_lte_100',
            ),
        ),
        migrations.CreateModel(
            name='BookingItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('price_per_day', models.DecimalField(decimal_places=2, max_digits=10)),
                ('number_of_days', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=12)),
                ('booking', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='bookings.booking',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='booking_items',
                    to='inventory.inventoryitem',
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name='bookingitem',
            constraint=models.CheckConstraint(
                condition=models.Q(('quantity__gte', 1)),
                name='booking_item_quantity_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='bookingitem',
            constraint=models.CheckConstraint(
                condition=models.Q(('number_of_days__gte', 1)),
                name='booking_item_days_positive',
            ),
        ),
    ]
