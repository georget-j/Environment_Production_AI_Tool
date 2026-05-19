"""Stripe checkout + webhook.

Test mode is the same code path as live — flip STRIPE_SECRET_KEY and
STRIPE_WEBHOOK_SECRET to live values and you are done.
"""

from __future__ import annotations

import logging
from typing import Any

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/api/billing", tags=["billing"])
log = logging.getLogger(__name__)


class CheckoutRequest(BaseModel):
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    url: str


def _stripe_client() -> Any:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> CheckoutResponse:
    settings = get_settings()
    if not settings.stripe_price_pro_monthly:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Pro price not configured")

    db_user = db.get(User, user.id)
    if db_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User row missing")

    client = _stripe_client()

    if not db_user.stripe_customer_id:
        customer = client.Customer.create(
            email=db_user.email,
            metadata={"supabase_user_id": str(user.id)},
        )
        db_user.stripe_customer_id = customer.id
        db.commit()

    session = client.checkout.Session.create(
        mode="subscription",
        customer=db_user.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_pro_monthly, "quantity": 1}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        client_reference_id=str(user.id),
        allow_promotion_codes=True,
    )
    return CheckoutResponse(url=session.url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Stripe webhook not configured")
    if stripe_signature is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing Stripe-Signature header")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid webhook: {exc}") from exc

    _apply_event(db, event)
    return {"received": "ok"}


# Map Stripe subscription statuses to our internal subscription_status column.
_STATUS_MAP = {
    "active": "active",
    "trialing": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "canceled",
    "incomplete": "free",
    "incomplete_expired": "free",
}


def _apply_event(db: Session, event: Any) -> None:
    event_type = event["type"]
    obj = event["data"]["object"]
    handlers = {
        "checkout.session.completed": _on_checkout_completed,
        "customer.subscription.created": _on_subscription_change,
        "customer.subscription.updated": _on_subscription_change,
        "customer.subscription.deleted": _on_subscription_deleted,
    }
    handler = handlers.get(event_type)
    if handler is None:
        log.debug("Ignoring Stripe event %s", event_type)
        return
    handler(db, obj)


def _on_checkout_completed(db: Session, obj: dict) -> None:
    user_id = obj.get("client_reference_id")
    customer_id = obj.get("customer")
    if not user_id:
        return
    user = db.get(User, user_id)
    if user is None:
        return
    if customer_id and not user.stripe_customer_id:
        user.stripe_customer_id = customer_id
    user.subscription_status = "active"
    db.commit()


def _on_subscription_change(db: Session, obj: dict) -> None:
    customer_id = obj.get("customer")
    stripe_status = obj.get("status", "free")
    if not customer_id:
        return
    user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
    if user is None:
        return
    user.subscription_status = _STATUS_MAP.get(stripe_status, "free")
    db.commit()


def _on_subscription_deleted(db: Session, obj: dict) -> None:
    customer_id = obj.get("customer")
    if not customer_id:
        return
    user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
    if user is None:
        return
    user.subscription_status = "canceled"
    db.commit()
