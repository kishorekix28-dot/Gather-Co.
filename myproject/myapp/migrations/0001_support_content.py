from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


FAQS = [
    (
        'How do I create an account?',
        'Choose Get started, enter your details, and select whether you are renting items or listing inventory.',
        'register signup account login sign in signin log in',
    ),
    (
        'How do I find rental items?',
        'Browse the Explore rentals page. Search by item name or filter the collection by category.',
        'browse search inventory products',
    ),
    (
        'How do I make a reservation?',
        'Open an item in the collection, choose your dates and quantity, then submit the booking request.',
        'book booking reserve dates',
    ),
    (
        'Can I cancel a reservation?',
        'Open your bookings from the dashboard and use the cancel action while the reservation is eligible for cancellation.',
        'cancel cancellation reservation',
    ),
    (
        'How do payments work?',
        'Payments in this demo are simulated. Use the payment action on an eligible reservation; no real charge is made.',
        'pay payment checkout charge',
    ),
    (
        'How can an owner list inventory?',
        'Create an account and choose the owner role. From your dashboard, add an item with its name, category, price, and availability.',
        'owner list add item product inventory',
    ),
    (
        'Where can I see my reservations?',
        'Sign in and open your dashboard. Customers can find their reservations under My bookings.',
        'status track dashboard bookings',
    ),
    (
        'How do I update an inventory listing?',
        'Sign in as the inventory owner, open your owner dashboard, and choose edit next to the listing you want to update.',
        'edit update listing owner product',
    ),
    (
        'What should I do if an item is unavailable?',
        'Try another date or browse similar items in the same category. Availability is checked when you submit a booking.',
        'availability available date out stock',
    ),
    (
        'How do I contact support?',
        'Ask the assistant using the chat button. If it cannot find an answer, it creates a support ticket for the team.',
        'help support contact ticket human',
    ),
    (
        'Are demo payments real?',
        'No. The payment flow is for demonstration only and does not process a real payment or store card details.',
        'demo payment real card safe',
    ),
]

ERRORS = [
    ('400', 'Bad request', 'The request could not be understood because some submitted information is invalid.', 'Check the form fields and correct any highlighted values before trying again.'),
    ('401', 'Sign-in required', 'This action requires an authenticated account.', 'Sign in and retry. If you already signed in, log out and back in.'),
    ('403', 'Access denied', 'Your account does not have permission to access this resource.', 'Check that you are using the correct account role, or contact support if you believe this is a mistake.'),
    ('404', 'Page not found', 'The requested page or item does not exist or is no longer available.', 'Check the address or return to the home page and try again.'),
    ('429', 'Too many requests', 'Requests are temporarily being rate limited.', 'Wait a short while before retrying.'),
    ('500', 'Something went wrong', 'The server encountered an unexpected error while processing the request.', 'Try again shortly. If the problem continues, ask the assistant to create a support ticket.'),
    ('503', 'Service temporarily unavailable', 'A required service is temporarily unavailable or undergoing maintenance.', 'Wait a moment and retry. Your submitted information may not have been saved.'),
    ('GAT-001', 'Reservation conflict', 'The requested inventory is not available for every selected date or quantity.', 'Choose different dates or a smaller quantity, then submit the reservation again.'),
]


def seed_support_content(apps, schema_editor):
    FAQ = apps.get_model('myapp', 'FAQ')
    ErrorCode = apps.get_model('myapp', 'ErrorCode')
    FAQ.objects.using(schema_editor.connection.alias).bulk_create(
        [FAQ(question=q, answer=a, keywords=k) for q, a, k in FAQS]
    )
    ErrorCode.objects.using(schema_editor.connection.alias).bulk_create(
        [
            ErrorCode(code=code, title=title, description=description, resolution=resolution)
            for code, title, description, resolution in ERRORS
        ]
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ErrorCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=12, unique=True)),
                ('title', models.CharField(max_length=120)),
                ('description', models.TextField()),
                ('resolution', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ('code',)},
        ),
        migrations.CreateModel(
            name='FAQ',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255)),
                ('answer', models.TextField()),
                ('keywords', models.CharField(blank=True, max_length=255)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ('question',), 'verbose_name': 'FAQ', 'verbose_name_plural': 'FAQs'},
        ),
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=120)),
                ('message', models.TextField()),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('status', models.CharField(choices=[('open', 'Open'), ('in_progress', 'In progress'), ('resolved', 'Resolved')], default='open', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='support_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.RunPython(seed_support_content, migrations.RunPython.noop),
    ]
