from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.roles import admin_required, is_admin, is_customer, staff_required
from suppliers.models import Supplier

from .forms import CategoryForm, ProductForm, StockMovementForm
from .models import ActivityLog, Category, Product, StockTransaction
from .selectors import category_valuation, inventory_totals, monthly_statistics
from .services import log_activity, record_transaction

PRODUCT_SORTS = {
    "name": "name", "-name": "-name", "price": "price", "-price": "-price",
    "quantity": "quantity", "-quantity": "-quantity", "newest": "-created_at",
}


def home(request):
    if request.user.is_authenticated:
        return redirect("bookings:customer_dashboard" if is_customer(request.user) else "inventory:dashboard")
    return render(request, "home.html")


@login_required
def dashboard(request):
    if is_customer(request.user):
        return redirect("bookings:customer_dashboard")
    from bookings.models import Booking
    from bookings.services import month_calendar

    today = timezone.localdate()
    totals = inventory_totals()
    monthly = monthly_statistics(6)
    categories = list(category_valuation()[:8])
    context = {
        "totals": totals,
        "recent_transactions": StockTransaction.objects.select_related("product", "user")[:8],
        "recent_activity": ActivityLog.objects.select_related("user")[:8],
        "low_stock_products": Product.objects.needs_attention().select_related("category").order_by("quantity")[:6],
        "monthly": monthly,
        "booking_cal": month_calendar(today.year, today.month),
        "pending_bookings": Booking.objects.filter(status=Booking.PENDING)
        .select_related("product", "customer").order_by("start_date")[:5],
        "todays_bookings": Booking.objects.filter(status=Booking.APPROVED, start_date__lte=today, end_date__gte=today)
        .select_related("product", "customer"),
        "chart_data": {
            "months": [m["label"] for m in monthly],
            "stock_in": [m["stock_in"] for m in monthly],
            "stock_out": [m["stock_out"] for m in monthly],
            "status": [totals["in_stock"], totals["low_stock"], totals["out_of_stock"]],
            "categories": [c.name for c in categories],
            "category_values": [float(c.value) for c in categories],
        },
    }
    return render(request, "dashboard.html", context)


# ---------------------------------------------------------------- products
def filter_products(params):
    qs = Product.objects.select_related("category", "supplier")
    q = params.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
    sku = params.get("sku", "").strip()
    if sku:
        qs = qs.filter(sku__icontains=sku)
    category = params.get("category", "")
    if category.isdigit():
        qs = qs.filter(category_id=int(category))
    stock = params.get("stock", "")
    if stock == "in":
        qs = qs.in_stock()
    elif stock == "low":
        qs = qs.low_stock()
    elif stock == "out":
        qs = qs.out_of_stock()
    elif stock == "available":
        qs = qs.filter(quantity__gt=0)
    sort = params.get("sort", "name")
    return qs.order_by(PRODUCT_SORTS.get(sort, "name"), "id")


@staff_required
def product_list(request):
    qs = filter_products(request.GET)
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "products.html", {
        "page_obj": page,
        "categories": Category.objects.all(),
        "filters": request.GET,
        "querystring": query.urlencode(),
        "result_count": qs.count(),
    })


@staff_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category", "supplier"), pk=pk)
    return render(request, "product_detail.html", {
        "product": product,
        "transactions": product.transactions.select_related("user", "supplier")[:20],
    })


@admin_required
@require_http_methods(["GET", "POST"])
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        product.quantity = 0
        product.save()
        opening = form.cleaned_data.get("opening_stock") or 0
        if opening:
            record_transaction(product=product, transaction_type=StockTransaction.STOCK_IN, quantity=opening,
                               user=request.user, supplier=product.supplier, note="Opening stock")
        log_activity(request.user, "Created product", f"{product.name} ({product.sku})")
        messages.success(request, f"Product {product.sku} created.")
        return redirect(product)
    return render(request, "product_form.html", {"form": form, "title": "Add product"})


@admin_required
@require_http_methods(["GET", "POST"])
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request.user, "Updated product", f"{product.name} ({product.sku})")
        messages.success(request, f"Product {product.sku} updated.")
        return redirect(product)
    return render(request, "product_form.html", {"form": form, "title": f"Edit {product.name}", "product": product})


@admin_required
@require_http_methods(["GET", "POST"])
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        label = f"{product.name} ({product.sku})"
        product.delete()
        log_activity(request.user, "Deleted product", label)
        messages.success(request, f"Product {label} deleted.")
        return redirect("inventory:product_list")
    return render(request, "confirm_delete.html", {
        "object": product, "kind": "product", "cancel_url": product.get_absolute_url(),
        "warning": "All stock transactions for this product will also be deleted.",
    })


# -------------------------------------------------------------- categories
@staff_required
def category_list(request):
    q = request.GET.get("q", "").strip()
    cats = Category.objects.annotate(
        product_count=Count("products"), units=Coalesce(Sum("products__quantity"), 0)
    ).order_by("name")
    if q:
        cats = cats.filter(Q(name__icontains=q) | Q(description__icontains=q))
    return render(request, "categories.html", {"categories": cats, "q": q})


@staff_required
def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    products = category.products.select_related("supplier").order_by("name")
    page = Paginator(products, 10).get_page(request.GET.get("page"))
    return render(request, "category_detail.html", {"category": category, "page_obj": page})


@admin_required
@require_http_methods(["GET", "POST"])
def category_form(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        log_activity(request.user, "Updated category" if pk else "Created category", obj.name)
        messages.success(request, f"Category {obj.name} saved.")
        return redirect("inventory:category_list")
    return render(request, "simple_form.html", {
        "form": form, "title": "Edit category" if pk else "Add category",
        "cancel_url": "inventory:category_list",
    })


@admin_required
@require_http_methods(["GET", "POST"])
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        name = category.name
        category.delete()
        log_activity(request.user, "Deleted category", name)
        messages.success(request, f"Category {name} deleted. Its products are now uncategorised.")
        return redirect("inventory:category_list")
    return render(request, "confirm_delete.html", {
        "object": category, "kind": "category", "cancel_url": "/categories/",
        "warning": f"{category.products.count()} product(s) will become uncategorised (they are not deleted).",
    })


# ------------------------------------------------------------ transactions
@staff_required
def transaction_list(request):
    qs = StockTransaction.objects.select_related("product", "user", "supplier")
    ttype = request.GET.get("type", "")
    if ttype in dict(StockTransaction.TYPE_CHOICES):
        qs = qs.filter(transaction_type=ttype)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q) | Q(reference__icontains=q))
    start, end = request.GET.get("start", ""), request.GET.get("end", "")
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "transactions.html", {
        "page_obj": page, "filters": request.GET, "querystring": query.urlencode(),
        "types": StockTransaction.TYPE_CHOICES,
    })


@staff_required
@require_http_methods(["GET", "POST"])
def transaction_create(request):
    initial = {}
    if request.GET.get("product", "").isdigit():
        initial["product"] = int(request.GET["product"])
    if request.GET.get("type") in dict(StockTransaction.TYPE_CHOICES):
        initial["transaction_type"] = request.GET["type"]
    form = StockMovementForm(request.POST or None, initial=initial)
    if not is_admin(request.user):
        form.fields["transaction_type"].choices = [
            c for c in StockTransaction.TYPE_CHOICES if c[0] != StockTransaction.ADJUSTMENT
        ]
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if data["transaction_type"] == StockTransaction.ADJUSTMENT and not is_admin(request.user):
            raise PermissionDenied("Only administrators can make stock adjustments.")
        product = data["product"]
        try:
            txn = record_transaction(
                product=product,
                transaction_type=data["transaction_type"],
                quantity=data["quantity"],
                new_quantity=data["quantity"] if data["transaction_type"] == StockTransaction.ADJUSTMENT else None,
                user=request.user,
                supplier=data.get("supplier"),
                unit_cost=data.get("unit_cost"),
                reference=data.get("reference", ""),
                note=data.get("note", ""),
            )
        except ValidationError as exc:
            form.add_error("quantity", exc.messages[0])
        else:
            product.refresh_from_db()
            messages.success(
                request,
                f"{txn.get_transaction_type_display()} recorded for {product.sku}: "
                f"{txn.quantity_before} → {txn.quantity_after}.",
            )
            if product.stock_status == Product.STATUS_OUT:
                messages.error(request, f"Out of stock alert: {product.name} has 0 units left.")
            elif product.stock_status == Product.STATUS_LOW:
                messages.warning(
                    request, f"Low stock alert: {product.name} has {product.quantity} unit(s) "
                             f"(minimum {product.min_stock_level})."
                )
            return redirect("inventory:transaction_list")
    return render(request, "transaction_form.html", {"form": form})
