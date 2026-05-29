"""Concept-atom router — Mental Models for Code pilot (Phase CC.1).

Endpoints:

  GET  /api/concepts                         List all concepts (summaries).
  GET  /api/concepts/{slug}                  Full concept payload + (signed-in) progress.
  POST /api/concepts/{slug}/try              Record a Try-stage attempt.
  POST /api/concepts/{slug}/stages/{stage}/complete
                                             Mark a stage complete (idempotent).
  POST /api/concepts/{slug}/reflect          Grade a Reflect explanation against the
                                             concept's rubric and (on 'complete') mark
                                             reflect_completed_at.

Concept-mode mentor calls (Read/Try teaching, Reflect grading) all go through
the helpers in app.ai.mentor and inherit its forward-reference sanitiser.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.mentor import ConceptContext, reflect_grade, socratic_teach
from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import Concept, ConceptFeedback, ConceptMastery, ConceptPrereq
from app.schemas import (
    ConceptDetail,
    ConceptFeedbackRequest,
    ConceptFeedbackResponse,
    ConceptMentorRequest,
    ConceptMentorResponse,
    ConceptStageProgress,
    ConceptSummary,
    ReflectGradeRequest,
    ReflectGradeResponse,
    StageCompleteRequest,
    StageCompleteResponse,
    TryAttemptRequest,
)

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


# The five stages that participate in mastery rollup. Try is non-blocking
# and excluded — it's just a productive-failure record.
_GATED_STAGES: tuple[str, ...] = ("read", "play", "check", "apply", "reflect")
_VALID_STAGES = frozenset(_GATED_STAGES)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _progress_from_row(row: ConceptMastery | None) -> ConceptStageProgress:
    if row is None:
        return ConceptStageProgress()
    return ConceptStageProgress(
        try_attempted_at=row.try_attempted_at,
        try_attempt_text=row.try_attempt_text,
        read_completed_at=row.read_completed_at,
        play_completed_at=row.play_completed_at,
        check_completed_at=row.check_completed_at,
        apply_completed_at=row.apply_completed_at,
        reflect_completed_at=row.reflect_completed_at,
        mastered_at=row.mastered_at,
        next_recall_due_at=row.next_recall_due_at,
        recall_interval_days=row.recall_interval_days,
        recall_streak=row.recall_streak,
        status=row.status,
    )


def _get_or_create_mastery(
    db: Session, user_id, concept_id
) -> ConceptMastery:
    row = db.scalar(
        select(ConceptMastery).where(
            ConceptMastery.user_id == user_id,
            ConceptMastery.concept_id == concept_id,
        )
    )
    if row is None:
        row = ConceptMastery(user_id=user_id, concept_id=concept_id)
        db.add(row)
        db.flush()
    return row


def _maybe_mark_mastered(row: ConceptMastery) -> None:
    """If every gated stage is complete, flip status to 'mastered' and
    schedule the first spaced-recall check (1 day out)."""
    if row.mastered_at is not None:
        return
    if not all(
        getattr(row, f"{stage}_completed_at") is not None for stage in _GATED_STAGES
    ):
        return
    now = _now()
    row.mastered_at = now
    row.status = "mastered"
    # First recall in 1 day (the floor of the SuperMemo-2-lite ladder).
    row.recall_interval_days = 1
    row.next_recall_due_at = now.replace(microsecond=0).replace(
        tzinfo=timezone.utc
    )  # placeholder; CC.4 wires the real scheduling


def _match_try_callback(
    attempt_text: str | None, expected: list | None
) -> str | None:
    """M4 — find the first matching try_expected_attempts entry.

    Each entry is `{"pattern": <regex>, "callback_md": <md>}`. We try them
    in author-order; first hit wins. Malformed regexes are skipped (we
    never let an author typo blow up Read).
    """
    if not attempt_text or not expected:
        return None
    for entry in expected:
        if not isinstance(entry, dict):
            continue
        pattern = entry.get("pattern")
        callback = entry.get("callback_md")
        if not pattern or not callback:
            continue
        try:
            if re.search(pattern, attempt_text):
                return callback
        except re.error:
            continue
    return None


def _load_concept_or_404(db: Session, slug: str) -> Concept:
    concept = db.scalar(select(Concept).where(Concept.slug == slug))
    if concept is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Concept not found")
    return concept


def _prereq_slugs_for(db: Session, concept_id) -> list[str]:
    rows = list(
        db.execute(
            select(Concept.slug)
            .join(
                ConceptPrereq,
                ConceptPrereq.prereq_concept_id == Concept.id,
            )
            .where(ConceptPrereq.concept_id == concept_id)
            .order_by(Concept.order_index)
        ).all()
    )
    return [r[0] for r in rows]


# ----------------------------------------------------------------------------
# List + detail (anonymous-friendly; progress only attaches when signed in)
# ----------------------------------------------------------------------------


@router.get("", response_model=list[ConceptSummary])
def list_concepts(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> list[ConceptSummary]:
    # Auth required: concepts are part of the paid learner experience.
    del user
    concepts = list(
        db.scalars(select(Concept).order_by(Concept.layer, Concept.order_index)).all()
    )
    # Hydrate prereq slugs in a single pass (M9). prereq rows join through
    # concept ids; we fetch the join then re-key by the consumer's id.
    prereq_pairs = list(
        db.execute(
            select(
                ConceptPrereq.concept_id,
                Concept.slug,
            )
            .join(Concept, Concept.id == ConceptPrereq.prereq_concept_id)
        ).all()
    )
    prereqs_by_concept_id: dict = {}
    for cid, prereq_slug in prereq_pairs:
        prereqs_by_concept_id.setdefault(cid, []).append(prereq_slug)
    return [
        ConceptSummary(
            id=c.id,
            slug=c.slug,
            layer=c.layer,
            topic_slug=c.topic_slug,
            title=c.title,
            one_line=c.one_line,
            order_index=c.order_index,
            prereqs=prereqs_by_concept_id.get(c.id, []),
        )
        for c in concepts
    ]


@router.get("/{slug}", response_model=ConceptDetail)
def get_concept(
    slug: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ConceptDetail:
    concept = _load_concept_or_404(db, slug)
    prereqs = _prereq_slugs_for(db, concept.id)

    row = db.scalar(
        select(ConceptMastery).where(
            ConceptMastery.user_id == user.id,
            ConceptMastery.concept_id == concept.id,
        )
    )
    progress = _progress_from_row(row)

    matched_callback = _match_try_callback(
        progress.try_attempt_text,
        concept.try_expected_attempts_json or [],
    )

    return ConceptDetail(
        id=concept.id,
        slug=concept.slug,
        layer=concept.layer,
        topic_slug=concept.topic_slug,
        title=concept.title,
        one_line=concept.one_line,
        order_index=concept.order_index,
        try_prompt_md=concept.try_prompt_md,
        try_kind=concept.try_kind,
        try_expected_attempts_json=concept.try_expected_attempts_json or [],
        exposition_md=concept.exposition_md,
        worked_example_md=concept.worked_example_md,
        play_widget_kind=concept.play_widget_kind,
        play_widget_json=concept.play_widget_json or {},
        check_mcqs_json=concept.check_mcqs_json or [],
        apply_challenge_slug=concept.apply_challenge_slug,
        apply_skeleton_json=concept.apply_skeleton_json,
        try_attempt_matched_callback_md=matched_callback,
        reflect_question=concept.reflect_question,
        reflect_rubric_json=concept.reflect_rubric_json or {},
        recall_checks_json=concept.recall_checks_json or [],
        prereqs=prereqs,
        progress=progress,
    )


# ----------------------------------------------------------------------------
# Try-stage attempt — recorded but non-blocking. Surfaced again in Read.
# ----------------------------------------------------------------------------


@router.post("/{slug}/try", response_model=StageCompleteResponse)
def record_try_attempt(
    slug: str,
    body: TryAttemptRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> StageCompleteResponse:
    concept = _load_concept_or_404(db, slug)
    row = _get_or_create_mastery(db, user.id, concept.id)
    if row.try_attempted_at is None:
        row.try_attempted_at = _now()
    # Always overwrite the attempt text — the most recent attempt is what
    # the Read stage should reference inline.
    row.try_attempt_text = body.attempt_text
    db.commit()
    db.refresh(row)
    return StageCompleteResponse(progress=_progress_from_row(row))


# ----------------------------------------------------------------------------
# Stage completion (read / play / check / apply / reflect).
# Reflect can also be reached via /reflect (with grading) — this endpoint
# is a lower-level mark-complete used by Play and Check when the client
# has already validated the stage locally.
# ----------------------------------------------------------------------------


@router.post(
    "/{slug}/stages/{stage}/complete",
    response_model=StageCompleteResponse,
)
def mark_stage_complete(
    slug: str,
    stage: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> StageCompleteResponse:
    if stage not in _VALID_STAGES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown stage {stage!r}. Valid: {sorted(_VALID_STAGES)}",
        )
    concept = _load_concept_or_404(db, slug)
    row = _get_or_create_mastery(db, user.id, concept.id)
    column = f"{stage}_completed_at"
    if getattr(row, column) is None:
        setattr(row, column, _now())
    _maybe_mark_mastered(row)
    db.commit()
    db.refresh(row)
    return StageCompleteResponse(progress=_progress_from_row(row))


# ----------------------------------------------------------------------------
# Reflect — grade the learner's explanation against the rubric, then (on
# 'complete') mark reflect_completed_at and roll into mastery.
# ----------------------------------------------------------------------------


@router.post("/{slug}/reflect", response_model=ReflectGradeResponse)
def grade_reflect(
    slug: str,
    body: ReflectGradeRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ReflectGradeResponse:
    concept = _load_concept_or_404(db, slug)
    row = _get_or_create_mastery(db, user.id, concept.id)

    # Build the mentor-context block. Mastered concepts give the mentor
    # the "safe to reference" allowlist (Exercism constraint).
    mastered_rows = list(
        db.execute(
            select(Concept.slug)
            .join(ConceptMastery, ConceptMastery.concept_id == Concept.id)
            .where(
                ConceptMastery.user_id == user.id,
                ConceptMastery.mastered_at.is_not(None),
            )
        ).all()
    )
    mastered_slugs = tuple(r[0] for r in mastered_rows)
    all_slug_rows = list(db.execute(select(Concept.slug)).all())
    all_slugs = tuple(r[0] for r in all_slug_rows)

    ctx = ConceptContext(
        slug=concept.slug,
        title=concept.title,
        one_line=concept.one_line,
        exposition_md=concept.exposition_md,
        worked_example_md=concept.worked_example_md,
        try_attempt_text=row.try_attempt_text,
        concepts_mastered=mastered_slugs,
        all_concept_slugs=all_slugs,
    )
    grade, _meta = reflect_grade(ctx, concept.reflect_rubric_json or {}, body.explanation)

    if grade.verdict == "complete" and row.reflect_completed_at is None:
        row.reflect_completed_at = _now()
        _maybe_mark_mastered(row)

    db.commit()
    db.refresh(row)
    return ReflectGradeResponse(
        verdict=grade.verdict,
        follow_up=grade.follow_up,
        rubric_hits=grade.rubric_hits,
        progress=_progress_from_row(row),
    )


# ----------------------------------------------------------------------------
# Mentor — concept-mode Socratic teaching (M1).
# Used by the concept page's mentor sidebar. NOT the task-flow mentor; that
# one stays on /api/ai/chat. Returns a single sanitised reply per call.
# ----------------------------------------------------------------------------


@router.post("/{slug}/mentor", response_model=ConceptMentorResponse)
def concept_mentor(
    slug: str,
    body: ConceptMentorRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ConceptMentorResponse:
    concept = _load_concept_or_404(db, slug)
    row = db.scalar(
        select(ConceptMastery).where(
            ConceptMastery.user_id == user.id,
            ConceptMastery.concept_id == concept.id,
        )
    )

    mastered_rows = list(
        db.execute(
            select(Concept.slug)
            .join(ConceptMastery, ConceptMastery.concept_id == Concept.id)
            .where(
                ConceptMastery.user_id == user.id,
                ConceptMastery.mastered_at.is_not(None),
            )
        ).all()
    )
    mastered_slugs = tuple(r[0] for r in mastered_rows)
    all_slug_rows = list(db.execute(select(Concept.slug)).all())
    all_slugs = tuple(r[0] for r in all_slug_rows)

    ctx = ConceptContext(
        slug=concept.slug,
        title=concept.title,
        one_line=concept.one_line,
        exposition_md=concept.exposition_md,
        worked_example_md=concept.worked_example_md,
        try_attempt_text=row.try_attempt_text if row else None,
        concepts_mastered=mastered_slugs,
        all_concept_slugs=all_slugs,
    )
    history = [
        {"role": t.role, "content": t.content} for t in body.history if t.content
    ]
    reply, meta = socratic_teach(ctx, history, body.message)
    return ConceptMentorResponse(
        reply=reply,
        removed_forward_refs=list(meta.get("removed_forward_refs") or []),
    )


# ----------------------------------------------------------------------------
# Feedback — M8. Collect 👍 / 👎 / other signal per concept. No author-facing
# dashboard yet — the SELECT side is queried via direct SQL when needed.
# ----------------------------------------------------------------------------


_FEEDBACK_KINDS = frozenset({"helpful", "confusing", "other"})


@router.post("/{slug}/feedback", response_model=ConceptFeedbackResponse)
def submit_concept_feedback(
    slug: str,
    body: ConceptFeedbackRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ConceptFeedbackResponse:
    if body.kind not in _FEEDBACK_KINDS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown feedback kind {body.kind!r}. Valid: {sorted(_FEEDBACK_KINDS)}",
        )
    # Ensure the concept exists (cheap guard against typos in client calls).
    _load_concept_or_404(db, slug)

    db.add(
        ConceptFeedback(
            user_id=user.id,
            concept_slug=slug,
            stage=body.stage,
            kind=body.kind,
            free_text=(body.free_text or None),
        )
    )
    db.commit()
    return ConceptFeedbackResponse(ok=True)
