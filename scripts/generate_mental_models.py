"""Generate the Mental Models for Code track — concept-atom framework.

Run from repo root:

    python scripts/generate_mental_models.py

Writes two files:

- supabase/mental_models_seed.generated.sql
    Idempotent INSERTs for the Mental Models track, the universal-CS
    foundation concepts (shared across all tracks), and the topic-specific
    Mental Models concepts. Includes the placement diagnostic question bank.

- apps/web/src/lib/mental-models-config.generated.ts
    CONCEPT_CONFIG entries for each concept (Play widget JSON, MCQ payloads,
    rubric structures) keyed by concept slug. Read by the concept page.

The track + first 10 concept atoms (6 universal-CS + 4 topic-specific) follow
the 6-stage UNIT structure from the CC plan:

    Try   — productive-failure attempt before instruction (Kapur)
    Read  — concrete worked example + abstract exposition (Sweller)
    Play  — state-visible interactive widget (Bret Victor)
    Check — 2-3 MCQs with surface-feature variability
    Apply — full task in existing pyodide skeleton/fillblank lesson
    Reflect — 2-sentence self-explanation graded by mentor

The track UUID is 0x004; concept UUIDs are 0x400..0x4ff;
diagnostic-question UUIDs are 0x4f0..0x4ff.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK_UUID = "00000000-0000-0000-0000-000000000004"
TRACK_SLUG = "mental-models"
TRACK_TITLE = "Mental Models for Code"
TRACK_DESCRIPTION = (
    "Learn how to think about code, not just write it. Concept-by-concept: "
    "variables, references, control flow, recursion, complexity, state machines, "
    "and the memory model. Each concept follows a six-stage UNIT — Try, Read, "
    "Play, Check, Apply, Reflect — grounded in cognitive-load and productive-"
    "failure research."
)

LAYERS = frozenset({"universal", "topic", "applied"})
WIDGET_KINDS = frozenset(
    {
        "code-stepper",
        "call-stack-visualiser",
        "state-machine-animator",
        "memory-model-viewer",
        "complexity-plotter",
        "generic-slider-chart",
    }
)
TRY_KINDS = frozenset({"code", "text-reasoning"})


@dataclass
class Concept:
    """One concept atom — the framework's UNIT.

    Identity
    --------
    n              global concept number (1..N) — drives the UUID
    slug           kebab-case slug (e.g. 'variables-names')
    layer          'universal' | 'topic'  (applied is for legacy challenges)
    topic_slug     None for layer='universal'; track slug for 'topic'
    title          human-readable display title
    one_line       short summary for the concept map
    order_index    display ordering within layer+topic
    prereqs        list of concept slugs this concept depends on

    Stages — each stage's content lives in its own fields:
    """

    n: int
    slug: str
    layer: str
    title: str
    one_line: str
    order_index: int

    # Try stage
    try_prompt_md: str
    try_kind: str
    try_expected_attempts: list[dict] = field(default_factory=list)

    # Read stage
    exposition_md: str = ""
    worked_example_md: str = ""

    # Play stage
    play_widget_kind: str = "code-stepper"
    play_widget: dict = field(default_factory=dict)

    # Check stage — list of {q, options, correct, why}
    check_mcqs: list[dict] = field(default_factory=list)

    # Apply stage
    apply_challenge_slug: str | None = None

    # Reflect stage
    reflect_question: str = ""
    reflect_rubric: dict = field(default_factory=dict)

    # Recall pool — 3 short checks
    recall_checks: list[dict] = field(default_factory=list)

    # Topic and prereqs
    topic_slug: str | None = None
    prereqs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.layer not in LAYERS:
            raise ValueError(f"concept {self.slug}: invalid layer {self.layer!r}")
        if self.try_kind not in TRY_KINDS:
            raise ValueError(f"concept {self.slug}: invalid try_kind {self.try_kind!r}")
        if self.play_widget_kind not in WIDGET_KINDS:
            raise ValueError(
                f"concept {self.slug}: invalid widget kind {self.play_widget_kind!r}"
            )
        if self.layer == "topic" and not self.topic_slug:
            raise ValueError(f"concept {self.slug}: layer=topic requires topic_slug")

    @property
    def uuid(self) -> str:
        # Concept UUIDs live in 0x400..0x4ef. Diagnostic question UUIDs use
        # 0x4f0..0x4ff so the two ranges never collide.
        if self.n >= 0xF0:
            raise ValueError(f"concept {self.slug}: n={self.n} reserved for diagnostic")
        return f"00000000-0000-0000-0000-{0x400 + (self.n - 1):012x}"


@dataclass
class DiagnosticQuestion:
    n: int  # within the diagnostic bank (1..16 or so)
    track_slug: str
    layer: str  # 'universal' | 'topic'
    question_md: str
    question_kind: str  # 'mcq' | 'mini-code'
    options: dict  # {options: [...], correct: 0} for mcq; {starter_code, expected_stdout} for mini-code
    expected_answer: str
    maps_to_concept_slugs: list[str]
    order_index: int

    @property
    def uuid(self) -> str:
        # 0x4f0..0x4ff reserved range
        if self.n > 0x10:
            raise ValueError(f"diagnostic question {self.n}: exceeds 0x10 budget")
        return f"00000000-0000-0000-0000-{0x4F0 + (self.n - 1):012x}"


# ============================================================================
# CONCEPTS — Layer 1 (universal CS, 6 atoms) + Layer 2 (mental models, 4 atoms)
# ============================================================================
#
# Phase CC.0 ships ONE smoke concept (`variables-names`) end-to-end. The
# remaining 9 atoms are authored in Phase CC.5 and inserted here in the same
# shape.

CONCEPTS: list[Concept] = [
    Concept(
        n=1,
        slug="variables-names",
        layer="universal",
        title="Variables and names",
        one_line="A variable is a name bound to a value in a scope.",
        order_index=100,
        prereqs=[],
        # Try — productive-failure attempt BEFORE any teaching.
        # Learner is expected to be uncertain; the attempt seeds the Read.
        try_prompt_md=(
            "**Try.** Predict the output of this snippet — *no running it, no "
            "looking it up*. If you're not sure, write your best guess and a "
            "one-line reason.\n\n"
            "```python\n"
            "a = [1, 2, 3]\n"
            "b = a\n"
            "b.append(4)\n"
            "print(a)\n"
            "```"
        ),
        try_kind="text-reasoning",
        try_expected_attempts=[
            {
                "pattern": r"\[1,\s*2,\s*3\]",
                "callback_md": (
                    "You predicted `[1, 2, 3]` — that's what would happen if "
                    "`b = a` made a *copy*. It doesn't; it makes a second name "
                    "for the same list. The Read stage shows why."
                ),
            },
            {
                "pattern": r"\[1,\s*2,\s*3,\s*4\]",
                "callback_md": (
                    "You predicted `[1, 2, 3, 4]` — correct. The Read stage "
                    "shows *why* this is the case: `b = a` doesn't copy the "
                    "list, it just binds a second name to it."
                ),
            },
        ],
        # Read — concrete worked example FIRST, then abstract exposition.
        exposition_md=(
            "A variable is not a box. It's a **name bound to a value in a "
            "scope**. Two names can be bound to the same value at once; "
            "mutating that value affects every name pointing at it.\n\n"
            "The mental model that catches *most* Python aliasing bugs is "
            "this: imagine an arrow from each name to the underlying object. "
            "`a = [1, 2, 3]` draws one arrow. `b = a` draws a second arrow "
            "to the *same* list (no second list is created). When you call "
            "`b.append(4)`, the list both arrows point at gets a new element "
            "— so `a` and `b` both reflect the change.\n\n"
            "This is different from immutable values like ints and strings. "
            "`x = 5; y = x; y = 6` doesn't change `x`, because integers are "
            "immutable — `y = 6` rebinds `y` to a different object instead "
            "of mutating the old one."
        ),
        worked_example_md=(
            "```python\n"
            "# Two names, one list.\n"
            "a = [1, 2, 3]    # 'a' → [1, 2, 3]\n"
            "b = a            # 'b' → same [1, 2, 3]; no copy made\n"
            "b.append(4)      # the shared list gets a new element\n"
            "print(a)         # [1, 2, 3, 4]\n"
            "print(b)         # [1, 2, 3, 4]\n"
            "print(a is b)    # True — same underlying object\n"
            "```"
        ),
        # Play — code-stepper widget shows variable bindings + heap state.
        # The Phase CC.2 widget renders this JSON.
        play_widget_kind="code-stepper",
        play_widget={
            "title": "Step through a name-binding scenario",
            "code": (
                "a = [1, 2, 3]\n"
                "b = a\n"
                "b.append(4)\n"
                "print(a)"
            ),
            "steps": [
                {
                    "line": 1,
                    "bindings": {"a": "→ list#1 [1, 2, 3]"},
                    "heap": [{"id": "list#1", "value": "[1, 2, 3]"}],
                    "caption": "`a` is bound to a list — one arrow from `a` to list#1.",
                },
                {
                    "line": 2,
                    "bindings": {"a": "→ list#1", "b": "→ list#1"},
                    "heap": [{"id": "list#1", "value": "[1, 2, 3]"}],
                    "caption": "`b = a` does NOT copy — it draws a second arrow to the same list#1.",
                },
                {
                    "line": 3,
                    "bindings": {"a": "→ list#1", "b": "→ list#1"},
                    "heap": [{"id": "list#1", "value": "[1, 2, 3, 4]"}],
                    "caption": "`b.append(4)` mutates list#1 itself — both `a` and `b` see the change.",
                },
                {
                    "line": 4,
                    "bindings": {"a": "→ list#1", "b": "→ list#1"},
                    "heap": [{"id": "list#1", "value": "[1, 2, 3, 4]"}],
                    "caption": "`print(a)` reads the (now-mutated) list. Output: [1, 2, 3, 4].",
                },
            ],
        },
        # Check — 2 MCQs with surface-feature variability (different containers,
        # different mutation methods — same underlying concept).
        check_mcqs=[
            {
                "q": (
                    "Given `xs = {'k': 1}` and `ys = xs`, what does "
                    "`ys['k'] = 9; print(xs)` print?"
                ),
                "options": ["{'k': 1}", "{'k': 9}", "TypeError", "None"],
                "correct": 1,
                "why": (
                    "`ys = xs` binds `ys` to the *same* dict. Mutating via "
                    "either name is visible through the other."
                ),
            },
            {
                "q": (
                    "Given `s = 'hi'; t = s; t = t + '!'`, what does "
                    "`print(s)` print?"
                ),
                "options": ["'hi'", "'hi!'", "'!hi'", "Error"],
                "correct": 0,
                "why": (
                    "Strings are immutable. `t = t + '!'` rebinds `t` to a "
                    "new string; `s` still points at the original 'hi'."
                ),
            },
        ],
        # Apply — links to an existing skeleton/fillblank challenge in the
        # Python Basics track. (Will be authored in Phase CC.5 if no exact
        # match exists. For the smoke ship of CC.0 this can stay null —
        # the Apply stage just shows "no Apply challenge yet" until then.)
        apply_challenge_slug=None,
        # Reflect — open-ended self-explanation graded by the mentor.
        reflect_question=(
            "In two sentences, explain to a colleague what a *variable* is "
            "in Python — and why `b = a` followed by `b.append(4)` changes "
            "`a` too."
        ),
        reflect_rubric={
            "must_mention": [
                "name",
                "value",
                "scope",
            ],
            "must_distinguish": [
                ["binding", "copying"],
                ["mutable", "immutable"],
            ],
            "must_explain": [
                "two names can be bound to the same object",
                "mutating the object affects every name bound to it",
            ],
        },
        # Recall pool — 3 short checks, one drawn at random per spaced-recall visit.
        recall_checks=[
            {
                "kind": "mcq",
                "q": "Given `xs = [1]; ys = xs; ys.append(2)`, what is `xs`?",
                "options": ["[1]", "[1, 2]", "TypeError"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "If `s = 'a'; t = s; t = 'b'`, what is `s`?",
                "options": ["'a'", "'b'", "None"],
                "correct": 0,
            },
            {
                "kind": "mcq",
                "q": "What does `b = a` do when `a` is a list?",
                "options": [
                    "Copies the list",
                    "Creates a second name for the same list",
                    "Raises an exception",
                ],
                "correct": 1,
            },
        ],
    ),
    # ------------------------------------------------------------------
    # Concept 2: references vs values — what mutation actually does.
    # Builds on variables-names; the Try here is the canonical "mutate a
    # list-default-argument" classic novice trap.
    # ------------------------------------------------------------------
    Concept(
        n=2,
        slug="references-values",
        layer="universal",
        title="References and values",
        one_line="Mutating an object is visible through every name bound to it.",
        order_index=200,
        prereqs=["variables-names"],
        try_prompt_md=(
            "**Try.** Predict the output of this snippet — without running it. "
            "It's a famous Python gotcha.\n\n"
            "```python\n"
            "def add_one(xs=[]):\n"
            "    xs.append(1)\n"
            "    return xs\n"
            "\n"
            "print(add_one())\n"
            "print(add_one())\n"
            "```"
        ),
        try_kind="text-reasoning",
        try_expected_attempts=[
            {
                "pattern": r"\[1\]\s*\[1\]",
                "callback_md": (
                    "You predicted two `[1]`s — that's what you'd get if "
                    "Python re-created the default list each call. It doesn't."
                ),
            },
            {
                "pattern": r"\[1\]\s*\[1,\s*1\]",
                "callback_md": (
                    "Correct. The default value is evaluated *once* at "
                    "function-definition time; every call without an "
                    "explicit `xs` shares that same list."
                ),
            },
        ],
        exposition_md=(
            "Python evaluates default arguments **once**, at function "
            "definition time. The resulting object is then shared across "
            "every call that doesn't pass that argument explicitly. If "
            "the default is a mutable object — a list, dict, set — every "
            "call's mutations accumulate on the same instance.\n\n"
            "The fix is the **None-sentinel** pattern: default to `None`, "
            "then check inside the function and create a fresh object per "
            "call. This is so common it's a 30-second answer in every "
            "senior Python interview.\n\n"
            "More broadly: when a function receives a mutable argument, "
            "decide explicitly whether you want to mutate it (visible to "
            "the caller, like `list.sort()`) or return a new object "
            "(no caller side effects, like `sorted()`). Either is fine; "
            "mixing them is what causes bugs."
        ),
        worked_example_md=(
            "```python\n"
            "# The bug:\n"
            "def add_one(xs=[]):\n"
            "    xs.append(1)        # mutates the shared default\n"
            "    return xs\n"
            "\n"
            "print(add_one())        # [1]\n"
            "print(add_one())        # [1, 1] — same list!\n"
            "\n"
            "# The fix:\n"
            "def add_one_safe(xs=None):\n"
            "    if xs is None:\n"
            "        xs = []         # fresh list per call\n"
            "    xs.append(1)\n"
            "    return xs\n"
            "\n"
            "print(add_one_safe())   # [1]\n"
            "print(add_one_safe())   # [1] — independent\n"
            "```"
        ),
        # Memory-model-viewer would render an arrow-and-box diagram here.
        # CC.2's host renders a stub; the config is authored for the eventual
        # widget implementation.
        play_widget_kind="memory-model-viewer",
        play_widget={
            "title": "The shared default list",
            "frames": [
                {
                    "caption": "At function definition: Python builds the default list once.",
                    "stack": [{"name": "(module)", "vars": {}}],
                    "heap": [
                        {"id": "list#1", "value": "[]", "labels": ["add_one.__defaults__[0]"]}
                    ],
                },
                {
                    "caption": "Call 1: xs binds to list#1 → append(1) mutates it.",
                    "stack": [
                        {"name": "(module)", "vars": {}},
                        {"name": "add_one", "vars": {"xs": "→ list#1"}},
                    ],
                    "heap": [
                        {"id": "list#1", "value": "[1]", "labels": ["add_one.__defaults__[0]", "xs"]}
                    ],
                },
                {
                    "caption": "Call 2: xs binds to the SAME list#1 → another mutation.",
                    "stack": [
                        {"name": "(module)", "vars": {}},
                        {"name": "add_one", "vars": {"xs": "→ list#1"}},
                    ],
                    "heap": [
                        {"id": "list#1", "value": "[1, 1]", "labels": ["add_one.__defaults__[0]", "xs"]}
                    ],
                },
            ],
        },
        check_mcqs=[
            {
                "q": (
                    "What does this print?\n\n"
                    "```\n"
                    "def f(d={}):\n"
                    "    d['n'] = d.get('n', 0) + 1\n"
                    "    return d\n"
                    "\n"
                    "print(f()); print(f())\n"
                    "```"
                ),
                "options": [
                    "{'n': 1} {'n': 1}",
                    "{'n': 1} {'n': 2}",
                    "{'n': 0} {'n': 1}",
                    "TypeError",
                ],
                "correct": 1,
                "why": (
                    "Same trap as lists. The dict default is built once "
                    "and reused across calls."
                ),
            },
            {
                "q": (
                    "Which is the safe default for a list-typed argument "
                    "in Python?"
                ),
                "options": [
                    "`def f(xs=[]):`",
                    "`def f(xs=list()):`",
                    "`def f(xs=None):` and create the list inside",
                    "`def f(xs):` and document that the caller must pass one",
                ],
                "correct": 2,
                "why": (
                    "The None-sentinel pattern is the canonical fix — a "
                    "fresh list per call, no shared state."
                ),
            },
        ],
        apply_challenge_slug=None,
        reflect_question=(
            "In two sentences, explain why mutating a default argument "
            "value in Python can leak state across calls — and how to "
            "fix it."
        ),
        reflect_rubric={
            "must_mention": ["default", "mutable", "shared"],
            "must_distinguish": [
                ["evaluation at definition", "evaluation per call"],
            ],
            "must_explain": [
                "the default object is created once",
                "every call without the argument reuses that same object",
                "use None as the sentinel and create a fresh object inside",
            ],
        },
        recall_checks=[
            {
                "kind": "mcq",
                "q": "Calling `f()` twice when `f` has `xs=[]` as default and appends 1 produces what after the second call?",
                "options": ["[1]", "[1, 1]", "[]"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "The Pythonic safe-default pattern is:",
                "options": ["`xs=[]`", "`xs=None` + check inside", "`xs=list()`"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "Default arguments in Python are evaluated…",
                "options": ["once, at definition", "every call", "lazily, on first use"],
                "correct": 0,
            },
        ],
    ),
    # ------------------------------------------------------------------
    # Concept 3: control flow — sequencing, branching, looping as causality.
    # Uses the code-stepper widget; the Try is a "predict the output of a
    # short imperative snippet" classic.
    # ------------------------------------------------------------------
    Concept(
        n=3,
        slug="control-flow",
        layer="universal",
        title="Control flow",
        one_line="Code runs top-to-bottom unless an if, loop, or function call diverts it.",
        order_index=300,
        prereqs=["variables-names"],
        try_prompt_md=(
            "**Try.** Predict what this prints — and how many times the "
            "body of the loop runs.\n\n"
            "```python\n"
            "n = 0\n"
            "for i in range(3):\n"
            "    if i == 1:\n"
            "        continue\n"
            "    n += i\n"
            "print(n)\n"
            "```"
        ),
        try_kind="text-reasoning",
        try_expected_attempts=[
            {
                "pattern": r"\b3\b",
                "callback_md": (
                    "You predicted 3 — that's the answer if all three "
                    "iterations contributed. `continue` skipped one."
                ),
            },
            {
                "pattern": r"\b2\b",
                "callback_md": (
                    "Correct. i=0 adds 0, i=1 hits `continue` so skips the "
                    "addition, i=2 adds 2 — total 2."
                ),
            },
        ],
        exposition_md=(
            "Code is **causal** — earlier statements set up the state that "
            "later statements depend on. Reading code is therefore a form "
            "of mental simulation: hold the current values of the live "
            "variables in your head, then step forward.\n\n"
            "Control-flow primitives are the three ways execution diverges "
            "from straight-line:\n\n"
            "1. **Branching** (`if` / `elif` / `else`): exactly one block "
            "runs based on a condition. Track which.\n"
            "2. **Looping** (`for` / `while`): a block runs multiple times. "
            "Track the loop variable and the accumulator.\n"
            "3. **Function calls**: execution jumps to the function body, "
            "runs to a `return` (or implicit None), and resumes one line "
            "after the call. Track which frame you're in.\n\n"
            "`break` exits the nearest loop. `continue` skips to the next "
            "iteration. Both are early-exit shortcuts — easy to misread."
        ),
        worked_example_md=(
            "```python\n"
            "# Sum the even numbers under 6.\n"
            "total = 0\n"
            "for i in range(6):\n"
            "    if i % 2 != 0:\n"
            "        continue        # skip odd i's\n"
            "    total += i          # only runs for i in {0, 2, 4}\n"
            "print(total)            # 6\n"
            "```"
        ),
        play_widget_kind="code-stepper",
        play_widget={
            "title": "Step through a continue-in-a-loop",
            "code": (
                "total = 0\n"
                "for i in range(6):\n"
                "    if i % 2 != 0:\n"
                "        continue\n"
                "    total += i\n"
                "print(total)"
            ),
            "steps": [
                {"line": 1, "bindings": {"total": "0"}, "caption": "`total` starts at 0."},
                {
                    "line": 2,
                    "bindings": {"total": "0", "i": "0"},
                    "caption": "First iteration: i=0 (even).",
                },
                {
                    "line": 5,
                    "bindings": {"total": "0", "i": "0"},
                    "caption": "0 % 2 == 0, so we skip continue and reach the add.",
                },
                {
                    "line": 5,
                    "bindings": {"total": "0", "i": "1"},
                    "caption": "Second iteration: i=1 (odd). Condition triggers.",
                },
                {
                    "line": 4,
                    "bindings": {"total": "0", "i": "1"},
                    "caption": "`continue` — jump straight back to the loop header. `total` unchanged.",
                },
                {
                    "line": 5,
                    "bindings": {"total": "2", "i": "2"},
                    "caption": "i=2 (even). 0 + 2 = 2.",
                },
                {
                    "line": 5,
                    "bindings": {"total": "2", "i": "3"},
                    "caption": "i=3 (odd). continue again. No change.",
                },
                {
                    "line": 5,
                    "bindings": {"total": "6", "i": "4"},
                    "caption": "i=4 (even). 2 + 4 = 6.",
                },
                {
                    "line": 5,
                    "bindings": {"total": "6", "i": "5"},
                    "caption": "i=5 (odd). continue. Final total 6.",
                },
                {
                    "line": 6,
                    "bindings": {"total": "6"},
                    "caption": "Print 6 — the sum of even numbers 0..4.",
                },
            ],
        },
        check_mcqs=[
            {
                "q": (
                    "How many times does the body of `for i in range(4): "
                    "if i == 2: break; print(i)` actually print?"
                ),
                "options": ["1", "2", "3", "4"],
                "correct": 1,
                "why": (
                    "`break` exits the loop entirely at i=2 — only i=0 and "
                    "i=1 reach the print, so 2 lines."
                ),
            },
            {
                "q": (
                    "What does `continue` do inside a `for` loop?"
                ),
                "options": [
                    "Exits the loop entirely",
                    "Skips the rest of the current iteration and starts the next",
                    "Restarts the loop from the beginning",
                    "Pauses execution",
                ],
                "correct": 1,
                "why": (
                    "`continue` is a per-iteration shortcut, not a "
                    "per-loop shortcut. The loop header runs again "
                    "immediately."
                ),
            },
        ],
        apply_challenge_slug=None,
        reflect_question=(
            "In two sentences, describe how `break` and `continue` differ "
            "— and why someone reading code at a glance might confuse them."
        ),
        reflect_rubric={
            "must_mention": ["break", "continue", "loop"],
            "must_distinguish": [
                ["exit the loop", "skip the iteration"],
            ],
            "must_explain": [
                "break exits the enclosing loop entirely",
                "continue jumps to the next iteration of the same loop",
                "both are early-exit shortcuts inside the loop body",
            ],
        },
        recall_checks=[
            {
                "kind": "mcq",
                "q": "`break` inside a `for` loop:",
                "options": ["skips one iteration", "exits the loop", "restarts the loop"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "`continue` inside a `for` loop:",
                "options": ["skips to next iteration", "exits the loop", "raises an exception"],
                "correct": 0,
            },
            {
                "kind": "mcq",
                "q": "If an `if` condition is False, the matching block:",
                "options": ["runs", "is skipped", "raises TypeError"],
                "correct": 1,
            },
        ],
    ),
    # ------------------------------------------------------------------
    # Concept 5: recursion — base case + recursive case + the stack.
    # Uses the call-stack-visualiser widget. The Try is to predict a small
    # factorial result without computing it longhand.
    # ------------------------------------------------------------------
    Concept(
        n=5,
        slug="recursion",
        layer="universal",
        title="Recursion",
        one_line="A function that calls itself — with a base case and a smaller subproblem.",
        order_index=500,
        prereqs=["functions"],
        try_prompt_md=(
            "**Try.** This is a classic recursive factorial:\n\n"
            "```python\n"
            "def fact(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * fact(n - 1)\n"
            "\n"
            "print(fact(4))\n"
            "```\n\n"
            "Predict what `fact(4)` returns — and how many times `fact` is "
            "called in total."
        ),
        try_kind="text-reasoning",
        try_expected_attempts=[
            {
                "pattern": r"\b24\b.*[3-5]",
                "callback_md": (
                    "You got the value (24) and an attempt at the call "
                    "count. The exact number of calls is 4 — fact(4), "
                    "fact(3), fact(2), fact(1). The Read covers why."
                ),
            },
            {
                "pattern": r"\b24\b",
                "callback_md": (
                    "Value correct (24 = 4 × 3 × 2 × 1). The call count "
                    "matters for the next stage — keep that in mind."
                ),
            },
        ],
        exposition_md=(
            "A recursive function calls itself. To not loop forever, every "
            "recursion needs:\n\n"
            "1. A **base case** — an input the function can answer without "
            "calling itself (here: `n <= 1` returns 1).\n"
            "2. A **recursive case** — a step that reduces the input "
            "toward the base case (here: `n - 1`) and combines the "
            "subresult (here: multiplies by `n`).\n\n"
            "Each call pushes a new **stack frame** holding the call's "
            "local variables. The frame stays on the stack until its "
            "function returns. For `fact(4)`, the stack grows: fact(4) → "
            "fact(3) → fact(2) → fact(1). fact(1) returns 1, then each "
            "outer frame collapses, multiplying as it goes: 1, 2, 6, 24.\n\n"
            "Forget the base case and the stack grows forever — you get "
            "`RecursionError: maximum recursion depth exceeded`. Forget "
            "to reduce toward the base case and the same."
        ),
        worked_example_md=(
            "```python\n"
            "def fact(n):\n"
            "    if n <= 1:                # base case\n"
            "        return 1\n"
            "    return n * fact(n - 1)    # recursive case\n"
            "\n"
            "print(fact(4))                # 24\n"
            "```\n\n"
            "Call trace:\n"
            "  fact(4) → 4 * fact(3) → 4 * (3 * fact(2)) → 4 * (3 * (2 * fact(1)))\n"
            "  fact(1) returns 1, then we unwind: 2*1=2, 3*2=6, 4*6=24."
        ),
        play_widget_kind="call-stack-visualiser",
        play_widget={
            "title": "Watch the call stack of fact(4)",
            "function_name": "fact",
            "frames": [
                {"caption": "Initial call.", "stack": ["fact(4)"]},
                {"caption": "fact(4) calls fact(3).", "stack": ["fact(4)", "fact(3)"]},
                {"caption": "fact(3) calls fact(2).", "stack": ["fact(4)", "fact(3)", "fact(2)"]},
                {
                    "caption": "fact(2) calls fact(1).",
                    "stack": ["fact(4)", "fact(3)", "fact(2)", "fact(1)"],
                },
                {
                    "caption": "fact(1) hits the base case and returns 1. The frame pops.",
                    "stack": ["fact(4)", "fact(3)", "fact(2) ← 1"],
                },
                {
                    "caption": "fact(2) computes 2 * 1 = 2 and returns. Pop.",
                    "stack": ["fact(4)", "fact(3) ← 2"],
                },
                {
                    "caption": "fact(3) computes 3 * 2 = 6 and returns. Pop.",
                    "stack": ["fact(4) ← 6"],
                },
                {"caption": "fact(4) computes 4 * 6 = 24 and returns. Stack empty.", "stack": []},
            ],
        },
        check_mcqs=[
            {
                "q": (
                    "What's missing from this recursive function?\n\n"
                    "```\n"
                    "def count_down(n):\n"
                    "    print(n)\n"
                    "    count_down(n - 1)\n"
                    "```"
                ),
                "options": [
                    "Nothing — it works",
                    "A base case",
                    "A return statement",
                    "A loop",
                ],
                "correct": 1,
                "why": (
                    "No base case → infinite recursion → "
                    "RecursionError. Add `if n <= 0: return` at the top."
                ),
            },
            {
                "q": (
                    "How many stack frames are live (not yet returned) at the "
                    "moment `fact(1)` is about to compute its return value, "
                    "when called as `fact(5)`?"
                ),
                "options": ["1", "3", "5", "Infinite"],
                "correct": 2,
                "why": (
                    "fact(5), fact(4), fact(3), fact(2), fact(1) — five "
                    "frames all live until the base case starts unwinding."
                ),
            },
        ],
        apply_challenge_slug=None,
        reflect_question=(
            "In two sentences, explain why a recursive function needs a "
            "base case — and what happens at runtime if you forget it."
        ),
        reflect_rubric={
            "must_mention": ["base case", "stack", "recursive"],
            "must_distinguish": [
                ["recursive case", "base case"],
            ],
            "must_explain": [
                "the base case is the input the function can answer without recursing",
                "without it the stack grows until RecursionError",
                "each call adds a frame; the base case starts the unwinding",
            ],
        },
        recall_checks=[
            {
                "kind": "mcq",
                "q": "A recursive function with no base case will:",
                "options": ["return None", "raise RecursionError", "loop forever"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "Each recursive call adds:",
                "options": ["a CPU register", "a stack frame", "a global variable"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "fact(3) calls how many functions before the first return?",
                "options": ["1", "3", "9"],
                "correct": 1,
            },
        ],
    ),
]


# ============================================================================
# DIAGNOSTIC — Layer-0 placement questions
# ============================================================================
#
# Phase CC.0 ships ONE placeholder question to wire the schema end-to-end.
# The full 10-question bank is authored in Phase CC.3.

DIAGNOSTIC_QUESTIONS: list[DiagnosticQuestion] = [
    DiagnosticQuestion(
        n=1,
        track_slug=TRACK_SLUG,
        layer="universal",
        question_md=(
            "Given `a = [1, 2]; b = a; b.append(3)`, what does `print(a)` print?"
        ),
        question_kind="mcq",
        options={"options": ["[1, 2]", "[1, 2, 3]", "[3]", "TypeError"], "correct": 1},
        expected_answer="1",
        maps_to_concept_slugs=["variables-names", "references-values"],
        order_index=1,
    ),
]


# ============================================================================
# SQL writer
# ============================================================================


def sql_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n")


def jsonb_lit(obj) -> str:
    """Render a Python object as a PostgreSQL JSONB literal."""
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return f"E'{sql_escape(payload)}'::jsonb"


def text_array_lit(items: list[str]) -> str:
    if not items:
        return "'{}'::text[]"
    quoted = ", ".join(f"'{sql_escape(s)}'" for s in items)
    return f"array[{quoted}]::text[]"


def write_sql() -> Path:
    lines: list[str] = []
    lines.append("-- AUTO-GENERATED by scripts/generate_mental_models.py")
    lines.append("-- Mental Models for Code track + concept atoms + diagnostic bank.")
    lines.append("-- Track + modules + the foundation concepts seed here.")
    lines.append("")

    # Track row (idempotent upsert).
    lines.append("insert into public.tracks (id, slug, title, description, difficulty, is_published) values (")
    lines.append(f"  '{TRACK_UUID}',")
    lines.append(f"  '{TRACK_SLUG}',")
    lines.append(f"  E'{sql_escape(TRACK_TITLE)}',")
    lines.append(f"  E'{sql_escape(TRACK_DESCRIPTION)}',")
    lines.append("  'foundation',")
    lines.append("  true")
    lines.append(")")
    lines.append("on conflict (slug) do update set")
    lines.append("  title = excluded.title,")
    lines.append("  description = excluded.description,")
    lines.append("  difficulty = excluded.difficulty,")
    lines.append("  is_published = excluded.is_published;")
    lines.append("")

    # Wipe + reinsert concept rows so renames / renumbering don't leave
    # orphans. Safe while the framework has no live learner data; revisit
    # before opening it to real users.
    lines.append(
        "delete from public.concept_prereqs where concept_id in ("
        "select id from public.concepts);"
    )
    lines.append("delete from public.concepts where slug like '%-%';")
    lines.append("delete from public.diagnostic_questions where track_slug = "
                 f"'{TRACK_SLUG}';")
    lines.append("")

    for concept in CONCEPTS:
        lines.append("insert into public.concepts (")
        lines.append(
            "  id, slug, layer, topic_slug, title, one_line,"
            " try_prompt_md, try_kind, try_expected_attempts_json,"
            " exposition_md, worked_example_md,"
            " play_widget_kind, play_widget_json,"
            " check_mcqs_json, apply_challenge_slug,"
            " reflect_question, reflect_rubric_json,"
            " recall_checks_json, order_index"
        )
        lines.append(") values (")
        lines.append(f"  '{concept.uuid}',")
        lines.append(f"  '{concept.slug}',")
        lines.append(f"  '{concept.layer}',")
        lines.append(
            f"  '{concept.topic_slug}'," if concept.topic_slug else "  null,"
        )
        lines.append(f"  E'{sql_escape(concept.title)}',")
        lines.append(f"  E'{sql_escape(concept.one_line)}',")
        lines.append(f"  E'{sql_escape(concept.try_prompt_md)}',")
        lines.append(f"  '{concept.try_kind}',")
        lines.append(f"  {jsonb_lit(concept.try_expected_attempts)},")
        lines.append(f"  E'{sql_escape(concept.exposition_md)}',")
        lines.append(f"  E'{sql_escape(concept.worked_example_md)}',")
        lines.append(f"  '{concept.play_widget_kind}',")
        lines.append(f"  {jsonb_lit(concept.play_widget)},")
        lines.append(f"  {jsonb_lit(concept.check_mcqs)},")
        if concept.apply_challenge_slug:
            lines.append(f"  '{concept.apply_challenge_slug}',")
        else:
            lines.append("  null,")
        lines.append(f"  E'{sql_escape(concept.reflect_question)}',")
        lines.append(f"  {jsonb_lit(concept.reflect_rubric)},")
        lines.append(f"  {jsonb_lit(concept.recall_checks)},")
        lines.append(f"  {concept.order_index}")
        lines.append(");")
        lines.append("")

    # Prereq edges — done in a second pass since concepts must exist first.
    for concept in CONCEPTS:
        for prereq_slug in concept.prereqs:
            lines.append(
                "insert into public.concept_prereqs (concept_id, prereq_concept_id) "
                f"select c.id, p.id from public.concepts c, public.concepts p "
                f"where c.slug = '{concept.slug}' and p.slug = '{prereq_slug}'"
                " on conflict do nothing;"
            )
    if any(c.prereqs for c in CONCEPTS):
        lines.append("")

    # Diagnostic question bank.
    for q in DIAGNOSTIC_QUESTIONS:
        lines.append("insert into public.diagnostic_questions (")
        lines.append(
            "  id, track_slug, layer, question_md, question_kind,"
            " options_json, expected_answer, maps_to_concept_slugs, order_index"
        )
        lines.append(") values (")
        lines.append(f"  '{q.uuid}',")
        lines.append(f"  '{q.track_slug}',")
        lines.append(f"  '{q.layer}',")
        lines.append(f"  E'{sql_escape(q.question_md)}',")
        lines.append(f"  '{q.question_kind}',")
        lines.append(f"  {jsonb_lit(q.options)},")
        lines.append(f"  E'{sql_escape(q.expected_answer)}',")
        lines.append(f"  {text_array_lit(q.maps_to_concept_slugs)},")
        lines.append(f"  {q.order_index}")
        lines.append(");")
        lines.append("")

    out_path = ROOT / "supabase" / "mental_models_seed.generated.sql"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ============================================================================
# TS config writer — drives the concept page's runtime config
# ============================================================================


def write_ts_config() -> Path:
    """Emit the per-concept runtime config consumed by apps/web.

    Mirrors the shape of quant-config.generated.ts: a single map literal
    keyed by concept slug. The web concept-page component reads from this
    so widget JSON, MCQ payloads, and rubric structure don't have to
    round-trip through the API on every request.
    """
    lines: list[str] = []
    lines.append("// AUTO-GENERATED by scripts/generate_mental_models.py")
    lines.append("// Per-concept runtime config: Play widget JSON, MCQs,")
    lines.append("// rubric structure. Read by the concept page.")
    lines.append("")
    lines.append("export type ConceptConfig = {")
    lines.append("  slug: string;")
    lines.append("  playWidgetKind: string;")
    lines.append("  playWidget: Record<string, unknown>;")
    lines.append("  checkMcqs: Array<{")
    lines.append("    q: string;")
    lines.append("    options: string[];")
    lines.append("    correct: number;")
    lines.append("    why?: string;")
    lines.append("  }>;")
    lines.append("  reflectQuestion: string;")
    lines.append("  reflectRubric: Record<string, unknown>;")
    lines.append("  recallChecks: Array<Record<string, unknown>>;")
    lines.append("};")
    lines.append("")
    lines.append("export const MENTAL_MODELS_CONFIG: Record<string, ConceptConfig> = {")
    for concept in CONCEPTS:
        lines.append(f"  '{concept.slug}': {{")
        lines.append(f"    slug: '{concept.slug}',")
        lines.append(f"    playWidgetKind: '{concept.play_widget_kind}',")
        lines.append(
            "    playWidget: "
            + json.dumps(concept.play_widget, ensure_ascii=False)
            + ","
        )
        lines.append(
            "    checkMcqs: "
            + json.dumps(concept.check_mcqs, ensure_ascii=False)
            + ","
        )
        # Escape backticks and dollar signs in case they ever appear in copy.
        rq_escaped = concept.reflect_question.replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"    reflectQuestion: '{rq_escaped}',")
        lines.append(
            "    reflectRubric: "
            + json.dumps(concept.reflect_rubric, ensure_ascii=False)
            + ","
        )
        lines.append(
            "    recallChecks: "
            + json.dumps(concept.recall_checks, ensure_ascii=False)
            + ","
        )
        lines.append("  },")
    lines.append("};")
    lines.append("")

    out_path = ROOT / "apps" / "web" / "src" / "lib" / "mental-models-config.generated.ts"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ============================================================================
# Entry point
# ============================================================================


def main() -> None:
    sql_path = write_sql()
    ts_path = write_ts_config()
    print(f"wrote {sql_path.relative_to(ROOT)}")
    print(f"wrote {ts_path.relative_to(ROOT)}")
    print(f"\n{len(CONCEPTS)} concept(s), {len(DIAGNOSTIC_QUESTIONS)} diagnostic question(s).")


if __name__ == "__main__":
    main()
