"""Read-only queries shared by the dashboard, reports and API."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from .models import Category, Product, StockTransaction

VALUE_EXPR = ExpressionWrapper(F("cost") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))
RETAIL_EXPR = ExpressionWrapper(F("price") * F("quantity"), output_field=DecimalField(max_digits=18, decimal_places=2))


def inventory_totals():
    agg = Product.objects.aggregate(
        total_products=Count("id"),
        total_units=Coalesce(Sum("quantity"), 0),
        total_value=Coalesce(Sum(VALUE_EXPR), Decimal("0")),
        retail_value=Coalesce(Sum(RETAIL_EXPR), Decimal("0")),
    )
    agg["low_stock"] = Product.objects.low_stock().count()
    agg["out_of_stock"] = Product.objects.out_of_stock().count()
    agg["in_stock"] = agg["total_products"] - agg["low_stock"] - agg["out_of_stock"]
    agg["total_categories"] = Category.objects.count()
    return agg


def month_starts(months=6):
    now = timezone.localtime()
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    starts = []
    for _ in range(months):
        starts.append(first)
        first = (first - timedelta(days=1)).replace(day=1)
    return list(reversed(starts))


def monthly_statistics(months=6):
    starts = month_starts(months)
    rows = (
        StockTransaction.objects.filter(created_at__gte=starts[0])
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            stock_in=Coalesce(Sum("quantity", filter=Q(transaction_type="IN")), 0),
            stock_out=Coalesce(Sum("quantity", filter=Q(transaction_type="OUT")), 0),
            adjustments=Count("id", filter=Q(transaction_type="ADJ")),
            transactions=Count("id"),
        )
    )
    by_month = {r["month"].strftime("%Y-%m"): r for r in rows if r["month"]}
    result = []
    for start in starts:
        key = start.strftime("%Y-%m")
        r = by_month.get(key, {})
        result.append({
            "label": start.strftime("%b %Y"),
            "stock_in": r.get("stock_in", 0),
            "stock_out": r.get("stock_out", 0),
            "adjustments": r.get("adjustments", 0),
            "transactions": r.get("transactions", 0),
            "net": r.get("stock_in", 0) - r.get("stock_out", 0),
        })
    return result


def category_valuation():
    return (
        Category.objects.annotate(
            product_count=Count("products"),
            units=Coalesce(Sum("products__quantity"), 0),
            value=Coalesce(
                Sum(ExpressionWrapper(F("products__cost") * F("products__quantity"),
                                      output_field=DecimalField(max_digits=18, decimal_places=2))),
                Decimal("0"),
            ),
        ).order_by("-value")
    )


def product_movement(start=None, end=None):
    filt = Q()
    if start:
        filt &= Q(transactions__created_at__date__gte=start)
    if end:
        filt &= Q(transactions__created_at__date__lte=end)
    return (
        Product.objects.select_related("category")
        .annotate(
            total_in=Coalesce(Sum("transactions__quantity", filter=filt & Q(transactions__transaction_type="IN")), 0),
            total_out=Coalesce(Sum("transactions__quantity", filter=filt & Q(transactions__transaction_type="OUT")), 0),
            movements=Count("transactions", filter=filt),
        )
        .order_by("-movements", "name")
    )
