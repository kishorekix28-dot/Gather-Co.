from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.forms import StyledFormMixin
from accounts.roles import admin_required
from inventory.models import StockTransaction
from inventory.services import log_activity

from .models import Supplier


class SupplierForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_person", "email", "phone", "website", "address", "notes", "is_active"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2}), "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Supplier.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A supplier with this name already exists.")
        return name

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if phone and not all(c.isdigit() or c in "+-() " for c in phone):
            raise forms.ValidationError("Phone may contain digits, spaces, +, -, ( and ) only.")
        return phone


@admin_required
def supplier_list(request):
    q = request.GET.get("q", "").strip()
    suppliers = Supplier.objects.annotate(
        product_count=Count("products", distinct=True),
        purchases=Count("transactions", filter=Q(transactions__transaction_type="IN"), distinct=True),
    )
    if q:
        suppliers = suppliers.filter(Q(name__icontains=q) | Q(contact_person__icontains=q) | Q(email__icontains=q))
    page = Paginator(suppliers.order_by("name"), 12).get_page(request.GET.get("page"))
    return render(request, "suppliers.html", {"page_obj": page, "q": q})


@admin_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    purchases = StockTransaction.objects.filter(supplier=supplier, transaction_type="IN").select_related("product", "user")
    total = purchases.aggregate(
        units=Coalesce(Sum("quantity"), 0),
        spend=Coalesce(Sum(ExpressionWrapper(F("unit_cost") * F("quantity"),
                                             output_field=DecimalField(max_digits=18, decimal_places=2))), 0,
                       output_field=DecimalField(max_digits=18, decimal_places=2)),
    )
    page = Paginator(purchases, 15).get_page(request.GET.get("page"))
    return render(request, "supplier_detail.html", {
        "supplier": supplier, "page_obj": page, "totals": total,
        "products": supplier.products.order_by("name")[:20],
    })


@admin_required
@require_http_methods(["GET", "POST"])
def supplier_form(request, pk=None):
    supplier = get_object_or_404(Supplier, pk=pk) if pk else None
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        log_activity(request.user, "Updated supplier" if pk else "Created supplier", obj.name)
        messages.success(request, f"Supplier {obj.name} saved.")
        return redirect(obj)
    return render(request, "simple_form.html", {
        "form": form, "title": "Edit supplier" if pk else "Add supplier", "cancel_url": "suppliers:list",
    })


@admin_required
@require_http_methods(["GET", "POST"])
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        name = supplier.name
        supplier.delete()
        log_activity(request.user, "Deleted supplier", name)
        messages.success(request, f"Supplier {name} deleted.")
        return redirect("suppliers:list")
    return render(request, "confirm_delete.html", {
        "object": supplier, "kind": "supplier", "cancel_url": supplier.get_absolute_url(),
        "warning": "Products and purchase history are kept; the supplier link is removed.",
    })
