import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('payment_type', models.CharField(
                    choices=[('advance', 'Advance'), ('balance', 'Balance'), ('refund', 'Refund')],
                    max_length=10,
                )),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('success', 'Successful'), ('failed', 'Failed')],
                    default='pending',
                    max_length=10,
                )),
                ('reference_id', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('booking', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to='bookings.booking',
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
