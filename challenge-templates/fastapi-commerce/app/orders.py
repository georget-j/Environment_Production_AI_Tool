"""Order creation + total calculation."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.coupons import discount_percent, is_valid
from app.models import Order, store


def compute_total(items: list[tuple[UUID, int]], coupon_code: str | None = None) -> int:
    """Return the order total in cents.

    Subtotal = sum(price * qty). If the coupon is valid, apply the percent
    discount to the subtotal. Round down to the nearest cent.
    """
    subtotal_cents = 0
    for product_id, qty in items:
        product = store.get_product(product_id)
        if product is None:
            raise ValueError(f"Unknown product: {product_id}")
        if qty <= 0:
            raise ValueError(f"Quantity must be positive, got {qty}")
        subtotal_cents += product.price_cents * qty

    if coupon_code and is_valid(coupon_code):
        percent = discount_percent(coupon_code)
        subtotal_cents = subtotal_cents - (subtotal_cents * percent) // 100

    return subtotal_cents


def create_order(items: list[tuple[UUID, int]], coupon_code: str | None = None) -> Order:
    if not items:
        raise ValueError("Order must have at least one item")
    total = compute_total(items, coupon_code)
    order = Order(id=uuid4(), items=items, coupon_code=coupon_code, total_cents=total)
    store.add_order(order)
    return order
