"""User-scoped aggregates: progress across tracks for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import (
    Challenge,
    Concept,
    ConceptMastery,
    Module,
    Track,
    UserChallengeProgress,
)
from app.schemas import (
    ContinueRef,
    MeProgressOut,
    TrackProgressDetail,
    TrackProgressOut,
)

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/progress", response_model=MeProgressOut)
def get_my_progress(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> MeProgressOut:
    """Aggregate the learner's progress across every published track.

    Returns one TrackProgressOut per track with completed/total counts and
    the slug of the most-recently-started lesson that isn't yet completed
    (so the per-track 'Continue' button can deep-link to it). Also returns
    a single overall ContinueRef pointing at the most-recently-started
    in-progress lesson across all tracks, used by the dashboard's hero
    'Resume' card.
    """
    tracks = list(
        db.scalars(
            select(Track).where(Track.is_published.is_(True)).order_by(Track.title)
        ).all()
    )
    if not tracks:
        return MeProgressOut(tracks=[], continue_lesson=None)

    track_ids = [t.id for t in tracks]
    modules = list(
        db.scalars(select(Module).where(Module.track_id.in_(track_ids))).all()
    )
    module_id_to_track_id = {m.id: m.track_id for m in modules}
    module_id_to_title = {m.id: m.title for m in modules}
    module_ids = list(module_id_to_track_id.keys())

    challenges = list(
        db.scalars(
            select(Challenge)
            .where(Challenge.module_id.in_(module_ids))
            .order_by(Challenge.order_index)
        ).all()
    ) if module_ids else []

    # Build ordered list of challenges per track (used to derive
    # 1-based position within the track for the Continue card).
    challenges_by_track: dict[str, list[Challenge]] = {t.slug: [] for t in tracks}
    challenge_id_to_track_slug: dict = {}
    for c in challenges:
        track_id = module_id_to_track_id.get(c.module_id)
        if track_id is None:
            continue
        track_slug = next((t.slug for t in tracks if t.id == track_id), None)
        if track_slug is None:
            continue
        challenges_by_track[track_slug].append(c)
        challenge_id_to_track_slug[c.id] = track_slug

    # Pull the user's progress for these challenges (single query).
    challenge_ids = [c.id for c in challenges]
    progress_rows = (
        list(
            db.scalars(
                select(UserChallengeProgress).where(
                    UserChallengeProgress.user_id == user.id,
                    UserChallengeProgress.challenge_id.in_(challenge_ids),
                )
            ).all()
        )
        if challenge_ids
        else []
    )
    progress_by_challenge = {p.challenge_id: p for p in progress_rows}

    # M5 — concept-mastery rollup per concept-based track. Today only the
    # Mental Models track has concepts; the per-track topic_slug column ties
    # a concept to a track (topic == track-shape mental-models).
    concept_total_by_track: dict[str, int] = {}
    concept_done_by_track: dict[str, int] = {}
    concept_in_progress_by_track: dict[str, str | None] = {}
    concept_rows = list(
        db.scalars(
            select(Concept).order_by(Concept.layer, Concept.order_index)
        ).all()
    )
    # Map topic_slug → track slug. Universal-layer concepts are shared so
    # they're attributed to every concept-based track. For the pilot, only
    # Mental Models is concept-based; the universal concepts also count
    # toward its progress.
    concept_track_slugs: set[str] = {
        t.slug for t in tracks if t.slug == "mental-models"
    }
    for slug in concept_track_slugs:
        concept_total_by_track[slug] = 0
        concept_done_by_track[slug] = 0
        concept_in_progress_by_track[slug] = None
    # Build per-track concept index. A concept counts toward a track if
    # its topic_slug == track slug OR layer == universal (foundation concepts
    # belong to every concept-based track for now).
    concepts_by_track: dict[str, list[Concept]] = {
        slug: [] for slug in concept_track_slugs
    }
    for c in concept_rows:
        for slug in concept_track_slugs:
            if c.topic_slug == slug or c.layer == "universal":
                concepts_by_track[slug].append(c)

    if concept_track_slugs and concept_rows:
        mastery_rows = list(
            db.scalars(
                select(ConceptMastery).where(ConceptMastery.user_id == user.id)
            ).all()
        )
        mastery_by_concept_id = {m.concept_id: m for m in mastery_rows}
        for slug, slugs_concepts in concepts_by_track.items():
            done = 0
            latest_in_progress: tuple = ()
            for c in slugs_concepts:
                concept_total_by_track[slug] += 1
                m = mastery_by_concept_id.get(c.id)
                if m is None:
                    continue
                if m.mastered_at is not None:
                    done += 1
                else:
                    # Treat any started-but-not-mastered concept as in-progress.
                    started = m.try_attempted_at or m.read_completed_at
                    if started is not None and (
                        not latest_in_progress or started > latest_in_progress[0]
                    ):
                        latest_in_progress = (started, c.slug)
            concept_done_by_track[slug] = done
            concept_in_progress_by_track[slug] = (
                latest_in_progress[1] if latest_in_progress else None
            )

    # Walk each track and tally.
    track_out: list[TrackProgressOut] = []
    overall_best: tuple = ()  # (started_at, track_slug, challenge_slug) — most recent in-progress
    overall_continue: ContinueRef | None = None
    for t in tracks:
        track_challenges = challenges_by_track.get(t.slug, [])
        completed = 0
        latest_in_progress: Challenge | None = None
        latest_in_progress_started = None
        for c in track_challenges:
            p = progress_by_challenge.get(c.id)
            if p is None:
                continue
            if p.status == "completed":
                completed += 1
            elif p.status == "in_progress":
                started = p.started_at
                if started is not None and (
                    latest_in_progress_started is None
                    or started > latest_in_progress_started
                ):
                    latest_in_progress = c
                    latest_in_progress_started = started
        # For concept-based tracks (no challenges), surface concept-mastery
        # counts via the standard completed/total so the existing dashboard
        # progress bar renders without bespoke wiring.
        challenge_total = len(track_challenges)
        if challenge_total == 0 and t.slug in concept_total_by_track:
            display_total = concept_total_by_track[t.slug]
            display_completed = concept_done_by_track[t.slug]
            display_in_progress = concept_in_progress_by_track[t.slug]
        else:
            display_total = challenge_total
            display_completed = completed
            display_in_progress = (
                latest_in_progress.slug if latest_in_progress else None
            )
        track_out.append(
            TrackProgressOut(
                slug=t.slug,
                title=t.title,
                description=t.description,
                difficulty=t.difficulty,
                completed=display_completed,
                total=display_total,
                latest_in_progress_slug=display_in_progress,
                concept_completed=concept_done_by_track.get(t.slug, 0),
                concept_total=concept_total_by_track.get(t.slug, 0),
            )
        )
        if latest_in_progress is not None and latest_in_progress_started is not None:
            if not overall_best or latest_in_progress_started > overall_best[0]:
                position = next(
                    (i + 1 for i, c in enumerate(track_challenges) if c.id == latest_in_progress.id),
                    1,
                )
                overall_best = (latest_in_progress_started, t.slug, latest_in_progress.slug)
                overall_continue = ContinueRef(
                    track_slug=t.slug,
                    track_title=t.title,
                    module_title=module_id_to_title.get(latest_in_progress.module_id, ""),
                    challenge_slug=latest_in_progress.slug,
                    challenge_title=latest_in_progress.title,
                    position=position,
                    total=len(track_challenges),
                )

    return MeProgressOut(tracks=track_out, continue_lesson=overall_continue)


@router.get("/track/{slug}/progress", response_model=TrackProgressDetail)
def get_track_progress(
    slug: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> TrackProgressDetail:
    """Per-challenge progress for a single track. Used by the track-detail
    page to mark lessons done/current/not-yet and surface 'Jump to next
    unsolved'.
    """
    track = db.scalar(
        select(Track).where(Track.slug == slug, Track.is_published.is_(True))
    )
    if track is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Track not found")

    modules = list(
        db.scalars(
            select(Module)
            .where(Module.track_id == track.id)
            .order_by(Module.order_index)
        ).all()
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

    progress_rows = (
        list(
            db.scalars(
                select(UserChallengeProgress).where(
                    UserChallengeProgress.user_id == user.id,
                    UserChallengeProgress.challenge_id.in_([c.id for c in challenges]),
                )
            ).all()
        )
        if challenges
        else []
    )
    status_by_challenge = {p.challenge_id: p.status for p in progress_rows}

    completed_slugs: list[str] = []
    in_progress_slugs: list[str] = []
    next_unsolved_slug: str | None = None
    module_progress: dict[str, dict[str, int]] = {
        str(m.id): {"completed": 0, "total": 0} for m in modules
    }

    for c in challenges:
        mod_key = str(c.module_id)
        module_progress.setdefault(mod_key, {"completed": 0, "total": 0})
        module_progress[mod_key]["total"] += 1
        st = status_by_challenge.get(c.id)
        if st == "completed":
            completed_slugs.append(c.slug)
            module_progress[mod_key]["completed"] += 1
        else:
            if st == "in_progress":
                in_progress_slugs.append(c.slug)
            if next_unsolved_slug is None:
                next_unsolved_slug = c.slug

    return TrackProgressDetail(
        completed_slugs=completed_slugs,
        in_progress_slugs=in_progress_slugs,
        next_unsolved_slug=next_unsolved_slug,
        completed=len(completed_slugs),
        total=len(challenges),
        module_progress=module_progress,
    )
