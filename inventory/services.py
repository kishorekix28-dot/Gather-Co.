"""Inventory domain services. All stock changes go through `record_transaction`."""
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import ActivityLog, Product, StockTransaction

logger = logging.getLogger("inventory.app")


def log_activity(user, action, description):
    try:
        ActivityLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action=action[:60],
            description=str(description)[:255],
        )
    except Exception:  # activity logging must never break the main operation
        logger.exception("Could not write activity log")


@transaction.atomic
def record_transaction(*, product, transaction_type, quantity, user=None, supplier=None, unit_cost=None,
                       reference="", note="", new_quantity=None):
    """Apply a stock movement atomically and record it.

    - IN / OUT: `quantity` is the number of units moved (> 0).
    - ADJ: `new_quantity` is the counted stock level; the delta is recorded.
    Raises ValidationError if the movement would make stock negative.
    """
    locked = Product.objects.select_for_update().get(pk=product.pk)
    before = locked.quantity

    if transaction_type == StockTransaction.ADJUSTMENT:
        if new_quantity is None or int(new_quantity) < 0:
            raise ValidationError("Adjusted quantity must be zero or greater.")
        after = int(new_quantity)
        change = after - before
        if change == 0:
            raise ValidationError("The new quantity equals the current stock; nothing to adjust.")
        moved = abs(change)
    else:
        if quantity is None or int(quantity) <= 0:
            raise ValidationError("Quantity must be a positive whole number.")
        moved = int(quantity)
        if transaction_type == StockTransaction.STOCK_IN:
            change = moved
        elif transaction_type == StockTransaction.STOCK_OUT:
            change = -moved
        else:
            raise ValidationError("Unknown transaction type.")
        after = before + change

    if after < 0:
        raise ValidationError(
            f"Insufficient stock: only {before} unit(s) of {locked.sku} available, cannot remove {moved}."
        )

    locked.quantity = after
    locked.save(update_fields=["quantity", "updated_at"])
    txn = StockTransaction.objects.create(
        product=locked,
        transaction_type=transaction_type,
        quantity=moved,
        quantity_change=change,
        quantity_before=before,
        quantity_after=after,
        unit_cost=unit_cost if unit_cost is not None else locked.cost,
        supplier=supplier,
        reference=reference,
        note=note,
        user=user if (user and user.is_authenticated) else None,
    )
    log_activity(user, txn.get_transaction_type_display(), f"{locked.sku}: {before} → {after} ({change:+d})")
    product.quantity = after
    return txn
