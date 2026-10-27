from django.db import migrations


FAQ_UPDATES = {
    'How do I find rental items?': (
        'Browse the Explore rentals section on the home page to see currently listed items. '
        'Use search or the category filter to narrow the list. Open an item to see its price, '
        'description, and availability.',
        'browse search inventory products item items product equipment rental rentals '
        'available catalog catalogue what show all chairs tables lights sound stage tents categories',
    ),
    'How do I make a reservation?': (
        'Browse Explore rentals, choose an item, and select Book. Enter your event start and '
        'end dates and quantity, then submit the booking request. Sign in first if asked. '
        'You can check the request in your dashboard under My bookings.',
        'book booking reserve reservation reservations dates date quantity rent rental checkout '
        'how can i make place request order',
    ),
    'Can I cancel a reservation?': (
        'Sign in, open your dashboard, and find the reservation in My bookings. Use its cancel '
        'action if cancellation is available for that booking.',
        'cancel cancellation canceled cancelled reservation booking bookings',
    ),
    'How do payments work?': (
        'Open an eligible reservation and choose its payment option. Payments on this demo site '
        'are simulated: no real charge is made and no card details are stored.',
        'pay payment payments checkout charge charges price prices cost costs demo card',
    ),
    'How can an owner list inventory?': (
        'Create an account and choose the owner role. Sign in, open your owner dashboard, and '
        'select Add inventory. Enter the item details, price, and stock to publish a listing.',
        'owner owners list listing listings add upload inventory item items product products stock',
    ),
    'Where can I see my reservations?': (
        'Sign in and open your dashboard. Your customer reservations appear under My bookings, '
        'where you can check their status and available actions.',
        'status track tracking dashboard confirmed confirmation reservations reservation bookings booking',
    ),
    'What should I do if an item is unavailable?': (
        'Try a different event date or a smaller quantity, or browse similar items in the same '
        'category. Availability is checked when you submit a booking.',
        'availability available stock unavailable item items date dates quantity booking reservation',
    ),
    'How do I contact support?': (
        'Open Ask the assistant from any page and ask your question. If the answer is not in the '
        'help articles, the assistant creates a support ticket. Sign in to view your tickets.',
        'help support contact ticket human assistant',
    ),
}

ADDITIONAL_FAQS = [
    (
        'What items can I rent?',
        'Ask the assistant to show the items, or browse Explore rentals on the home page. The '
        'assistant lists active items from the current catalog; use search and category filters '
        'to explore them.',
        'what which all items products rentals inventory equipment show list catalog catalogue available',
    ),
    (
        'How do I search or filter items?',
        'On the home page, browse Explore rentals. Enter an item name in Search or choose a '
        'category, then select Search items.',
        'search filter category categories find browse item items products',
    ),
    (
        'Where can I see item prices?',
        'Open a rental item from Explore rentals to view its price per day and any listed security '
        'deposit before you submit a booking.',
        'price prices cost costs rate daily per day deposit item rental',
    ),
]


def expand_help_content(apps, schema_editor):
    FAQ = apps.get_model('myapp', 'FAQ')
    database = schema_editor.connection.alias
    for question, (answer, keywords) in FAQ_UPDATES.items():
        FAQ.objects.using(database).filter(question=question).update(
            answer=answer,
            keywords=keywords,
        )
    for question, answer, keywords in ADDITIONAL_FAQS:
        FAQ.objects.using(database).get_or_create(
            question=question,
            defaults={'answer': answer, 'keywords': keywords},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_support_content'),
    ]

    operations = [
        migrations.RunPython(expand_help_content, migrations.RunPython.noop),
    ]
