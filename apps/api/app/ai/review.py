"""Structured PR review.

OpenAI structured outputs: we send the JSON Schema below; the model is
constrained to return matching JSON. Keep this schema in lockstep with
packages/shared/src/review.ts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.ai.prompts import get_prompt, get_prompt_sha
from app.config import get_settings

PR_REVIEW_SCHEMA: dict[str, Any] = {
    "name": "pr_review",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "passed",
            "score",
            "summary",
            "strengths",
            "issues",
            "required_fixes",
            "skills_practiced",
            "next_recommended_challenge",
        ],
        "properties": {
            "passed": {"type": "boolean"},
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["severity", "title", "suggestion"],
                    "properties": {
                        "severity": {"enum": ["minor", "major", "critical"]},
                        "title": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                },
            },
            "required_fixes": {"type": "array", "items": {"type": "string"}},
            "skills_practiced": {"type": "array", "items": {"type": "string"}},
            "next_recommended_challenge": {"type": ["string", "null"]},
        },
    },
    "strict": True,
}


@dataclass(frozen=True)
class ReviewInput:
    title: str
    scenario: str
    learner_goal: str
    skills: list[str]
    repo_url: str
    commit_sha: str | None
    test_output: str | None
    tests_passed: bool


def review(submission: ReviewInput) -> tuple[dict, dict]:
    """Call OpenAI; return (review_json, metadata)."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    system_prompt = get_prompt("pr-reviewer-prompt")
    user_block = json.dumps(
        {
            "challenge": {
                "title": submission.title,
                "scenario": submission.scenario,
                "learner_goal": submission.learner_goal,
                "skills": submission.skills,
            },
            "submission": {
                "repo_url": submission.repo_url,
                "commit_sha": submission.commit_sha,
                "tests_passed": submission.tests_passed,
                "test_output_tail": (submission.test_output or "")[-3000:],
            },
        },
        indent=2,
    )

    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        model=settings.openai_model_review,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_block},
        ],
        response_format={"type": "json_schema", "json_schema": PR_REVIEW_SCHEMA},
        temperature=0.2,
    )
    raw = completion.choices[0].message.content or "{}"
    payload = json.loads(raw)
    metadata = {
        "model": completion.model,
        "usage": completion.usage.model_dump() if completion.usage else None,
        "prompt_sha": get_prompt_sha(),
    }
    return payload, metadata
