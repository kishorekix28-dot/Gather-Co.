"""Indian Rupee formatting: ₹12,34,567.89 (Indian digit grouping)."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template

register = template.Library()


def format_inr(value, decimals=2):
    try:
        amount = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError, TypeError):
        return value
    decimals = int(decimals)
    quant = Decimal(1) if decimals == 0 else Decimal(1).scaleb(-decimals)
    amount = amount.quantize(quant, rounding=ROUND_HALF_UP)
    sign = "-" if amount < 0 else ""
    integer, _, frac = f"{abs(amount):.{decimals}f}".partition(".")
    if len(integer) > 3:
        head, tail = integer[:-3], integer[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        integer = ",".join(groups + [tail])
    return f"{sign}₹{integer}" + (f".{frac}" if decimals else "")


@register.filter(name="inr")
def inr(value, decimals=2):
    return format_inr(value, decimals)
