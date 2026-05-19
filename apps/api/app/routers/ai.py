from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.mentor import ChallengeContext, chat
from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import AIMessage, Challenge, Submission, UserChallengeProgress

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    challenge_id: UUID
    message: str = Field(..., min_length=1, max_length=4000)
    hint_level: int = Field(1, ge=1, le=3)


class ChatTurnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Literal["user", "assistant"]
    content: str
    hint_level: int | None
    created_at: datetime


class ChatResponse(BaseModel):
    user_turn: ChatTurnOut
    assistant_turn: ChatTurnOut


def _load_history(db: Session, user_id: UUID, challenge_id: UUID, limit: int = 20) -> list[dict[str, str]]:
    rows = (
        db.scalars(
            select(AIMessage)
            .where(AIMessage.user_id == user_id, AIMessage.challenge_id == challenge_id)
            .order_by(AIMessage.created_at.desc())
            .limit(limit)
        )
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in reversed(rows) if row.role in ("user", "assistant")]


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ChatResponse:
    challenge = db.get(Challenge, body.challenge_id)
    if challenge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")

    progress = db.scalar(
        select(UserChallengeProgress).where(
            UserChallengeProgress.user_id == user.id,
            UserChallengeProgress.challenge_id == challenge.id,
        )
    )
    latest_submission = db.scalar(
        select(Submission)
        .where(Submission.user_id == user.id, Submission.challenge_id == challenge.id)
        .order_by(Submission.created_at.desc())
        .limit(1)
    )

    context = ChallengeContext(
        title=challenge.title,
        scenario=challenge.scenario,
        learner_goal=challenge.learner_goal,
        latest_test_output=latest_submission.test_output if latest_submission else None,
        attempts_count=progress.attempts_count if progress else 0,
    )

    history = _load_history(db, user.id, challenge.id)

    try:
        assistant_text, metadata = chat(context, history, body.message, body.hint_level)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    user_msg = AIMessage(
        user_id=user.id,
        challenge_id=challenge.id,
        role="user",
        content=body.message,
        hint_level=body.hint_level,
        prompt_sha=metadata["prompt_sha"],
    )
    assistant_msg = AIMessage(
        user_id=user.id,
        challenge_id=challenge.id,
        role="assistant",
        content=assistant_text,
        hint_level=body.hint_level,
        prompt_sha=metadata["prompt_sha"],
        metadata_json=metadata,
    )
    db.add_all([user_msg, assistant_msg])
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return ChatResponse(
        user_turn=ChatTurnOut.model_validate(user_msg),
        assistant_turn=ChatTurnOut.model_validate(assistant_msg),
    )


@router.get("/messages/{challenge_id}", response_model=list[ChatTurnOut])
def list_messages(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[ChatTurnOut]:
    rows = (
        db.scalars(
            select(AIMessage)
            .where(AIMessage.user_id == user.id, AIMessage.challenge_id == challenge_id)
            .order_by(AIMessage.created_at)
        )
        .all()
    )
    return [ChatTurnOut.model_validate(r) for r in rows if r.role in ("user", "assistant")]
