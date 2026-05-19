from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import Challenge, Module, UserChallengeProgress
from app.schemas import ChallengeDetail, ModuleOut, ProgressOut

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.get("/{slug}", response_model=ChallengeDetail)
def get_challenge(slug: str, db: Session = Depends(get_db)) -> ChallengeDetail:
    challenge = db.scalar(select(Challenge).where(Challenge.slug == slug))
    if not challenge:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")
    module = db.get(Module, challenge.module_id)
    if module is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Challenge has no module")
    return ChallengeDetail(
        id=challenge.id,
        slug=challenge.slug,
        title=challenge.title,
        order_index=challenge.order_index,
        is_free=challenge.is_free,
        skills=challenge.skills,
        scenario=challenge.scenario,
        learner_goal=challenge.learner_goal,
        instructions=challenge.instructions,
        repo_template_url=challenge.repo_template_url,
        repo_branch=challenge.repo_branch,
        validation_config_json=challenge.validation_config_json,
        ai_rules_json=challenge.ai_rules_json,
        module=ModuleOut.model_validate(module),
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
