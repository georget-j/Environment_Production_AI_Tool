"""Generate the working version of a learner's editable files.

Used by POST /api/ai/show-answer. Sends the challenge context, the
editable + read-only file snapshot, and the latest pytest output (if
any) to OpenAI with a strict JSON schema. The frontend overwrites the
learner's editor with whatever this returns, so the schema is locked
down: one entry per editable file with the entire file contents.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.ai.prompts import get_prompt_sha, get_prompt_with_guardrail
from app.config import get_settings

ANSWER_SCHEMA: dict[str, Any] = {
    "name": "challenge_answer",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["fixed_files", "summary"],
        "properties": {
            "fixed_files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "content"],
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            },
            "summary": {"type": "string"},
        },
    },
    "strict": True,
}


@dataclass(frozen=True)
class AnswerInput:
    challenge_title: str
    scenario: str
    learner_goal: str
    editable_files: dict[str, str]
    readonly_files: dict[str, str]
    test_output: str | None


def answer(payload: AnswerInput) -> tuple[dict, dict]:
    """Call OpenAI; return (payload_json, metadata)."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    system_prompt = get_prompt_with_guardrail("show-answer-prompt")

    def _section(name: str, files: dict[str, str], cap: int) -> str:
        if not files:
            return f"### {name}\n(none)"
        blocks = "\n\n".join(
            f"#### {path}\n```\n{(body or '')[:cap]}\n```" for path, body in files.items()
        )
        return f"### {name}\n{blocks}"

    editable_section = _section(
        "Editable files (return one fixed entry per file here)",
        payload.editable_files,
        6000,
    )
    readonly_section = _section("Read-only context files", payload.readonly_files, 4000)
    test_output = (payload.test_output or "")[-3000:]

    user_block = (
        f"Challenge: {payload.challenge_title}\n\n"
        f"Scenario:\n{payload.scenario}\n\n"
        f"Goal:\n{payload.learner_goal}\n\n"
        f"---\n{editable_section}\n\n"
        f"---\n{readonly_section}\n\n"
        f"---\n"
        f"Latest pytest output (may be empty):\n```\n{test_output}\n```"
    )

    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        # The review model is the larger one; show-answer needs accuracy more
        # than throughput, so reuse it rather than the chat model.
        model=settings.openai_model_review,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_block},
        ],
        response_format={"type": "json_schema", "json_schema": ANSWER_SCHEMA},
        temperature=0.1,
    )
    raw = completion.choices[0].message.content or "{}"
    parsed = json.loads(raw)

    # Guard rail: only return files the learner could actually edit. Drop
    # anything else the model invented.
    allowed = set(payload.editable_files.keys())
    parsed["fixed_files"] = [
        f for f in parsed.get("fixed_files", []) if f.get("path") in allowed
    ]

    metadata = {
        "model": completion.model,
        "usage": completion.usage.model_dump() if completion.usage else None,
        "prompt_sha": get_prompt_sha(),
    }
    return parsed, metadata
