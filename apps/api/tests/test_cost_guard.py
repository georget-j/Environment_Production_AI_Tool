import pytest
from fastapi import HTTPException

from app.cost_guard import DEFAULT_LIMITS, _kill_switch_on, _limit, enforce_ai_budget


def test_kill_switch_off_by_default(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("AI_KILL_SWITCH", raising=False)
    assert _kill_switch_on() is False


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
def test_kill_switch_truthy_values(monkeypatch, value: str) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AI_KILL_SWITCH", value)
    assert _kill_switch_on() is True


@pytest.mark.parametrize("value", ["false", "0", "no", "", "maybe"])
def test_kill_switch_falsy_values(monkeypatch, value: str) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AI_KILL_SWITCH", value)
    assert _kill_switch_on() is False


def test_default_limits_match_documented_caps() -> None:
    # If these change, update docs/cost-guards.md to match.
    assert DEFAULT_LIMITS["chat"] == 50
    assert DEFAULT_LIMITS["show_answer"] == 10
    assert DEFAULT_LIMITS["explain_tests"] == 30


def test_limit_overridden_via_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AI_DAILY_CHAT_LIMIT", "5")
    assert _limit("chat") == 5


def test_limit_zero_means_disabled(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AI_DAILY_SHOW_ANSWER_LIMIT", "0")
    assert _limit("show_answer") == 0


def test_limit_invalid_env_falls_back(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AI_DAILY_CHAT_LIMIT", "not-a-number")
    assert _limit("chat") == DEFAULT_LIMITS["chat"]


def test_limit_negative_clamped(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AI_DAILY_CHAT_LIMIT", "-99")
    assert _limit("chat") == 0


class _DummyDB:
    """Minimal stand-in for a Session — enforce_ai_budget only calls .scalar()."""

    def __init__(self, count: int) -> None:
        self._count = count

    def scalar(self, _stmt: object) -> int:
        return self._count


def test_enforce_raises_503_when_kill_switch_on(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("AI_KILL_SWITCH", "true")
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc:
        enforce_ai_budget(_DummyDB(0), uuid4(), "chat")  # type: ignore[arg-type]
    assert exc.value.status_code == 503


def test_enforce_raises_503_when_limit_zero(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("AI_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AI_DAILY_CHAT_LIMIT", "0")
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc:
        enforce_ai_budget(_DummyDB(0), uuid4(), "chat")  # type: ignore[arg-type]
    assert exc.value.status_code == 503


def test_enforce_raises_429_when_quota_hit(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("AI_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AI_DAILY_CHAT_LIMIT", "3")
    from uuid import uuid4

    with pytest.raises(HTTPException) as exc:
        enforce_ai_budget(_DummyDB(3), uuid4(), "chat")  # type: ignore[arg-type]
    assert exc.value.status_code == 429


def test_enforce_passes_when_under_quota(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("AI_KILL_SWITCH", raising=False)
    monkeypatch.setenv("AI_DAILY_CHAT_LIMIT", "10")
    from uuid import uuid4

    enforce_ai_budget(_DummyDB(2), uuid4(), "chat")  # type: ignore[arg-type]
