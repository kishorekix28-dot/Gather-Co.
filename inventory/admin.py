from django.contrib import admin

from .models import ActivityLog, Category, Product, StockTransaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "quantity", "min_stock_level", "price", "cost")
    list_filter = ("category",)
    search_fields = ("sku", "name")
    readonly_fields = ("quantity",)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "transaction_type", "quantity_change", "quantity_after", "user")
    list_filter = ("transaction_type",)
    search_fields = ("product__sku", "reference")

    def has_change_permission(self, request, obj=None):
        return False  # the stock ledger is append-only


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "description")
