"""Socratic mentor chat — OpenAI calls + hint-level enforcement.

Levels (from plans/04_AI_MENTOR_AND_VALIDATION.md):
  1 → Socratic only. Ask one diagnostic question, no concrete next step.
  2 → Diagnostic + a concrete next step + file/function pointer if possible.
  3 → Add a pseudocode sketch. Final code only if attempts_count >= 3.

Mental Models track adds two non-task mentor modes:

  socratic_teach → used during a concept's Read + Try stages. Teaches the
    concept itself. Never refers to the Apply task or to concept slugs the
    learner has not yet completed.
  reflect_grade → used during a concept's Reflect stage. Grades the
    learner's two-sentence explanation against the per-concept rubric
    and returns structured {verdict, follow_up, rubric_hits}.

Every concept-mode call now sanitises the output via `_strip_forward_refs`
so the mentor cannot accidentally name a concept the learner hasn't
mastered yet (Exercism's mentor constraint).
"""

from __future__ import annotations

import json
import re
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
    # "python" (default), "c", or None. Drives a runtime-specific addendum
    # so the mentor doesn't suggest unsupported features for the lesson's
    # in-browser sandbox (e.g. <pthread.h> in JSCPP, file I/O, etc.).
    language: str | None = None


# Mentor system-prompt addenda per in-browser runtime. Kept terse — they
# ride alongside the main socratic-hint prompt every C lesson.
_LANGUAGE_ADDENDA = {
    "c": (
        "Runtime context: this learner's code runs in a small in-browser C "
        "interpreter (picoc compiled to WASM). It supports stdio (printf, basic "
        "scanf), control flow, arrays, pointers, structs, malloc/free, function "
        "pointers, and the essentials of <math.h>, <string.h>, <stdlib.h>. It "
        "does NOT support: threads (<pthread.h>), file I/O beyond stdin/stdout, "
        "<unistd.h>, <signal.h>, system calls, or deep recursion (small "
        "interpreter stack — prefer iteration). Never suggest these. The error "
        "format the learner sees is 'line LINE:COL <message>' — refer to that "
        "directly when diagnosing."
    ),
}


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
    language_note = (
        f"\n\n{_LANGUAGE_ADDENDA[context.language]}"
        if context.language and context.language in _LANGUAGE_ADDENDA
        else ""
    )
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
        f"{language_note}"
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


# ============================================================================
# Concept-mode mentor — Mental Models track (CC.1)
# ============================================================================


@dataclass(frozen=True)
class ConceptContext:
    """Context for a non-task mentor call inside a concept UNIT.

    The mentor receives the concept's identity + Read content + the learner's
    Try attempt (if any). It NEVER receives an Apply task / test output —
    those belong to the task-hint flow.

    concepts_mastered enforces the no-forward-reference rule: the mentor's
    output is scanned for any concept slug not in this list, and those
    references are stripped before returning.
    """

    slug: str
    title: str
    one_line: str
    exposition_md: str
    worked_example_md: str
    try_attempt_text: str | None
    concepts_mastered: tuple[str, ...]
    # The full set of concept slugs in the system. Used to detect
    # forward-reference attempts (mentions of valid slugs the learner
    # hasn't completed).
    all_concept_slugs: tuple[str, ...]


def _strip_forward_refs(
    text: str,
    mastered: tuple[str, ...],
    all_concepts: tuple[str, ...],
) -> tuple[str, list[str]]:
    """Remove mentions of unmastered concept slugs.

    Returns (sanitised_text, removed_slugs). A removed mention is replaced
    with the slug's title-cased phrase ("call-stack-tree" → "the call stack
    tree") so the prose stays readable, but the formal concept name is
    elided. This is the Exercism mentor constraint applied as a hard
    post-generation guard.
    """
    forbidden = {s for s in all_concepts if s not in set(mastered)}
    removed: list[str] = []
    sanitised = text
    for slug in forbidden:
        # Match the slug as a discrete token (kebab-case or quoted/backticked).
        # Conservative: only strip exact slug forms; don't mangle prose that
        # happens to share words.
        slug_re = re.compile(rf"`?\b{re.escape(slug)}\b`?", re.IGNORECASE)
        if slug_re.search(sanitised):
            removed.append(slug)
            replacement = slug.replace("-", " ")
            sanitised = slug_re.sub(replacement, sanitised)
    return sanitised, removed


def _concept_context_block(ctx: ConceptContext) -> str:
    try_note = (
        f"Learner's Try attempt (their guess BEFORE instruction):\n"
        f"{ctx.try_attempt_text}\n"
        if ctx.try_attempt_text
        else "Learner did not record a Try attempt.\n"
    )
    mastered_note = (
        f"Concepts the learner has completed (safe to reference):\n"
        f"{', '.join(ctx.concepts_mastered) or '(none yet)'}\n\n"
        "If a relevant concept is not in this list, paraphrase its meaning "
        "instead of naming the slug."
    )
    return (
        f"Concept under study: {ctx.title} ({ctx.slug})\n"
        f"One-liner: {ctx.one_line}\n\n"
        f"Read-stage exposition:\n{ctx.exposition_md}\n\n"
        f"Worked example:\n{ctx.worked_example_md}\n\n"
        f"{try_note}\n"
        f"{mastered_note}"
    )


def socratic_teach(
    context: ConceptContext,
    history: list[dict[str, str]],
    user_message: str,
) -> tuple[str, dict]:
    """Concept-mode teaching call. Used in Read + Try stages.

    Returns (assistant_text, metadata). The assistant_text is post-processed
    to strip references to unmastered concept slugs (Exercism constraint).
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    system_prompt = get_prompt_with_guardrail("socratic-teach-prompt")
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": _concept_context_block(context)},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        model=settings.openai_model_chat,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.4,
    )
    raw = completion.choices[0].message.content or ""
    sanitised, removed_refs = _strip_forward_refs(
        raw, context.concepts_mastered, context.all_concept_slugs
    )
    metadata = {
        "model": completion.model,
        "usage": completion.usage.model_dump() if completion.usage else None,
        "prompt_sha": get_prompt_sha(),
        "mode": "socratic_teach",
        "concept_slug": context.slug,
        "removed_forward_refs": removed_refs,
    }
    return sanitised, metadata


@dataclass(frozen=True)
class ReflectGrade:
    """Structured output from reflect_grade."""

    verdict: str  # "complete" | "shallow"
    follow_up: str | None
    rubric_hits: dict
    raw: str  # the original model output, for debugging


# Reflect is a self-explanation exercise (research basis: self-explanation
# effect). The cognitive work happens in WRITING the answer; precise rubric
# match is not the point. A deterministic length-gate ensures any genuine
# attempt passes the stage — the LLM's text becomes optional context, not a
# gate. Anything shorter than this is too short to count as reflection.
_REFLECT_MIN_CHARS = 80


def reflect_grade(
    context: ConceptContext,
    rubric: dict,
    learner_explanation: str,
) -> tuple[ReflectGrade, dict]:
    """Grade a Reflect-stage answer.

    Pass policy: a non-trivial attempt (≥ 80 chars) passes the stage
    deterministically. The LLM is consulted for praise / one optional
    probing question (shown to the learner as feedback), but it never
    gates progression. Trivially short answers ("hi", "idk") get an
    immediate 'shallow' verdict without an LLM call.

    Returns (grade, metadata). On any LLM error the grade falls back to
    'complete' with no follow-up — Reflect must not block the learner.
    """
    # Deterministic short-circuit: trivially short = shallow with a nudge.
    # This path runs without an API key — it costs nothing and shouldn't
    # depend on OpenAI configuration.
    cleaned = (learner_explanation or "").strip()
    if len(cleaned) < _REFLECT_MIN_CHARS:
        return (
            ReflectGrade(
                verdict="shallow",
                follow_up=(
                    "That feels too short to be a real reflection — give it "
                    "two full sentences in your own words. What's the "
                    "mechanism, and why does it matter?"
                ),
                rubric_hits={},
                raw="(length-gate: too short)",
            ),
            {
                "model": "deterministic",
                "usage": None,
                "prompt_sha": get_prompt_sha(),
                "mode": "reflect_grade",
                "concept_slug": context.slug,
                "length_gate": "too_short",
            },
        )

    # Past the length gate — we'll call OpenAI for feedback. Verify the key.
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    system_prompt = get_prompt_with_guardrail("reflect-grade-prompt")
    context_block = (
        f"Concept: {context.title} ({context.slug})\n"
        f"One-liner: {context.one_line}\n\n"
        f"Rubric:\n{json.dumps(rubric, indent=2)}\n\n"
        f"Learner's explanation:\n{learner_explanation}\n\n"
        f"Concepts the learner has completed: "
        f"{', '.join(context.concepts_mastered) or '(none yet)'}\n"
        "Do not name unmastered concepts in your follow_up."
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context_block},
    ]

    client = OpenAI(api_key=settings.openai_api_key)
    # Reflect grading is a judgement call across a few lines of prose; use
    # the stronger model (same one PR review uses). The lighter `gpt-4o-mini`
    # tended to read the rubric as a literal checklist and mark almost any
    # paraphrased two-sentence answer "shallow".
    completion = client.chat.completions.create(
        model=settings.openai_model_review,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
        follow_up_raw = parsed.get("follow_up")
        if follow_up_raw:
            follow_up_sanitised, _ = _strip_forward_refs(
                follow_up_raw,
                context.concepts_mastered,
                context.all_concept_slugs,
            )
        else:
            follow_up_sanitised = None
        # The length gate has already decided: this is a pass. The LLM's
        # opinion is treated as optional feedback. Verdict is fixed to
        # 'complete' so the stage actually advances.
        grade = ReflectGrade(
            verdict="complete",
            follow_up=follow_up_sanitised,
            rubric_hits=parsed.get("rubric_hits", {}),
            raw=raw,
        )
    except (json.JSONDecodeError, AttributeError):
        # Never block the learner on an LLM parse error — they wrote ≥ 80
        # chars, they pass.
        grade = ReflectGrade(
            verdict="complete",
            follow_up=None,
            rubric_hits={},
            raw=raw,
        )

    metadata = {
        "model": completion.model,
        "usage": completion.usage.model_dump() if completion.usage else None,
        "prompt_sha": get_prompt_sha(),
        "mode": "reflect_grade",
        "concept_slug": context.slug,
    }
    return grade, metadata
