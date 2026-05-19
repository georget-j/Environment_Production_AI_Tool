"""Plain-English explanation of pytest failures.

Used by POST /api/ai/explain-tests. Sends the pytest output, the
challenge context, and the learner's current source to OpenAI with a
strict JSON schema. The mentor never returns code; it tells the learner
what failed and where to look.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.ai.prompts import get_prompt, get_prompt_sha
from app.config import get_settings

EXPLAIN_SCHEMA: dict[str, Any] = {
    "name": "test_failure_explanation",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["failures"],
        "properties": {
            "failures": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["test_name", "what_was_checked", "what_happened", "where_to_look"],
                    "properties": {
                        "test_name": {"type": "string"},
                        "what_was_checked": {"type": "string"},
                        "what_happened": {"type": "string"},
                        "where_to_look": {"type": "string"},
                    },
                },
            }
        },
    },
    "strict": True,
}


@dataclass(frozen=True)
class ExplainInput:
    challenge_title: str
    scenario: str
    learner_goal: str
    test_output: str
    files: dict[str, str]


def explain(payload: ExplainInput) -> tuple[dict, dict]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    system_prompt = get_prompt("test-failure-explainer-prompt")

    # Cap each file at 4000 chars so we don't blow the context window.
    file_block = "\n\n".join(
        f"### {path}\n```\n{(body or '')[:4000]}\n```" for path, body in payload.files.items()
    )

    user_block = (
        f"Challenge: {payload.challenge_title}\n\n"
        f"Scenario:\n{payload.scenario}\n\n"
        f"Goal:\n{payload.learner_goal}\n\n"
        f"---\n"
        f"Learner's current files:\n{file_block}\n\n"
        f"---\n"
        f"pytest output (last 4000 chars):\n```\n{payload.test_output[-4000:]}\n```"
    )

    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        model=settings.openai_model_chat,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_block},
        ],
        response_format={"type": "json_schema", "json_schema": EXPLAIN_SCHEMA},
        temperature=0.2,
    )
    raw = completion.choices[0].message.content or "{}"
    parsed = json.loads(raw)
    metadata = {
        "model": completion.model,
        "usage": completion.usage.model_dump() if completion.usage else None,
        "prompt_sha": get_prompt_sha(),
    }
    return parsed, metadata
