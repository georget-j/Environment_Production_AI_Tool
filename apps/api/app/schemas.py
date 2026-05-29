"""Pydantic response schemas. Mirrored on the TS side in packages/shared."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TrackOut(_Base):
    id: UUID
    slug: str
    title: str
    description: str | None
    difficulty: str | None


class ModuleOut(_Base):
    id: UUID
    slug: str
    title: str
    order_index: int


class ChallengeSummary(_Base):
    id: UUID
    slug: str
    title: str
    order_index: int
    is_free: bool
    skills: list[str]
    module_id: UUID


class ChallengeNavRef(_Base):
    slug: str
    title: str


class ChallengeDetail(ChallengeSummary):
    scenario: str
    learner_goal: str
    instructions: str
    repo_template_url: str | None
    repo_branch: str | None
    validation_config_json: dict
    ai_rules_json: dict
    module: ModuleOut
    previous: ChallengeNavRef | None = None
    next: ChallengeNavRef | None = None
    position_in_track: int = 1
    total_in_track: int = 1


class TrackDetail(TrackOut):
    modules: list[ModuleOut]
    challenges: list[ChallengeSummary]


class ProgressOut(_Base):
    id: UUID
    challenge_id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    attempts_count: int


class TrackProgressOut(_Base):
    """Per-track aggregate for the authenticated user. Used by the dashboard
    to render progress bars + a 'Continue track' CTA per track card."""

    slug: str
    title: str
    description: str | None = None
    difficulty: str | None = None
    completed: int
    total: int
    latest_in_progress_slug: str | None = None
    # M5 — concept-mastery rollup for concept-based tracks (Mental Models
    # today). For challenge-based tracks both are 0. When non-zero AND the
    # track has no challenges, completed/total above mirror these so the
    # dashboard progress bar Just Works.
    concept_completed: int = 0
    concept_total: int = 0


class ContinueRef(_Base):
    """Pointer to the lesson the dashboard's 'Resume' card should link to —
    the most-recently-started in-progress lesson across all tracks."""

    track_slug: str
    track_title: str
    module_title: str
    challenge_slug: str
    challenge_title: str
    position: int
    total: int


class MeProgressOut(_Base):
    tracks: list[TrackProgressOut]
    continue_lesson: ContinueRef | None = None


class TrackProgressDetail(_Base):
    """Per-challenge progress for a single track, used to decorate the
    track-detail page with done/current/not-yet state per lesson."""

    completed_slugs: list[str]
    in_progress_slugs: list[str]
    next_unsolved_slug: str | None = None
    completed: int
    total: int
    module_progress: dict[str, dict[str, int]]  # module_id (str) → {completed, total}


# ----------------------------------------------------------------------------
# Concept atoms — Mental Models for Code pilot (CC.1)
# ----------------------------------------------------------------------------


class ConceptStageProgress(_Base):
    """Snapshot of one learner's progress through a concept's stages.

    Each field is the completion timestamp for that stage, or null if
    not yet completed. mastered_at flips when read..reflect are all set.
    status is the human-readable rollup ('in_progress'|'mastered'|'needs_review').
    """

    try_attempted_at: datetime | None = None
    try_attempt_text: str | None = None
    read_completed_at: datetime | None = None
    play_completed_at: datetime | None = None
    check_completed_at: datetime | None = None
    apply_completed_at: datetime | None = None
    reflect_completed_at: datetime | None = None
    mastered_at: datetime | None = None
    next_recall_due_at: datetime | None = None
    recall_interval_days: int = 1
    recall_streak: int = 0
    status: str = "in_progress"


class ConceptSummary(_Base):
    """Listed in the track index and the concept map."""

    id: UUID
    slug: str
    layer: str
    topic_slug: str | None
    title: str
    one_line: str
    order_index: int


class ConceptDetail(ConceptSummary):
    """Full concept payload — used by the unit shell to render all 6 stages."""

    try_prompt_md: str
    try_kind: str
    try_expected_attempts_json: list
    exposition_md: str
    worked_example_md: str
    play_widget_kind: str
    play_widget_json: dict
    check_mcqs_json: list
    apply_challenge_slug: str | None
    # M2 — inline Pyodide skeleton for Apply.
    # Shape: {instructions_md, starter_code, hidden_test} or None.
    apply_skeleton_json: dict | None = None
    # M4 — Try→Read personalisation. When the learner has recorded a Try
    # attempt that matches one of try_expected_attempts[].pattern, this
    # holds the matched callback_md so the Read stage can surface "you
    # tried X — here's why" inline.
    try_attempt_matched_callback_md: str | None = None
    reflect_question: str
    reflect_rubric_json: dict
    recall_checks_json: list
    # Slugs of prerequisite concepts — used by the concept map + the
    # "you may want to revisit X" recommendation in Apply.
    prereqs: list[str] = []
    # Current learner's per-stage progress, if signed in. Optional so an
    # anonymous read-only client can still fetch the concept.
    progress: ConceptStageProgress | None = None


class StageCompleteRequest(_Base):
    """POST body when the learner finishes a stage. Always idempotent —
    re-completing a stage is a no-op."""

    stage: str  # 'read' | 'play' | 'check' | 'apply' | 'reflect'


class StageCompleteResponse(_Base):
    progress: ConceptStageProgress


class TryAttemptRequest(_Base):
    """POST body when the learner submits a Try attempt."""

    attempt_text: str


class ReflectGradeRequest(_Base):
    """POST body for the Reflect stage — the learner's explanation goes
    to the mentor for rubric grading."""

    explanation: str


class ReflectGradeResponse(_Base):
    verdict: str  # 'complete' | 'shallow'
    follow_up: str | None = None
    rubric_hits: dict = {}
    # When verdict == 'complete', the server also marks reflect_completed_at.
    progress: ConceptStageProgress


class ConceptMentorTurn(_Base):
    """One historical message in the concept-mentor conversation."""

    role: str  # 'user' | 'assistant'
    content: str


class ConceptMentorRequest(_Base):
    """POST body for the concept-mode mentor (Read/Try teaching)."""

    message: str
    history: list[ConceptMentorTurn] = []
    # Optional active stage hint so the mentor knows what the learner is
    # looking at right now. Server-side this is just additional context.
    stage: str | None = None


class ConceptMentorResponse(_Base):
    reply: str
    # Slugs of concepts the mentor mentioned that were stripped by the
    # forward-reference sanitiser; surfaced for debugging only.
    removed_forward_refs: list[str] = []


class ConceptFeedbackRequest(_Base):
    """M8 — learner feedback on a concept atom."""

    kind: str  # 'helpful' | 'confusing' | 'other'
    stage: str | None = None
    free_text: str | None = None


class ConceptFeedbackResponse(_Base):
    ok: bool = True
