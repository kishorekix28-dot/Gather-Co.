from decimal import Decimal

from django.contrib.auth.models import User

from accounts.models import Profile
from inventory.models import Category, Product

PASSWORD = "Str0ng!Test-Pass"


def make_user(username, role="STAFF"):
    user = User.objects.create_user(username, f"{username}@example.com", PASSWORD,
                                    is_superuser=role == "ADMIN", is_staff=role == "ADMIN")
    Profile.objects.update_or_create(user=user, defaults={"role": role})
    return user


def make_product(sku="TEST-001", qty=0, min_level=5, **kw):
    cat = kw.pop("category", None) or Category.objects.get_or_create(name="Testing")[0]
    return Product.objects.create(name=kw.pop("name", f"Product {sku}"), sku=sku, category=cat,
                                  price=Decimal("10.00"), cost=Decimal("6.00"), quantity=qty,
                                  min_stock_level=min_level, **kw)
