from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name'], 'verbose_name_plural': 'categories'},
        ),
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('description', models.TextField(blank=True)),
                ('image_url', models.URLField(blank=True)),
                ('price_per_day', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    validators=[MinValueValidator(Decimal('0.01'))],
                )),
                ('security_deposit', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('0.00'),
                    max_digits=10,
                    validators=[MinValueValidator(Decimal('0.00'))],
                )),
                ('stock', models.PositiveIntegerField(validators=[MinValueValidator(1)])),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='products',
                    to='inventory.category',
                )),
                ('owner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='stock_items',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['name', 'id']},
        ),
        migrations.AddConstraint(
            model_name='inventoryitem',
            constraint=models.CheckConstraint(
                condition=models.Q(('stock__gte', 1)),
                name='product_stock_positive',
            ),
        ),
    ]
