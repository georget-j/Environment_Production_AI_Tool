"""Coupon validation.

Hardcoded for the MVP. In a real app this hits Stripe Coupons or a DB.
"""

from __future__ import annotations

_VALID_CODES = {
    "WELCOME10": 10,  # 10% off
    "SUMMER20": 20,
    "VIP50": 50,
}


def is_valid(code: str | None) -> bool:
    if not code:
        return False
    return code.strip().upper() in _VALID_CODES


def discount_percent(code: str | None) -> int:
    if not code:
        return 0
    return _VALID_CODES.get(code.strip().upper(), 0)
