from unittest.mock import MagicMock

from app.routers.billing import _apply_event


def _user_row(**overrides):
    u = MagicMock()
    u.id = "11111111-1111-1111-1111-111111111111"
    u.email = "u@e.com"
    u.stripe_customer_id = None
    u.subscription_status = "free"
    for k, v in overrides.items():
        setattr(u, k, v)
    return u


def _fake_db(user) -> MagicMock:
    db = MagicMock()
    db.get.return_value = user
    db.scalar.return_value = user
    return db


def test_checkout_completed_flips_status() -> None:
    user = _user_row()
    db = _fake_db(user)
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": user.id,
                "customer": "cus_TEST123",
            }
        },
    }
    _apply_event(db, event)
    assert user.subscription_status == "active"
    assert user.stripe_customer_id == "cus_TEST123"
    db.commit.assert_called()


def test_subscription_updated_maps_status() -> None:
    user = _user_row(stripe_customer_id="cus_X")
    db = _fake_db(user)
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"customer": "cus_X", "status": "past_due"}},
    }
    _apply_event(db, event)
    assert user.subscription_status == "past_due"


def test_subscription_deleted_cancels() -> None:
    user = _user_row(stripe_customer_id="cus_X", subscription_status="active")
    db = _fake_db(user)
    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_X"}},
    }
    _apply_event(db, event)
    assert user.subscription_status == "canceled"


def test_unknown_event_is_ignored() -> None:
    user = _user_row()
    db = _fake_db(user)
    _apply_event(db, {"type": "charge.refunded", "data": {"object": {}}})
    # No mutations made.
    assert user.subscription_status == "free"
