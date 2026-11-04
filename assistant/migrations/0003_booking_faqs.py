from django.db import migrations

FAQS = [
    ("Bookings", "How do I book or reserve items?",
     "Create a customer account, then open **My dashboard**. Choose your **From** and **To** dates and click "
     "**Check** to see how many units of each item are free. Click **Book** on an item, enter the quantity and an "
     "optional note, then **Request booking**. Staff review the request; you can follow its status under "
     "**My bookings**.",
     "book, booking, reserve, reservation, rent, hire, availability, available dates"),
    ("Bookings", "How does staff approve a booking?",
     "Staff open **Booking requests** (or the pending list on the Dashboard) and click **Approve** or **Reject**. "
     "Approval re-checks availability and blocks the booked units on every day of the booking so they cannot be "
     "double-booked. Customers see the decision and any staff message on the booking.",
     "approve booking, reject booking, booking request, confirm reservation, block dates"),
    ("Bookings", "Where can I see booked days on the calendar?",
     "Staff open **Booking calendar** (or the calendar on the Dashboard). Each day shows the approved bookings and "
     "the number of units blocked; dashed entries are still pending. Use the arrows to move between months.",
     "calendar, booked days, schedule, booking calendar, reserved days"),
    ("Bookings", "How do I cancel a booking?",
     "Open **My bookings** and click **Cancel** next to a pending or approved booking that has not ended yet. "
     "Cancelling frees the units for other customers immediately.",
     "cancel booking, cancel reservation, remove booking"),
]


def seed(apps, schema_editor):
    FAQ = apps.get_model("assistant", "FAQ")
    for category, question, answer, keywords in FAQS:
        FAQ.objects.update_or_create(question=question, defaults={
            "answer": answer, "category": category, "keywords": keywords, "is_active": True})


class Migration(migrations.Migration):
    dependencies = [("assistant", "0002_seed_knowledge_base")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
