"""Prompt loader. The canonical text lives in prompts/AI_MENTOR_SYSTEM_PROMPTS.md.

Every AI response stores `prompt_sha` so we can correlate behavior with the
exact prompt text that produced it. Falls back to a content hash when git
isn't available (e.g. inside a Docker image).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from functools import lru_cache
from pathlib import Path

_PROMPTS_FILE = Path(__file__).resolve().parent / "system_prompts.md"
# Heading must fit on one line (`[^\n]+?`) so we never glom a body-less
# section into the next section's slug; body uses DOTALL so it can span
# multiple lines until the closing fence.
_SECTION_RE = re.compile(r"^##\s+([^\n]+?)\s*$\n+```text?\n(.*?)```", re.MULTILINE | re.DOTALL)


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, str], str]:
    text = _PROMPTS_FILE.read_text(encoding="utf-8")
    sections = {
        _slugify(name): body.strip() for name, body in _SECTION_RE.findall(text)
    }
    if not sections:
        raise RuntimeError(f"No prompt sections found in {_PROMPTS_FILE}")
    return sections, _resolve_sha(text)


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _resolve_sha(text: str) -> str:
    """Prefer the git blob SHA; fall back to a stable content hash."""
    try:
        result = subprocess.run(
            ["git", "hash-object", str(_PROMPTS_FILE)],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def get_prompt(slug: str) -> str:
    sections, _ = _load()
    if slug not in sections:
        raise KeyError(f"Unknown prompt section: {slug!r}. Available: {sorted(sections)}")
    return sections[slug]


def get_prompt_with_guardrail(slug: str) -> str:
    """Prepend the runtime guardrail to a learner-facing prompt.

    Use for the mentor, explainer, and show-answer prompts — anywhere we
    want the AI to obey the in-browser-sandbox constraints. The PR reviewer
    prompt uses get_prompt() directly because production-deployment talk is
    legitimate in that context.
    """
    guardrail = get_prompt("runtime-guardrail")
    body = get_prompt(slug)
    return f"{guardrail}\n\n{body}"


def get_prompt_sha() -> str:
    _, sha = _load()
    return sha
