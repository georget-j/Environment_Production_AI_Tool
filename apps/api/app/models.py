"""SQLAlchemy models mirroring supabase/migrations/0001_init.sql.

Supabase is canonical for schema. These models exist so apps/api can issue
typed queries against the same Postgres instance the web app reads via PostgREST.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="learner", nullable=False)
    subscription_status: Mapped[str] = mapped_column(String, default="free", nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    track_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    module_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    learner_goal: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    repo_template_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    repo_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_config_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_rules_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserChallengeProgress(Base):
    __tablename__ = "user_challenge_progress"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    challenge_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String, default="not_started", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    challenge_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"))
    repo_url: Mapped[str] = mapped_column(Text, nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    test_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    lint_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_review_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    prompt_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    challenge_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    hint_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
