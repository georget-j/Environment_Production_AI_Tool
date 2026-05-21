"""Cost guards for OpenAI-backed routes.

Two layers of defence against a runaway OpenAI bill:

1. A global kill switch (env: ``AI_KILL_SWITCH``). Set to ``true`` on Fly and
   every AI endpoint immediately returns 503 without calling OpenAI. One
   command to stop the bleeding if something goes sideways.

2. Per-user, per-day quotas tuned for a ~$10/month combined OpenAI cap with
   gpt-4o-mini for chat/explain and gpt-4o for show-answer. Counts are read
   from the AIMessage table — the system of record — so a process restart
   doesn't grant fresh allowance.

Defaults can be overridden via env:
    AI_DAILY_CHAT_LIMIT, AI_DAILY_SHOW_ANSWER_LIMIT, AI_DAILY_EXPLAIN_LIMIT.
Setting a limit to 0 disables that endpoint (returns 503).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AIMessage

GuardKind = Literal["chat", "show_answer", "explain_tests"]

DEFAULT_LIMITS: dict[GuardKind, int] = {
    "chat": 50,
    "show_answer": 10,
    "explain_tests": 30,
}


def _kill_switch_on() -> bool:
    return os.getenv("AI_KILL_SWITCH", "").strip().lower() in ("1", "true", "yes", "on")


def _limit(kind: GuardKind) -> int:
    env_name = f"AI_DAILY_{kind.upper()}_LIMIT"
    raw = os.getenv(env_name)
    if raw is None:
        return DEFAULT_LIMITS[kind]
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_LIMITS[kind]
    return max(0, parsed)


def _utc_today_start() -> datetime:
    now = datetime.now(UTC)
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


def _count_today(db: Session, user_id: UUID, kind: GuardKind) -> int:
    today = _utc_today_start()
    if kind == "chat":
        # Every chat call writes one user-role row, so user rows == chat calls.
        stmt = (
            select(func.count())
            .select_from(AIMessage)
            .where(
                AIMessage.user_id == user_id,
                AIMessage.role == "user",
                AIMessage.created_at >= today,
            )
        )
    else:
        # show_answer / explain_tests are written with metadata_json.source = kind.
        stmt = (
            select(func.count())
            .select_from(AIMessage)
            .where(
                AIMessage.user_id == user_id,
                AIMessage.metadata_json.op("->>")("source") == kind,
                AIMessage.created_at >= today,
            )
        )
    return db.scalar(stmt) or 0


def enforce_ai_budget(db: Session, user_id: UUID, kind: GuardKind) -> None:
    """Raises 503 if the kill switch is on, 429 if the user is over today's quota."""
    if _kill_switch_on():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI features are temporarily disabled. Please try again later.",
        )
    limit = _limit(kind)
    if limit == 0:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"AI feature '{kind}' is currently disabled.",
        )
    count = _count_today(db, user_id, kind)
    if count >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily limit reached for {kind} ({limit}/day). Try again tomorrow.",
        )
