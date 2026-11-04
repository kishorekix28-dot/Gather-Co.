"""Convert existing USD prices/costs to Indian Rupees (one-time, 1 USD = ₹83)."""
from decimal import Decimal

from django.db import migrations

RATE = Decimal("83")


def to_inr(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    StockTransaction = apps.get_model("inventory", "StockTransaction")
    for p in Product.objects.all():
        p.price = (p.price * RATE).quantize(Decimal("1"))
        p.cost = (p.cost * RATE).quantize(Decimal("1"))
        p.save(update_fields=["price", "cost"])
    for t in StockTransaction.objects.exclude(unit_cost=None):
        t.unit_cost = (t.unit_cost * RATE).quantize(Decimal("1"))
        t.save(update_fields=["unit_cost"])


class Migration(migrations.Migration):
    dependencies = [("inventory", "0001_initial")]
    operations = [migrations.RunPython(to_inr, migrations.RunPython.noop)]
