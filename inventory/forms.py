import re
from decimal import Decimal

from django import forms

from accounts.forms import StyledFormMixin
from suppliers.models import Supplier

from .models import Category, Product, StockTransaction

SKU_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-_]{1,39}$")
MAX_IMAGE_BYTES = 3 * 1024 * 1024


class ProductForm(StyledFormMixin, forms.ModelForm):
    opening_stock = forms.IntegerField(
        min_value=0, initial=0, required=False, label="Opening stock",
        help_text="Initial quantity on hand. Later changes are made through stock transactions.",
    )

    class Meta:
        model = Product
        fields = ["name", "sku", "category", "supplier", "price", "cost", "min_stock_level", "description", "image"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "cost": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }
        help_texts = {"sku": "Unique stock keeping unit: letters, digits, dashes (e.g. ELEC-001)."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.filter(is_active=True)
        if self.instance.pk:
            del self.fields["opening_stock"]
        self._style()
        self.fields["image"].widget.attrs["accept"] = "image/*"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Product name must be at least 2 characters.")
        return name

    def clean_sku(self):
        sku = self.cleaned_data["sku"].strip().upper()
        if not SKU_RE.match(sku):
            raise forms.ValidationError("SKU may only contain letters, digits, '-' and '_' (2–40 characters).")
        qs = Product.objects.filter(sku__iexact=sku)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A product with SKU {sku} already exists.")
        return sku

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "size") and image.size > MAX_IMAGE_BYTES:
            raise forms.ValidationError("Image must be 3 MB or smaller.")
        return image

    def clean(self):
        data = super().clean()
        price, cost = data.get("price"), data.get("cost")
        if price is not None and price < Decimal("0"):
            self.add_error("price", "Price cannot be negative.")
        if cost is not None and cost < Decimal("0"):
            self.add_error("cost", "Cost cannot be negative.")
        return data


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A category with this name already exists.")
        return name


class StockMovementForm(StyledFormMixin, forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.select_related("category").all())
    transaction_type = forms.ChoiceField(choices=StockTransaction.TYPE_CHOICES, label="Type")
    quantity = forms.IntegerField(
        min_value=0, required=False,
        help_text="Units to add/remove. For adjustments, enter the counted stock level.",
    )
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.filter(is_active=True), required=False)
    unit_cost = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False)
    reference = forms.CharField(max_length=80, required=False, help_text="PO / invoice / order number")
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean(self):
        data = super().clean()
        ttype, qty = data.get("transaction_type"), data.get("quantity")
        if qty is None:
            self.add_error("quantity", "Quantity is required.")
        elif ttype in (StockTransaction.STOCK_IN, StockTransaction.STOCK_OUT) and qty <= 0:
            self.add_error("quantity", "Quantity must be greater than zero.")
        if ttype != StockTransaction.STOCK_IN:
            data["supplier"] = None
        return data
