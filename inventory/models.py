from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def out_of_stock(self):
        return self.filter(quantity=0)

    def low_stock(self):
        return self.filter(quantity__gt=0, quantity__lte=models.F("min_stock_level"))

    def in_stock(self):
        return self.filter(quantity__gt=models.F("min_stock_level"))

    def needs_attention(self):
        return self.filter(quantity__lte=models.F("min_stock_level"))


class Product(models.Model):
    STATUS_IN = "in"
    STATUS_LOW = "low"
    STATUS_OUT = "out"

    name = models.CharField(max_length=150)
    sku = models.CharField("SKU", max_length=40, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    cost = models.DecimalField(
        "purchase cost", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=5)
    image = models.ImageField(upload_to="products/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gte=0), name="product_quantity_non_negative")]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        self.sku = (self.sku or "").strip().upper()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("inventory:product_detail", args=[self.pk])

    @property
    def stock_status(self):
        if self.quantity == 0:
            return self.STATUS_OUT
        if self.quantity <= self.min_stock_level:
            return self.STATUS_LOW
        return self.STATUS_IN

    @property
    def stock_status_label(self):
        return {self.STATUS_OUT: "Out of stock", self.STATUS_LOW: "Low stock", self.STATUS_IN: "In stock"}[
            self.stock_status
        ]

    @property
    def stock_value(self):
        return self.cost * self.quantity

    @property
    def retail_value(self):
        return self.price * self.quantity


class StockTransaction(models.Model):
    STOCK_IN = "IN"
    STOCK_OUT = "OUT"
    ADJUSTMENT = "ADJ"
    TYPE_CHOICES = [(STOCK_IN, "Stock In"), (STOCK_OUT, "Stock Out"), (ADJUSTMENT, "Adjustment")]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField(help_text="Units moved (always positive).")
    quantity_change = models.IntegerField(help_text="Signed change applied to stock.")
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.quantity_change:+d} {self.product.sku}"

    @property
    def total_cost(self):
        return (self.unit_cost or Decimal("0")) * self.quantity


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=60)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.action}: {self.description}"
