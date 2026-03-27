from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def number(value, decimals=0):
    if value is None or value == "":
        return "-"

    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 0

    try:
        num = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    return f"{num:,.{decimals}f}" if decimals > 0 else f"{num:,.0f}"


@register.filter
def status_badge_class(value):
    if not value:
        return "badge badge-secondary"

    status = str(value).strip().lower()

    if status in ["pending", "pending approval", "pending authorization"]:
        return "badge badge-pending"
    if status == "pending collection":
        return "badge badge-info"
    if status == "partially issued":
        return "badge badge-purple"
    if status in ["issued", "fully issued", "approved", "authorized"]:
        return "badge badge-success"
    if status in ["rejected", "cancelled"]:
        return "badge badge-danger"
    if status == "skipped":
        return "badge badge-secondary"

    return "badge badge-secondary"


@register.filter
def yesno_badge(value):
    return "badge badge-info" if value else "badge badge-secondary"