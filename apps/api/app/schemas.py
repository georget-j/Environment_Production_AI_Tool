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
