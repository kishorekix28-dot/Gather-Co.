from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from inventory.models import ActivityLog, Category, Product, StockTransaction
from inventory.services import record_transaction
from suppliers.models import Supplier

from .helpers import PASSWORD, make_product, make_user


class AuthenticationTests(TestCase):
    def test_registration_creates_customer_user_and_logs_in(self):
        resp = self.client.post(reverse("accounts:register"), {
            "username": "newstaff", "email": "new@example.com", "first_name": "New", "last_name": "Staff",
            "password1": "Very$ecure-2026", "password2": "Very$ecure-2026"})
        self.assertRedirects(resp, reverse("bookings:customer_dashboard"))
        from django.contrib.auth.models import User
        user = User.objects.get(username="newstaff")
        self.assertEqual(user.profile.role, "CUSTOMER")
        self.assertTrue(user.password.startswith(("pbkdf2_", "argon2", "bcrypt")), "password must be hashed")
        self.assertNotEqual(user.password, "Very$ecure-2026")

    def test_login_and_logout(self):
        make_user("alice")
        resp = self.client.post(reverse("accounts:login"), {"username": "alice", "password": PASSWORD})
        self.assertRedirects(resp, reverse("inventory:dashboard"))
        self.assertEqual(self.client.get(reverse("inventory:dashboard")).status_code, 200)
        resp = self.client.post(reverse("accounts:logout"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.get(reverse("inventory:dashboard")).status_code, 302)

    def test_logout_requires_post(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)

    def test_invalid_credentials(self):
        make_user("alice")
        resp = self.client.post(reverse("accounts:login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid username or password")

    def test_restricted_pages_redirect_anonymous(self):
        for name in ("inventory:dashboard", "inventory:product_list", "inventory:transaction_list",
                     "inventory:category_list", "suppliers:list", "inventory:reports", "support:list"):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302, name)
            self.assertIn(reverse("accounts:login"), resp["Location"])

    def test_staff_cannot_access_admin_features(self):
        make_user("bob")
        self.client.login(username="bob", password=PASSWORD)
        product = make_product()
        for url in (reverse("inventory:product_create"), reverse("inventory:product_delete", args=[product.pk]),
                    reverse("suppliers:list"), reverse("inventory:reports"), reverse("accounts:user_list"),
                    reverse("assistant:knowledge_base")):
            self.assertEqual(self.client.get(url).status_code, 403, url)
        # Staff can view inventory and products
        self.assertEqual(self.client.get(reverse("inventory:product_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:product_detail", args=[product.pk])).status_code, 200)


class ProductTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", "ADMIN")
        self.client.login(username="admin", password=PASSWORD)
        self.category = Category.objects.create(name="Electronics")
        self.supplier = Supplier.objects.create(name="Acme")

    def _data(self, **overrides):
        data = {"name": "Wireless Mouse", "sku": "elec-100", "category": self.category.pk, "supplier": self.supplier.pk,
                "price": "24.99", "cost": "12.00", "min_stock_level": "5", "description": "Test", "opening_stock": "20"}
        data.update(overrides)
        return data

    def test_add_product_with_opening_stock(self):
        resp = self.client.post(reverse("inventory:product_create"), self._data())
        product = Product.objects.get(sku="ELEC-100")
        self.assertRedirects(resp, product.get_absolute_url())
        self.assertEqual(product.quantity, 20)
        txn = product.transactions.get()
        self.assertEqual((txn.transaction_type, txn.quantity_before, txn.quantity_after), ("IN", 0, 20))
        self.assertTrue(ActivityLog.objects.filter(action="Created product").exists())

    def test_duplicate_sku_rejected_case_insensitive(self):
        make_product(sku="ELEC-100")
        resp = self.client.post(reverse("inventory:product_create"), self._data(sku="Elec-100"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already exists")
        self.assertEqual(Product.objects.filter(sku="ELEC-100").count(), 1)

    def test_validation_errors(self):
        resp = self.client.post(reverse("inventory:product_create"), self._data(price="-1", sku="bad sku!", name=""))
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertIn("price", form.errors)
        self.assertIn("sku", form.errors)
        self.assertIn("name", form.errors)
        self.assertFalse(Product.objects.exists())

    def test_edit_product(self):
        product = make_product(sku="EDIT-1", qty=3)
        data = self._data(sku="EDIT-1", name="Renamed", price="30.00")
        data.pop("opening_stock")
        resp = self.client.post(reverse("inventory:product_update", args=[product.pk]), data)
        self.assertEqual(resp.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.name, "Renamed")
        self.assertEqual(str(product.price), "30.00")
        self.assertEqual(product.quantity, 3, "editing must not change quantity")

    def test_delete_product(self):
        product = make_product(sku="DEL-1")
        self.assertEqual(self.client.get(reverse("inventory:product_delete", args=[product.pk])).status_code, 200)
        resp = self.client.post(reverse("inventory:product_delete", args=[product.pk]))
        self.assertRedirects(resp, reverse("inventory:product_list"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_image_upload(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, "PNG")
        img = SimpleUploadedFile("p.png", buf.getvalue(), content_type="image/png")
        resp = self.client.post(reverse("inventory:product_create"), {**self._data(sku="IMG-1"), "image": img})
        self.assertEqual(resp.status_code, 302)
        product = Product.objects.get(sku="IMG-1")
        self.assertTrue(product.image.name.startswith("products/"))
        product.image.delete(save=False)


class StockTests(TestCase):
    def setUp(self):
        self.staff = make_user("staff")
        self.client.login(username="staff", password=PASSWORD)
        self.product = make_product(sku="STK-1", qty=0, min_level=5)

    def post(self, ttype, qty, **extra):
        return self.client.post(reverse("inventory:transaction_create"),
                                {"product": self.product.pk, "transaction_type": ttype, "quantity": qty, **extra})

    def test_stock_in_and_out(self):
        self.assertEqual(self.post("IN", 12).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 12)
        self.assertEqual(self.post("OUT", 4).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 8)
        self.assertEqual(StockTransaction.objects.filter(product=self.product).count(), 2)
        out = StockTransaction.objects.filter(transaction_type="OUT").get()
        self.assertEqual((out.quantity_before, out.quantity_after, out.quantity_change, out.user), (12, 8, -4, self.staff))

    def test_negative_stock_prevented(self):
        self.post("IN", 3)
        resp = self.post("OUT", 5)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Insufficient stock")
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 3)
        with self.assertRaises(ValidationError):
            record_transaction(product=self.product, transaction_type="OUT", quantity=10)
        self.assertEqual(StockTransaction.objects.filter(transaction_type="OUT").count(), 0)

    def test_zero_and_negative_quantities_rejected(self):
        self.assertEqual(self.post("IN", 0).status_code, 200)
        self.assertEqual(self.post("IN", -5).status_code, 200)
        self.assertFalse(StockTransaction.objects.exists())

    def test_low_stock_and_out_of_stock_alerts(self):
        self.post("IN", 10)
        resp = self.client.post(reverse("inventory:transaction_create"),
                                {"product": self.product.pk, "transaction_type": "OUT", "quantity": 7}, follow=True)
        self.assertContains(resp, "Low stock alert")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_status, "low")
        resp = self.client.post(reverse("inventory:transaction_create"),
                                {"product": self.product.pk, "transaction_type": "OUT", "quantity": 3}, follow=True)
        self.assertContains(resp, "Out of stock alert")
        self.assertIn(self.product, Product.objects.out_of_stock())

    def test_staff_cannot_adjust_but_admin_can(self):
        self.post("IN", 10)
        self.assertEqual(self.post("ADJ", 4).status_code, 200)  # choice not offered to staff
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)
        make_user("boss", "ADMIN")
        self.client.login(username="boss", password=PASSWORD)
        self.assertEqual(self.post("ADJ", 4).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 4)
        adj = StockTransaction.objects.get(transaction_type="ADJ")
        self.assertEqual(adj.quantity_change, -6)

    def test_dashboard_counts(self):
        make_product(sku="OUT-1", qty=0)
        make_product(sku="LOW-1", qty=2, min_level=5)
        make_product(sku="OK-1", qty=50, min_level=5)
        resp = self.client.get(reverse("inventory:dashboard"))
        totals = resp.context["totals"]
        self.assertEqual(totals["total_products"], 4)
        self.assertEqual(totals["out_of_stock"], 2)
        self.assertEqual(totals["low_stock"], 1)
        self.assertEqual(len(resp.context["monthly"]), 6)


class SearchFilterTests(TestCase):
    def setUp(self):
        make_user("staff")
        self.client.login(username="staff", password=PASSWORD)
        self.cat_a = Category.objects.create(name="A")
        self.cat_b = Category.objects.create(name="B")
        make_product(sku="ALPHA-1", name="Alpha widget", qty=50, category=self.cat_a)
        make_product(sku="BETA-1", name="Beta gadget", qty=2, min_level=5, category=self.cat_b)
        make_product(sku="GAMMA-1", name="Gamma gizmo", qty=0, category=self.cat_b)

    def skus(self, **params):
        resp = self.client.get(reverse("inventory:product_list"), params)
        return [p.sku for p in resp.context["page_obj"]]

    def test_search_by_name_and_sku(self):
        self.assertEqual(self.skus(q="widget"), ["ALPHA-1"])
        self.assertEqual(self.skus(sku="beta"), ["BETA-1"])

    def test_category_and_stock_filters(self):
        self.assertEqual(sorted(self.skus(category=self.cat_b.pk)), ["BETA-1", "GAMMA-1"])
        self.assertEqual(self.skus(stock="low"), ["BETA-1"])
        self.assertEqual(self.skus(stock="out"), ["GAMMA-1"])
        self.assertEqual(self.skus(stock="in"), ["ALPHA-1"])

    def test_sorting_and_pagination(self):
        self.assertEqual(self.skus(sort="-quantity"), ["ALPHA-1", "BETA-1", "GAMMA-1"])
        self.assertEqual(self.skus(sort="quantity"), ["GAMMA-1", "BETA-1", "ALPHA-1"])
        for i in range(12):
            make_product(sku=f"PAGE-{i:02d}")
        resp = self.client.get(reverse("inventory:product_list"), {"page": 2})
        self.assertEqual(resp.context["page_obj"].number, 2)
        self.assertEqual(len(resp.context["page_obj"].object_list), 5)


class CategorySupplierReportTests(TestCase):
    def setUp(self):
        make_user("admin", "ADMIN")
        self.client.login(username="admin", password=PASSWORD)

    def test_category_crud_and_search(self):
        self.client.post(reverse("inventory:category_create"), {"name": "Tools", "description": "Hand tools"})
        cat = Category.objects.get(name="Tools")
        self.client.post(reverse("inventory:category_update", args=[cat.pk]), {"name": "Power Tools"})
        cat.refresh_from_db()
        self.assertEqual(cat.name, "Power Tools")
        resp = self.client.get(reverse("inventory:category_list"), {"q": "power"})
        self.assertEqual([c.name for c in resp.context["categories"]], ["Power Tools"])
        product = make_product(category=cat)
        self.assertContains(self.client.get(reverse("inventory:category_detail", args=[cat.pk])), product.sku)
        self.client.post(reverse("inventory:category_delete", args=[cat.pk]))
        product.refresh_from_db()
        self.assertIsNone(product.category)

    def test_supplier_crud_and_purchase_history(self):
        self.client.post(reverse("suppliers:create"), {"name": "Globex", "email": "a@globex.example",
                                                        "phone": "+1 555 0100", "is_active": "on"})
        sup = Supplier.objects.get(name="Globex")
        product = make_product()
        record_transaction(product=product, transaction_type="IN", quantity=7, supplier=sup, unit_cost=2)
        resp = self.client.get(reverse("suppliers:detail", args=[sup.pk]))
        self.assertEqual(resp.context["totals"]["units"], 7)
        self.assertContains(resp, product.name)
        self.client.post(reverse("suppliers:update", args=[sup.pk]), {"name": "Globex Corp", "phone": "123",
                                                                      "is_active": "on"})
        sup.refresh_from_db()
        self.assertEqual(sup.name, "Globex Corp")
        bad = self.client.post(reverse("suppliers:update", args=[sup.pk]), {"name": "Globex Corp", "phone": "abc"})
        self.assertEqual(bad.status_code, 200)
        self.client.post(reverse("suppliers:delete", args=[sup.pk]))
        self.assertFalse(Supplier.objects.exists())

    def test_reports_and_csv_export(self):
        p = make_product(sku="CSV-1", qty=0, min_level=5)
        record_transaction(product=p, transaction_type="IN", quantity=3)
        for kind in ("inventory", "stock-in", "stock-out", "low-stock", "valuation", "movement"):
            self.assertEqual(self.client.get(reverse("inventory:reports"), {"report": kind}).status_code, 200)
            resp = self.client.get(reverse("inventory:export_csv", args=[kind]))
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp["Content-Type"], "text/csv")
            self.assertIn("attachment", resp["Content-Disposition"])
        body = self.client.get(reverse("inventory:export_csv", args=["low-stock"])).content.decode()
        self.assertIn("CSV-1", body)
        self.assertEqual(self.client.get("/reports/export/unknown/").status_code, 404)
