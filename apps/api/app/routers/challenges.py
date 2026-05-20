from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import ensure_can_access
from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import Challenge, Module, UserChallengeProgress
from app.schemas import ChallengeDetail, ChallengeNavRef, ModuleOut, ProgressOut

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.get("/{slug}", response_model=ChallengeDetail)
def get_challenge(slug: str, db: Session = Depends(get_db)) -> ChallengeDetail:
    challenge = db.scalar(select(Challenge).where(Challenge.slug == slug))
    if not challenge:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")
    module = db.get(Module, challenge.module_id)
    if module is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Challenge has no module")

    # Sibling challenges across the whole track, ordered first by module
    # position then by challenge position. Used for prev/next nav + "Lesson N
    # of M" display in the UI.
    siblings = (
        db.execute(
            select(Challenge.slug, Challenge.title, Challenge.id)
            .join(Module, Challenge.module_id == Module.id)
            .where(Module.track_id == module.track_id)
            .order_by(Module.order_index, Challenge.order_index)
        )
        .all()
    )
    total = len(siblings)
    position = 1
    previous_ref: ChallengeNavRef | None = None
    next_ref: ChallengeNavRef | None = None
    for i, row in enumerate(siblings):
        if row.id == challenge.id:
            position = i + 1
            if i > 0:
                previous_ref = ChallengeNavRef(slug=siblings[i - 1].slug, title=siblings[i - 1].title)
            if i < total - 1:
                next_ref = ChallengeNavRef(slug=siblings[i + 1].slug, title=siblings[i + 1].title)
            break

    return ChallengeDetail(
        id=challenge.id,
        slug=challenge.slug,
        title=challenge.title,
        order_index=challenge.order_index,
        is_free=challenge.is_free,
        skills=challenge.skills,
        module_id=challenge.module_id,
        scenario=challenge.scenario,
        learner_goal=challenge.learner_goal,
        instructions=challenge.instructions,
        repo_template_url=challenge.repo_template_url,
        repo_branch=challenge.repo_branch,
        validation_config_json=challenge.validation_config_json,
        ai_rules_json=challenge.ai_rules_json,
        module=ModuleOut.model_validate(module),
        previous=previous_ref,
        next=next_ref,
        position_in_track=position,
        total_in_track=max(total, 1),
    )


@router.post("/{slug}/start", response_model=ProgressOut)
def start_challenge(
    slug: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> ProgressOut:
    challenge = db.scalar(select(Challenge).where(Challenge.slug == slug))
    if not challenge:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")
    ensure_can_access(db, user.id, challenge)

    existing = db.scalar(
        select(UserChallengeProgress).where(
            UserChallengeProgress.user_id == user.id,
            UserChallengeProgress.challenge_id == challenge.id,
        )
    )
    if existing:
        if existing.status == "not_started":
            existing.status = "in_progress"
            existing.started_at = datetime.now(UTC)
            db.commit()
            db.refresh(existing)
        return ProgressOut.model_validate(existing)

    progress = UserChallengeProgress(
        user_id=user.id,
        challenge_id=challenge.id,
        status="in_progress",
        started_at=datetime.now(UTC),
        attempts_count=0,
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return ProgressOut.model_validate(progress)
