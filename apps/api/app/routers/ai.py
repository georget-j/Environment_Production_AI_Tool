from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.answers import AnswerInput, answer
from app.ai.explainer import ExplainInput, explain
from app.ai.mentor import ChallengeContext, chat
from app.auth import AuthUser, get_current_user
from app.cost_guard import enforce_ai_budget
from app.db import get_db
from app.models import AIMessage, Challenge, Submission, UserChallengeProgress

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    challenge_id: UUID
    message: str = Field(..., min_length=1, max_length=4000)
    hint_level: int = Field(1, ge=1, le=3)
    # Snapshot of the learner's current editor contents. Sent on every
    # chat call so the mentor never has to ask the learner to paste code.
    current_files: dict[str, str] = Field(default_factory=dict)


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

    enforce_ai_budget(db, user.id, "chat")

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

    # Defensive: cap each file to 6000 chars before handing to the prompt
    # builder (which also caps per-file to 4000).
    capped_files = {
        path: (body.current_files.get(path) or "")[:6000]
        for path in body.current_files
    }

    context = ChallengeContext(
        title=challenge.title,
        scenario=challenge.scenario,
        learner_goal=challenge.learner_goal,
        latest_test_output=latest_submission.test_output if latest_submission else None,
        attempts_count=progress.attempts_count if progress else 0,
        current_files=capped_files or None,
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


class ExplainTestsRequest(BaseModel):
    challenge_id: UUID
    test_output: str = Field(..., min_length=1, max_length=20000)
    files: dict[str, str] = Field(default_factory=dict)


class FailureExplanation(BaseModel):
    test_name: str
    what_was_checked: str
    what_happened: str
    where_to_look: str
    file: str | None = None
    line: int | None = None
    function: str | None = None


class ExplainTestsResponse(BaseModel):
    failures: list[FailureExplanation]


@router.post("/explain-tests", response_model=ExplainTestsResponse)
def explain_tests_endpoint(
    body: ExplainTestsRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ExplainTestsResponse:
    challenge = db.get(Challenge, body.challenge_id)
    if challenge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")

    enforce_ai_budget(db, user.id, "explain_tests")

    # Truncate files defensively (the model has a context window).
    capped = {path: (body.files.get(path) or "")[:4000] for path in body.files}

    try:
        payload, metadata = explain(
            ExplainInput(
                challenge_title=challenge.title,
                scenario=challenge.scenario,
                learner_goal=challenge.learner_goal,
                test_output=body.test_output,
                files=capped,
            )
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    # Persist a thin audit row tagged source=explain_tests so the cost guard
    # can count usage. Content kept short — the failure list is rendered
    # client-side, this row exists for accounting.
    db.add(
        AIMessage(
            user_id=user.id,
            challenge_id=challenge.id,
            role="assistant",
            content=f"Explained {len(payload.get('failures', []))} test failure(s).",
            hint_level=None,
            prompt_sha=metadata.get("prompt_sha") if isinstance(metadata, dict) else None,
            metadata_json={**(metadata if isinstance(metadata, dict) else {}), "source": "explain_tests"},
        )
    )
    db.commit()

    return ExplainTestsResponse(
        failures=[FailureExplanation(**f) for f in payload.get("failures", [])]
    )


class ShowAnswerRequest(BaseModel):
    challenge_id: UUID
    editable_files: dict[str, str] = Field(..., min_length=1)
    readonly_files: dict[str, str] = Field(default_factory=dict)
    test_output: str | None = None


class FixedFile(BaseModel):
    path: str
    content: str


class ShowAnswerResponse(BaseModel):
    fixed_files: list[FixedFile]
    summary: str


@router.post("/show-answer", response_model=ShowAnswerResponse)
def show_answer_endpoint(
    body: ShowAnswerRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ShowAnswerResponse:
    challenge = db.get(Challenge, body.challenge_id)
    if challenge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")

    enforce_ai_budget(db, user.id, "show_answer")

    editable = {p: (body.editable_files.get(p) or "")[:6000] for p in body.editable_files}
    readonly = {p: (body.readonly_files.get(p) or "")[:4000] for p in body.readonly_files}

    try:
        payload, metadata = answer(
            AnswerInput(
                challenge_title=challenge.title,
                scenario=challenge.scenario,
                learner_goal=challenge.learner_goal,
                editable_files=editable,
                readonly_files=readonly,
                test_output=body.test_output,
            )
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    summary = payload.get("summary", "")
    # Persist a server-side record so the show-answer summary survives page
    # reload, admins can audit usage, and the cost guard can count calls.
    # Always written (even on empty summary) so an empty-response failure
    # mode can't bypass the per-user daily quota.
    db.add(
        AIMessage(
            user_id=user.id,
            challenge_id=challenge.id,
            role="assistant",
            content=f"Here's a working version. {summary}" if summary else "(show_answer: empty summary)",
            hint_level=None,
            prompt_sha=metadata.get("prompt_sha"),
            metadata_json={**metadata, "source": "show_answer"},
        )
    )
    db.commit()

    return ShowAnswerResponse(
        fixed_files=[FixedFile(**f) for f in payload.get("fixed_files", [])],
        summary=summary,
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


@router.delete("/messages/{challenge_id}")
def clear_messages(
    challenge_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, int]:
    """Delete all of this learner's chat history for a challenge.

    Owner-only by definition: the WHERE clause includes user_id. Returns
    the number of rows removed for the UI to show a confirmation.
    """
    result = db.execute(
        delete(AIMessage).where(
            AIMessage.user_id == user.id,
            AIMessage.challenge_id == challenge_id,
        )
    )
    db.commit()
    return {"deleted": result.rowcount or 0}
