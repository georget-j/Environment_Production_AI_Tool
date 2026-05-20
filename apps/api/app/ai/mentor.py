"""Socratic mentor chat — OpenAI calls + hint-level enforcement.

Levels (from plans/04_AI_MENTOR_AND_VALIDATION.md):
  1 → Socratic only. Ask one diagnostic question, no concrete next step.
  2 → Diagnostic + a concrete next step + file/function pointer if possible.
  3 → Add a pseudocode sketch. Final code only if attempts_count >= 3.
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from app.ai.prompts import get_prompt_sha, get_prompt_with_guardrail
from app.config import get_settings

_HINT_INSTRUCTIONS = {
    1: (
        "HINT LEVEL 1 — Socratic only. "
        "Ask exactly one useful diagnostic question. Do not propose a fix. "
        "Encourage the learner to run tests or inspect logs."
    ),
    2: (
        "HINT LEVEL 2 — Diagnostic + a single concrete next step. "
        "You may name a file or function to inspect. Do NOT write code."
    ),
    3: (
        "HINT LEVEL 3 — Pseudocode. "
        "Sketch the shape of the fix in 3-5 lines of pseudocode. "
        "Write real code only if attempts_count >= 3."
    ),
}


@dataclass(frozen=True)
class ChallengeContext:
    title: str
    scenario: str
    learner_goal: str
    latest_test_output: str | None
    attempts_count: int
    # Snapshot of the learner's CURRENT editor contents, keyed by path. Sent
    # by the web client on every chat call so the mentor doesn't have to ask
    # the learner to paste their code.
    current_files: dict[str, str] | None = None


# Per-file content cap so a noisy lesson can't blow up the prompt.
_FILE_BYTE_CAP = 4000


def _render_current_files(files: dict[str, str] | None) -> str:
    if not files:
        return "(the learner's editor is empty or this lesson has no editable files)"
    parts: list[str] = []
    for path, body in files.items():
        snippet = (body or "")[:_FILE_BYTE_CAP]
        parts.append(f"--- {path} ---\n{snippet}")
    return "\n\n".join(parts)


def build_messages(
    context: ChallengeContext, history: list[dict[str, str]], user_message: str, hint_level: int
) -> list[dict[str, str]]:
    level = max(1, min(3, hint_level))
    system_prompt = get_prompt_with_guardrail("socratic-hint-prompt")
    context_block = (
        f"Challenge: {context.title}\n"
        f"Scenario: {context.scenario}\n"
        f"Goal: {context.learner_goal}\n"
        f"Attempt count: {context.attempts_count}\n\n"
        f"Learner's current editor contents:\n"
        f"{_render_current_files(context.current_files)}\n\n"
        f"Latest test output (last 2000 chars):\n"
        f"{(context.latest_test_output or '(none yet)')[-2000:]}\n\n"
        f"{_HINT_INSTRUCTIONS[level]}\n"
        f"Important: you ALREADY have the learner's current code above. "
        f"Never ask them to paste or share their code — refer to it directly."
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": context_block},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def chat(
    context: ChallengeContext,
    history: list[dict[str, str]],
    user_message: str,
    hint_level: int,
) -> tuple[str, dict]:
    """Call OpenAI; return (assistant_text, metadata)."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    messages = build_messages(context, history, user_message, hint_level)
    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        model=settings.openai_model_chat,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.4,
    )
    choice = completion.choices[0].message
    metadata = {
        "model": completion.model,
        "usage": completion.usage.model_dump() if completion.usage else None,
        "prompt_sha": get_prompt_sha(),
        "hint_level": hint_level,
    }
    return choice.content or "", metadata
