"""Load realistic demo data: categories, suppliers, products, 6 months of transactions and demo users.

Demo user passwords come from DEMO_ADMIN_PASSWORD / DEMO_STAFF_PASSWORD env vars
(or --admin-password / --staff-password); nothing is hardcoded.
"""
import os
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile
from inventory.models import Category, Product, StockTransaction
from inventory.services import record_transaction
from suppliers.models import Supplier

CATEGORIES = {
    "Electronics": "Devices, components and accessories",
    "Office Supplies": "Stationery and everyday office items",
    "Furniture": "Desks, chairs and storage",
    "Networking": "Routers, switches and cabling",
    "Packaging": "Boxes, tape and shipping materials",
    "Cleaning": "Janitorial and hygiene supplies",
}
SUPPLIERS = [
    ("Northwind Components", "Asha Raman", "orders@northwind.example", "+91 44 4000 1000", "Chennai, India"),
    ("BlueRiver Office Co.", "Daniel Ortiz", "sales@blueriver.example", "+1 415 555 0134", "San Francisco, USA"),
    ("Apex Furniture Works", "Meera Iyer", "hello@apexfurniture.example", "+91 80 2222 3333", "Bengaluru, India"),
    ("PackRight Logistics", "Tom Becker", "support@packright.example", "+49 30 1234 5678", "Berlin, Germany"),
]
PRODUCTS = [
    ("Wireless Mouse", "ELEC-001", "Electronics", 0, 24.99, 11.50, 120, 20),
    ("Mechanical Keyboard", "ELEC-002", "Electronics", 0, 89.00, 52.00, 45, 10),
    ("27\" 4K Monitor", "ELEC-003", "Electronics", 0, 329.00, 245.00, 8, 10),
    ("USB-C Docking Station", "ELEC-004", "Electronics", 0, 149.00, 98.00, 0, 5),
    ("Noise-cancelling Headset", "ELEC-005", "Electronics", 0, 119.00, 70.00, 32, 8),
    ("A4 Copy Paper (500 sheets)", "OFF-001", "Office Supplies", 1, 6.50, 3.20, 400, 100),
    ("Gel Pens (Box of 12)", "OFF-002", "Office Supplies", 1, 9.90, 4.10, 60, 25),
    ("Sticky Notes Pack", "OFF-003", "Office Supplies", 1, 4.75, 1.90, 18, 30),
    ("Desk Organizer", "OFF-004", "Office Supplies", 1, 22.00, 10.00, 27, 10),
    ("Ergonomic Office Chair", "FUR-001", "Furniture", 2, 279.00, 165.00, 14, 5),
    ("Standing Desk", "FUR-002", "Furniture", 2, 499.00, 310.00, 4, 5),
    ("Filing Cabinet", "FUR-003", "Furniture", 2, 189.00, 112.00, 9, 3),
    ("Gigabit Switch 24-port", "NET-001", "Networking", 0, 219.00, 140.00, 11, 4),
    ("Cat6 Cable 10m", "NET-002", "Networking", 0, 12.00, 4.50, 150, 40),
    ("Wi-Fi 6 Router", "NET-003", "Networking", 0, 159.00, 96.00, 0, 6),
    ("Shipping Box Medium", "PKG-001", "Packaging", 3, 1.80, 0.65, 800, 200),
    ("Packing Tape Roll", "PKG-002", "Packaging", 3, 3.20, 1.10, 140, 50),
    ("Bubble Wrap 50m", "PKG-003", "Packaging", 3, 24.00, 12.00, 6, 10),
    ("Hand Sanitizer 1L", "CLN-001", "Cleaning", 1, 8.50, 3.90, 70, 20),
    ("Microfiber Cloths (10)", "CLN-002", "Cleaning", 1, 11.00, 4.80, 35, 15),
]


class Command(BaseCommand):
    help = "Populate the database with demo inventory data."

    def add_arguments(self, parser):
        parser.add_argument("--admin-password", default=os.environ.get("DEMO_ADMIN_PASSWORD"))
        parser.add_argument("--staff-password", default=os.environ.get("DEMO_STAFF_PASSWORD"))
        parser.add_argument("--reset", action="store_true", help="Delete existing inventory data first.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            StockTransaction.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Supplier.objects.all().delete()

        admin = self._user("admin", "admin@stockpilot.example", opts["admin_password"], "ADMIN", "Kishore", "Admin")
        staff = self._user("staff", "staff@stockpilot.example", opts["staff_password"], "STAFF", "Priya", "Staff")

        cats = {name: Category.objects.get_or_create(name=name, defaults={"description": d})[0]
                for name, d in CATEGORIES.items()}
        sups = [Supplier.objects.get_or_create(name=n, defaults={"contact_person": c, "email": e, "phone": p,
                                                                   "address": a})[0]
                for n, c, e, p, a in SUPPLIERS]

        if Product.objects.exists():
            self.stdout.write("Products already exist; skipping product/transaction seeding.")
            return

        rng = random.Random(42)
        now = timezone.now()
        for name, sku, cat, sup, price, cost, target, min_level in PRODUCTS:
            product = Product.objects.create(
                name=name, sku=sku, category=cats[cat], supplier=sups[sup], price=Decimal(str(price)),
                cost=Decimal(str(cost)), quantity=0, min_stock_level=min_level,
                description=f"{name} – stocked item in {cat.lower()}.",
            )
            # Build a plausible 6-month history that ends at the target quantity.
            history = []
            qty = 0
            for month_back in range(5, -1, -1):
                received = rng.randint(target // 3 + 5, target + 15) if target else rng.randint(5, 15)
                history.append(("IN", received, month_back))
                qty += received
                issued = rng.randint(0, qty // 2) if month_back else max(qty - target, 0)
                if month_back == 0:
                    issued = qty - target
                if issued > 0:
                    history.append(("OUT", issued, month_back))
                    qty -= issued
            for ttype, amount, month_back in history:
                txn = record_transaction(
                    product=product, transaction_type=ttype, quantity=amount,
                    user=admin if ttype == "IN" else staff, supplier=product.supplier if ttype == "IN" else None,
                    reference=f"{'PO' if ttype == 'IN' else 'SO'}-{rng.randint(1000, 9999)}",
                )
                stamp = now - timedelta(days=30 * month_back + rng.randint(0, 20), hours=rng.randint(0, 10))
                StockTransaction.objects.filter(pk=txn.pk).update(created_at=stamp)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Category.objects.count()} categories, {Supplier.objects.count()} suppliers, "
            f"{Product.objects.count()} products, {StockTransaction.objects.count()} transactions."))

    def _user(self, username, email, password, role, first, last):
        user = User.objects.filter(username=username).first()
        if user:
            return user
        if not password:
            raise CommandError(f"Provide a password for demo user '{username}' via env or CLI option.")
        user = User.objects.create_user(username, email, password, first_name=first, last_name=last,
                                        is_staff=role == "ADMIN", is_superuser=role == "ADMIN")
        Profile.objects.update_or_create(user=user, defaults={"role": role})
        return user
