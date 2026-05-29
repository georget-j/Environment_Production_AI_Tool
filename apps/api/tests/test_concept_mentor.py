"""Tests for the concept-mode mentor helpers (Phase CC.1).

The OpenAI clients (`socratic_teach`, `reflect_grade`) themselves require
a real API key, so they're not exercised here. We test the bits that run
purely in-process: the forward-reference sanitiser, which is the Exercism
constraint applied as a hard post-generation guard.
"""

from app.ai.mentor import ConceptContext, _strip_forward_refs, reflect_grade


ALL_CONCEPTS = (
    "variables-names",
    "references-values",
    "control-flow",
    "functions",
    "recursion",
    "complexity",
    "code-as-state-machine",
    "memory-model",
    "call-stack-tree",
    "causality-in-code",
)


def test_mastered_slug_is_kept() -> None:
    text = "You learned this in variables-names earlier today."
    out, removed = _strip_forward_refs(text, ("variables-names",), ALL_CONCEPTS)
    assert out == text
    assert removed == []


def test_unmastered_slug_is_humanised() -> None:
    # The learner has only mastered variables-names. The mentor must not
    # name `recursion` (which is a real concept slug) yet.
    text = "This is conceptually similar to recursion."
    out, removed = _strip_forward_refs(text, ("variables-names",), ALL_CONCEPTS)
    assert "recursion" in removed
    assert "recursion" in out  # the human phrase still reads naturally
    # But it should NOT appear in the original slug form as a distinct token.
    # Here "recursion" the WORD is fine — slug and word coincide. The next
    # test exercises a hyphenated slug where the distinction matters.


def test_unmastered_hyphenated_slug_is_humanised() -> None:
    text = "This builds on the call-stack-tree mental model."
    out, removed = _strip_forward_refs(text, ("variables-names",), ALL_CONCEPTS)
    assert "call-stack-tree" in removed
    assert "call-stack-tree" not in out  # original slug form gone
    assert "call stack tree" in out      # humanised form remains


def test_backticked_unmastered_slug_is_stripped() -> None:
    text = "Soon you'll meet `memory-model` — but not today."
    out, removed = _strip_forward_refs(text, (), ALL_CONCEPTS)
    assert "memory-model" in removed
    assert "`memory-model`" not in out
    assert "memory model" in out


def test_multiple_unmastered_slugs_each_handled() -> None:
    text = "Look at recursion and memory-model together."
    out, removed = _strip_forward_refs(text, (), ALL_CONCEPTS)
    assert set(removed) == {"recursion", "memory-model"}
    assert "memory-model" not in out


def test_case_insensitive_match_is_humanised() -> None:
    # Models occasionally capitalise concept slugs.
    text = "Coming up: Control-Flow. Stay tuned."
    out, removed = _strip_forward_refs(text, (), ALL_CONCEPTS)
    assert "control-flow" in removed
    assert "Control-Flow" not in out


def test_word_that_happens_to_share_letters_is_not_mangled() -> None:
    # 'variables' alone is not the slug 'variables-names'; don't touch it.
    text = "Variables are bound by name."
    out, removed = _strip_forward_refs(text, (), ALL_CONCEPTS)
    assert removed == []
    assert out == text


# ----------------------------------------------------------------------------
# Reflect length-gate — trivially short explanations must short-circuit to
# 'shallow' WITHOUT calling OpenAI. This test exercises that path; the
# OpenAI-pass path requires real credentials and lives outside CI.
# ----------------------------------------------------------------------------


def _ctx() -> ConceptContext:
    return ConceptContext(
        slug="variables-names",
        title="Variables and names",
        one_line="A variable is a name bound to a value.",
        exposition_md="(omitted)",
        worked_example_md="(omitted)",
        try_attempt_text=None,
        concepts_mastered=(),
        all_concept_slugs=ALL_CONCEPTS,
    )


def test_reflect_short_circuits_for_trivial_explanation() -> None:
    # Trivially short — should NOT hit OpenAI and should return 'shallow'.
    grade, meta = reflect_grade(_ctx(), {}, "idk")
    assert grade.verdict == "shallow"
    assert grade.follow_up is not None
    assert meta["length_gate"] == "too_short"
    assert meta["model"] == "deterministic"


def test_reflect_short_circuits_on_empty_explanation() -> None:
    grade, meta = reflect_grade(_ctx(), {}, "")
    assert grade.verdict == "shallow"
    assert meta["length_gate"] == "too_short"
