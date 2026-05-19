from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Challenge, Module, Track
from app.schemas import ChallengeSummary, ModuleOut, TrackDetail, TrackOut

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackOut])
def list_tracks(db: Session = Depends(get_db)) -> list[Track]:
    return list(db.scalars(select(Track).where(Track.is_published.is_(True))).all())


@router.get("/{slug}", response_model=TrackDetail)
def get_track(slug: str, db: Session = Depends(get_db)) -> TrackDetail:
    track = db.scalar(select(Track).where(Track.slug == slug, Track.is_published.is_(True)))
    if not track:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Track not found")

    modules = list(
        db.scalars(select(Module).where(Module.track_id == track.id).order_by(Module.order_index)).all()
    )
    module_ids = [m.id for m in modules]
    challenges = (
        list(
            db.scalars(
                select(Challenge)
                .where(Challenge.module_id.in_(module_ids))
                .order_by(Challenge.order_index)
            ).all()
        )
        if module_ids
        else []
    )

    return TrackDetail(
        id=track.id,
        slug=track.slug,
        title=track.title,
        description=track.description,
        difficulty=track.difficulty,
        modules=[ModuleOut.model_validate(m) for m in modules],
        challenges=[ChallengeSummary.model_validate(c) for c in challenges],
    )
