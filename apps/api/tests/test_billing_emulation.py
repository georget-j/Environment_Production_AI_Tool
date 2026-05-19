from unittest.mock import MagicMock

import pytest

from app.config import get_settings
from app.routers.billing import (
    CheckoutRequest,
    create_checkout_session,
    stripe_webhook,
)


@pytest.fixture(autouse=True)
def _emulate(monkeypatch):
    monkeypatch.setenv("STRIPE_EMULATED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _user():
    u = MagicMock()
    u.id = "11111111-1111-1111-1111-111111111111"
    u.email = "u@e.com"
    u.subscription_status = "free"
    return u


def test_checkout_emulated_flips_status_and_returns_success_url() -> None:
    user = _user()
    db = MagicMock()
    db.get.return_value = user

    auth = MagicMock()
    auth.id = user.id
    body = CheckoutRequest(success_url="https://example.com/ok", cancel_url="https://example.com/cancel")

    result = create_checkout_session(body=body, db=db, user=auth)
    assert result.url == "https://example.com/ok"
    assert user.subscription_status == "active"
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_webhook_emulated_is_a_noop() -> None:
    db = MagicMock()
    result = await stripe_webhook(request=MagicMock(), stripe_signature=None, db=db)
    assert result == {"received": "emulated"}
    db.commit.assert_not_called()
