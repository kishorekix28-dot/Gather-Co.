"""Inventory reports with CSV export (administrators only)."""
import csv
from datetime import date

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.roles import admin_required
from core.currency import convert_valuation

from .models import Product, StockTransaction
from .selectors import category_valuation, inventory_totals, product_movement

REPORTS = {
    "inventory": "Current inventory",
    "stock-in": "Stock-in history",
    "stock-out": "Stock-out history",
    "low-stock": "Low-stock products",
    "valuation": "Inventory valuation",
    "movement": "Product movement",
}


def _parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def build_report(kind, start=None, end=None):
    """Return (headers, rows) for a report kind."""
    if kind == "inventory":
        qs = Product.objects.select_related("category", "supplier").order_by("name")
        headers = ["SKU", "Name", "Category", "Supplier", "Quantity", "Min level", "Status", "Cost", "Price", "Stock value"]
        rows = [[p.sku, p.name, p.category or "", p.supplier or "", p.quantity, p.min_stock_level,
                 p.stock_status_label, p.cost, p.price, p.stock_value] for p in qs]
    elif kind in ("stock-in", "stock-out"):
        ttype = StockTransaction.STOCK_IN if kind == "stock-in" else StockTransaction.STOCK_OUT
        qs = StockTransaction.objects.filter(transaction_type=ttype).select_related("product", "user", "supplier")
        if start:
            qs = qs.filter(created_at__date__gte=start)
        if end:
            qs = qs.filter(created_at__date__lte=end)
        headers = ["Date", "SKU", "Product", "Quantity", "Before", "After", "Unit cost", "Total", "Supplier",
                   "Reference", "User"]
        rows = [[timezone.localtime(t.created_at).strftime("%Y-%m-%d %H:%M"), t.product.sku, t.product.name,
                 t.quantity, t.quantity_before, t.quantity_after, t.unit_cost or "", t.total_cost,
                 t.supplier or "", t.reference, t.user.username if t.user else ""] for t in qs]
    elif kind == "low-stock":
        qs = Product.objects.needs_attention().select_related("category", "supplier").order_by("quantity")
        headers = ["SKU", "Name", "Category", "Quantity", "Min level", "Shortfall", "Status", "Supplier"]
        rows = [[p.sku, p.name, p.category or "", p.quantity, p.min_stock_level,
                 max(p.min_stock_level - p.quantity, 0), p.stock_status_label, p.supplier or ""] for p in qs]
    elif kind == "valuation":
        headers = ["Category", "Products", "Units", "Stock value (cost)"]
        rows = [[c.name, c.product_count, c.units, c.value] for c in category_valuation()]
        uncategorised = Product.objects.filter(category__isnull=True)
        if uncategorised.exists():
            rows.append(["Uncategorised", uncategorised.count(), sum(p.quantity for p in uncategorised),
                         sum(p.stock_value for p in uncategorised)])
    elif kind == "movement":
        headers = ["SKU", "Product", "Category", "Stock in", "Stock out", "Net", "Movements", "Current qty"]
        rows = [[p.sku, p.name, p.category or "", p.total_in, p.total_out, p.total_in - p.total_out, p.movements,
                 p.quantity] for p in product_movement(start, end)]
    else:
        raise Http404("Unknown report")
    return headers, rows


@admin_required
def reports(request):
    kind = request.GET.get("report", "inventory")
    if kind not in REPORTS:
        kind = "inventory"
    start, end = _parse_date(request.GET.get("start")), _parse_date(request.GET.get("end"))
    headers, rows = build_report(kind, start, end)
    totals = inventory_totals()
    return render(request, "reports.html", {
        "reports": REPORTS, "kind": kind, "title": REPORTS[kind], "headers": headers, "rows": rows[:200],
        "row_count": len(rows), "start": request.GET.get("start", ""), "end": request.GET.get("end", ""),
        "totals": totals, "currency": convert_valuation(totals["total_value"]),
    })


@admin_required
def export_csv(request, kind):
    if kind not in REPORTS:
        raise Http404("Unknown report")
    start, end = _parse_date(request.GET.get("start")), _parse_date(request.GET.get("end"))
    headers, rows = build_report(kind, start, end)
    response = HttpResponse(content_type="text/csv")
    stamp = timezone.localdate().isoformat()
    response["Content-Disposition"] = f'attachment; filename="{kind}-report-{stamp}.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        # Neutralise spreadsheet formula injection.
        writer.writerow([f"'{c}" if isinstance(c, str) and c[:1] in "=+-@" else c for c in map(_cell, row)])
    return response


def _cell(value):
    return value if isinstance(value, (int, float)) else str(value)
