"""Paywall enforcement.

Pro challenges (is_free = false) require subscription_status = 'active'.
The first 2 challenges of every track are marked is_free in the seed.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Challenge, User


def ensure_can_access(db: Session, user_id, challenge: Challenge) -> None:
    if challenge.is_free:
        return
    user = db.get(User, user_id)
    if user is None or user.subscription_status not in ("active",):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Pro subscription required for this challenge",
        )
