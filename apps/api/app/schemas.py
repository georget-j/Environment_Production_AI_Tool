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


class ChallengeDetail(ChallengeSummary):
    scenario: str
    learner_goal: str
    instructions: str
    repo_template_url: str | None
    repo_branch: str | None
    validation_config_json: dict
    ai_rules_json: dict
    module: ModuleOut


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
