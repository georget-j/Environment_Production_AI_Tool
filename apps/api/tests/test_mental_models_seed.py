"""Static guards for `scripts/generate_mental_models.py` (M0 — non-destructive seed).

The seed is re-run every content tweak. v2 requires it to PRESERVE every
learner's `concept_mastery` row. These tests are the bright-line check
that we never regress the seed's idempotency guarantees:

  - The generated SQL must NOT contain `delete from public.concept_mastery`
    anywhere — touching that table on re-seed wipes user progress.
  - Concept inserts must use `on conflict (slug) do update set` so
    re-running the seed updates rows in place.
  - The generator must be deterministic — running it twice must produce
    byte-identical output. (Catches accidental ordering by dict-iteration
    or unstable sort.)
  - The prereq wipe must be scoped to the concepts the generator owns
    (not a blanket `delete from public.concept_prereqs`) so future
    concept-based tracks don't get their edges nuked when Mental Models
    re-seeds.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATOR = REPO_ROOT / "scripts" / "generate_mental_models.py"
SEED_PATH = REPO_ROOT / "supabase" / "mental_models_seed.generated.sql"


def _run_generator() -> str:
    """Run the generator, return the produced SQL file contents."""
    result = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    # Generator writes "wrote ..." lines to stdout, not the SQL itself.
    assert "wrote" in result.stdout, result.stdout
    return SEED_PATH.read_text(encoding="utf-8")


def test_seed_does_not_touch_concept_mastery() -> None:
    """The most important guard. concept_mastery holds learner progress."""
    sql = _run_generator()
    # Case-insensitive search — Postgres SQL is case-insensitive on
    # keywords, and an author could write `DELETE FROM` mid-refactor.
    forbidden = re.compile(
        r"\b(delete\s+from|truncate)\b[^;]*\bconcept_mastery\b",
        re.IGNORECASE,
    )
    matches = forbidden.findall(sql)
    assert not matches, (
        "Seed must NEVER delete or truncate concept_mastery — that's "
        "every learner's progress. Found: " + repr(matches)
    )


def test_concepts_use_on_conflict_upsert() -> None:
    """Concept rows must UPSERT by slug, not delete + reinsert."""
    sql = _run_generator()
    # There are 7 concepts; each must have its own ON CONFLICT clause.
    upsert_count = len(
        re.findall(r"on conflict \(slug\) do update set", sql, re.IGNORECASE)
    )
    # Tracks also use `on conflict (slug)` → expect 1 + 1 per concept.
    assert upsert_count >= 8, (
        f"Expected ≥ 8 `on conflict (slug) do update set` clauses "
        f"(1 for tracks + 1 per concept). Got {upsert_count}."
    )


def test_no_blanket_concept_delete() -> None:
    """A bare `delete from public.concepts;` would nuke other tracks'
    concepts. The seed must scope deletes by slug, or skip them entirely
    (the upsert pattern doesn't need a delete at all)."""
    sql = _run_generator()
    blanket = re.compile(
        r"\bdelete\s+from\s+public\.concepts\b\s*;",
        re.IGNORECASE,
    )
    matches = blanket.findall(sql)
    assert not matches, (
        "Seed must not unconditionally delete public.concepts. "
        "Use UPSERT by slug instead. Found: " + repr(matches)
    )


def test_prereq_wipe_is_slug_scoped() -> None:
    """Wiping concept_prereqs is fine — but the WHERE clause must scope
    to the concepts we own, not every concept in the DB. Otherwise
    future concept-based tracks lose their prereq graphs when Mental
    Models re-seeds."""
    sql = _run_generator()
    # Locate the concept_prereqs delete; verify it has a slug-scoped subquery.
    delete_lines = re.findall(
        r"delete\s+from\s+public\.concept_prereqs[^;]*;",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert len(delete_lines) >= 1, "Expected at least one concept_prereqs wipe."
    for line in delete_lines:
        assert "slug in (" in line.lower(), (
            "concept_prereqs delete must be scoped to a slug IN (...) list. "
            f"Got: {line!r}"
        )


def test_generator_is_deterministic() -> None:
    """Running the generator twice in a row must produce byte-identical
    output — otherwise re-runs cause noisy diffs and unpredictable
    UPSERTs against prod."""
    first = _run_generator()
    second = _run_generator()
    assert first == second, (
        "Generator output drifted between two consecutive runs. "
        "Check for dict-iteration ordering or unstable sorts."
    )
