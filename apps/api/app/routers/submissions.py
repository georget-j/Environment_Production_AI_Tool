from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.review import ReviewInput, review
from app.auth import AuthUser, get_current_user
from app.db import get_db
from app.models import Challenge, Submission, UserChallengeProgress
from app.validation import parse_pytest_output

router = APIRouter(prefix="/api", tags=["submissions"])

_REPO_URL_RE = re.compile(
    r"^https?://[a-zA-Z0-9.\-]+/[\w\-./]+?(?:\.git)?/?$"
)
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


class SubmissionCreate(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=500)
    commit_sha: str | None = None
    test_output: str | None = None
    lint_output: str | None = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    repo_url: str
    commit_sha: str | None
    passed: bool
    test_output: str | None
    lint_output: str | None
    ai_review_json: dict
    created_at: datetime


@router.post("/challenges/{slug}/submit", response_model=SubmissionOut)
def submit_challenge(
    slug: str,
    body: SubmissionCreate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> SubmissionOut:
    if not _REPO_URL_RE.match(body.repo_url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "repo_url must be an http(s) URL")
    if body.commit_sha and not _SHA_RE.match(body.commit_sha):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "commit_sha must be 7-40 hex chars")

    challenge = db.scalar(select(Challenge).where(Challenge.slug == slug))
    if not challenge:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Challenge not found")

    summary = parse_pytest_output(body.test_output)

    submission = Submission(
        user_id=user.id,
        challenge_id=challenge.id,
        repo_url=body.repo_url,
        commit_sha=body.commit_sha,
        test_output=body.test_output,
        lint_output=body.lint_output,
        passed=summary.passed,
        ai_review_json={},
    )
    db.add(submission)

    # Bump attempts and mark complete on first pass.
    progress = db.scalar(
        select(UserChallengeProgress).where(
            UserChallengeProgress.user_id == user.id,
            UserChallengeProgress.challenge_id == challenge.id,
        )
    )
    if progress is None:
        progress = UserChallengeProgress(
            user_id=user.id,
            challenge_id=challenge.id,
            status="in_progress",
            started_at=datetime.now(UTC),
            attempts_count=0,
        )
        db.add(progress)

    progress.attempts_count += 1
    if summary.passed and progress.status != "completed":
        progress.status = "completed"
        progress.completed_at = datetime.now(UTC)

    db.commit()
    db.refresh(submission)

    # Run the AI PR review synchronously. If OpenAI is unconfigured or the call
    # fails, persist an empty review_json and let the UI render the failure mode.
    try:
        review_json, metadata = review(
            ReviewInput(
                title=challenge.title,
                scenario=challenge.scenario,
                learner_goal=challenge.learner_goal,
                skills=challenge.skills,
                repo_url=submission.repo_url,
                commit_sha=submission.commit_sha,
                test_output=submission.test_output,
                tests_passed=summary.passed,
            )
        )
        submission.ai_review_json = review_json
        submission.prompt_sha = metadata["prompt_sha"]
        db.commit()
        db.refresh(submission)
    except Exception as exc:
        submission.ai_review_json = {"error": str(exc)[:300]}
        db.commit()
        db.refresh(submission)

    return SubmissionOut.model_validate(submission)


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: UUID,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> SubmissionOut:
    submission = db.get(Submission, submission_id)
    if submission is None or submission.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    return SubmissionOut.model_validate(submission)
