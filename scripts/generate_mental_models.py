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
    # M2 — inline Pyodide skeleton. Shape:
    #   {instructions_md: str, starter_code: str, hidden_test: str}
    # When non-null, the Apply stage renders a runner that loads
    # starter_code + hidden_test and runs pytest. Pass → stage complete.
    apply_skeleton: dict | None = None

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
        # Read — short, scannable. Bret Victor's principle: surface the
        # mental model first ("arrow from name to value"), then bullet the
        # three rules. Worked example renders below.
        exposition_md=(
            "**Mental model:** a variable is an arrow from a *name* to a *value*. "
            "Two names can point at the same value.\n\n"
            "Three rules cover almost every Python aliasing bug:\n\n"
            "- `b = a` does **not** copy. It points `b` at whatever `a` is already pointing at.\n"
            "- Mutating the value (e.g. `b.append(4)`) is visible through *every* name pointing at it.\n"
            "- Re-assigning a name (e.g. `b = 99`) only moves *that* name's arrow — it doesn't touch the old value or other names.\n\n"
            "Lists, dicts, and sets are **mutable** — the gotcha above applies. "
            "Ints, strings, and tuples are **immutable** — you can't mutate them, "
            "so two names pointing at the same int can never surprise each other."
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
        # different mutation methods — same underlying concept). The `q` is
        # rendered as markdown — fenced code blocks read better than inline soup.
        check_mcqs=[
            {
                "q": (
                    "What does this print?\n\n"
                    "```python\n"
                    "xs = {'k': 1}\n"
                    "ys = xs\n"
                    "ys['k'] = 9\n"
                    "print(xs)\n"
                    "```"
                ),
                "options": [
                    "`{'k': 1}`",
                    "`{'k': 9}`",
                    "`TypeError`",
                    "`None`",
                ],
                "correct": 1,
                "why": (
                    "`ys = xs` points `ys` at the *same* dict. Mutating via "
                    "either name is visible through the other."
                ),
            },
            {
                "q": (
                    "What does this print?\n\n"
                    "```python\n"
                    "s = 'hi'\n"
                    "t = s\n"
                    "t = t + '!'\n"
                    "print(s)\n"
                    "```"
                ),
                "options": [
                    "`'hi'`",
                    "`'hi!'`",
                    "`'!hi'`",
                    "`Error`",
                ],
                "correct": 0,
                "why": (
                    "Strings are immutable. `t = t + '!'` builds a new string "
                    "and points `t` at it — `s` still points at the original."
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
        # Kept small on purpose. The grader treats this as a guide, not a
        # checklist (see system_prompts.md → "Reflect grade prompt"). A
        # paraphrase like "two names point at the same list, so changing
        # it through b shows up through a" should pass.
        reflect_rubric={
            "must_mention": ["name", "value"],
            "must_distinguish": [["mutable", "immutable"]],
            "must_explain": [
                "two names can point at the same value; mutating it is visible through both",
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
    # Concept 4: functions — args, return, side effects, pure vs impure.
    # Uses code-stepper. The Try contrasts a mutating vs returning version
    # of the same operation.
    # ------------------------------------------------------------------
    Concept(
        n=4,
        slug="functions",
        layer="universal",
        title="Functions",
        one_line="A function takes inputs, optionally has side effects, and may return a value.",
        order_index=400,
        prereqs=["variables-names", "control-flow"],
        try_prompt_md=(
            "**Try.** Two near-identical functions. Predict what each call "
            "prints.\n\n"
            "```python\n"
            "def add_in_place(xs, n):\n"
            "    xs.append(n)        # mutates xs\n"
            "\n"
            "def add_returning(xs, n):\n"
            "    return xs + [n]     # returns a new list\n"
            "\n"
            "a = [1, 2]\n"
            "add_in_place(a, 3)\n"
            "print(a)\n"
            "\n"
            "b = [1, 2]\n"
            "result = add_returning(b, 3)\n"
            "print(b, result)\n"
            "```"
        ),
        try_kind="text-reasoning",
        try_expected_attempts=[
            {
                "pattern": r"\[1,\s*2,\s*3\].*\[1,\s*2\].*\[1,\s*2,\s*3\]",
                "callback_md": "Correct — mutating vs returning is a real distinction.",
            },
            {
                "pattern": r"\[1,\s*2\]",
                "callback_md": (
                    "Partially right. The key difference is that "
                    "`add_in_place` mutates `a`; `add_returning` leaves "
                    "`b` alone but returns a new list."
                ),
            },
        ],
        exposition_md=(
            "A function is a reusable block of code that takes inputs "
            "(arguments) and may produce outputs in two ways:\n\n"
            "1. **Return value** — what `return` sends back to the caller. "
            "If you omit `return`, Python implicitly returns `None`.\n"
            "2. **Side effects** — anything else visible outside the "
            "function: mutating an argument, printing, writing a file, "
            "modifying a global.\n\n"
            "A function is **pure** if its return value depends only on "
            "its arguments and it has no side effects. Pure functions "
            "are the easiest to test (same input → same output, always) "
            "and the easiest to reason about. Use them as the default; "
            "fall back to side effects only when you must.\n\n"
            "Inside a function, the parameter names become **local "
            "bindings** — they live in a fresh scope. Reassigning them "
            "doesn't affect the caller's bindings. *Mutating* the "
            "object they point at does, because the binding and the "
            "object are different things (lesson: references-values)."
        ),
        worked_example_md=(
            "```python\n"
            "def square(n):            # pure: same n → same return\n"
            "    return n * n\n"
            "\n"
            "def shout(msg):           # side-effect: print is observable\n"
            "    print(msg.upper())\n"
            "    # no `return` → returns None\n"
            "\n"
            "x = square(4)             # x = 16\n"
            "y = shout('hi')           # prints HI; y is None\n"
            "```"
        ),
        play_widget_kind="code-stepper",
        play_widget={
            "title": "Step through a function call",
            "code": (
                "def square(n):\n"
                "    return n * n\n"
                "\n"
                "x = square(4)\n"
                "print(x)"
            ),
            "steps": [
                {"line": 4, "bindings": {}, "caption": "Call square(4). Push a frame for square."},
                {
                    "line": 1,
                    "bindings": {"n": "4"},
                    "caption": "Inside square: parameter n is bound to 4 in the new frame.",
                },
                {
                    "line": 2,
                    "bindings": {"n": "4"},
                    "caption": "Compute n * n = 16. Return value pops the frame.",
                },
                {
                    "line": 4,
                    "bindings": {"x": "16"},
                    "caption": "Back in the caller. x is bound to the returned 16.",
                },
                {"line": 5, "bindings": {"x": "16"}, "caption": "Print x → 16."},
            ],
        },
        check_mcqs=[
            {
                "q": (
                    "Which of these is a **pure** function?\n\n"
                    "```\n"
                    "def a(xs): xs.append(1); return xs\n"
                    "def b(xs): return xs + [1]\n"
                    "def c(): print('hi')\n"
                    "```"
                ),
                "options": ["a", "b", "c", "All three"],
                "correct": 1,
                "why": (
                    "b returns a new list and mutates nothing. "
                    "a mutates its argument; c prints (side effect)."
                ),
            },
            {
                "q": (
                    "What does this print?\n\n"
                    "```\n"
                    "def f(): pass\n"
                    "print(f())\n"
                    "```"
                ),
                "options": ["nothing", "0", "None", "Error"],
                "correct": 2,
                "why": "No `return` → implicitly returns None.",
            },
        ],
        apply_challenge_slug=None,
        reflect_question=(
            "In two sentences, distinguish a *pure* function from one with "
            "*side effects* — and explain why pure functions are easier to "
            "test."
        ),
        reflect_rubric={
            "must_mention": ["pure", "side effect", "return"],
            "must_distinguish": [["return value", "side effect"]],
            "must_explain": [
                "pure: same input always gives same output",
                "pure: no observable state change outside the function",
                "purity makes tests deterministic",
            ],
        },
        recall_checks=[
            {
                "kind": "mcq",
                "q": "A function with no `return` returns:",
                "options": ["0", "None", "the last expression"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "Reassigning a parameter inside a function affects the caller's binding?",
                "options": ["Yes", "No", "Only for ints"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "A pure function has:",
                "options": [
                    "no return value",
                    "no side effects and a deterministic return",
                    "no arguments",
                ],
                "correct": 1,
            },
        ],
    ),
    # ------------------------------------------------------------------
    # Concept 6: complexity — Big O, N vs operations, growth families.
    # Uses complexity-plotter. The Try is to estimate whether two algorithms
    # match in cost on the same input.
    # ------------------------------------------------------------------
    Concept(
        n=6,
        slug="complexity",
        layer="universal",
        title="Complexity",
        one_line="How the number of operations grows with the size of the input.",
        order_index=600,
        prereqs=["control-flow"],
        try_prompt_md=(
            "**Try.** Two functions, both finding the maximum of a list of "
            "N items:\n\n"
            "```python\n"
            "def max_a(xs):              # one pass\n"
            "    m = xs[0]\n"
            "    for x in xs:\n"
            "        if x > m: m = x\n"
            "    return m\n"
            "\n"
            "def max_b(xs):              # nested loop\n"
            "    for x in xs:\n"
            "        if all(x >= y for y in xs):\n"
            "            return x\n"
            "```\n\n"
            "Which one stays fast as N grows to 1,000,000? Sketch in one "
            "line *how* the cost grows for each."
        ),
        try_kind="text-reasoning",
        try_expected_attempts=[
            {
                "pattern": r"max_a|a\b",
                "callback_md": (
                    "Correct on which is faster. The Read explains why "
                    "max_a is O(N) and max_b is O(N²)."
                ),
            },
            {
                "pattern": r"max_b|b\b",
                "callback_md": (
                    "Counter-intuitive answer — the nested `all(...)` "
                    "inside the loop quietly makes max_b O(N²), so on "
                    "1M elements it's about a million times slower."
                ),
            },
        ],
        exposition_md=(
            "**Time complexity** measures how the number of operations "
            "grows as the input size N grows. We use Big-O notation to "
            "describe the growth *family*, not the exact count.\n\n"
            "The families you'll meet most:\n\n"
            "- **O(1)** — constant. Cost doesn't depend on N. Hash lookups, "
            "array indexing.\n"
            "- **O(log N)** — logarithmic. Cost grows very slowly. Binary "
            "search.\n"
            "- **O(N)** — linear. Cost scales with N. One pass over a list.\n"
            "- **O(N log N)** — linearithmic. Efficient sorts.\n"
            "- **O(N²)** — quadratic. Nested loops over the same list. "
            "Doubling N quadruples cost.\n"
            "- **O(2ⁿ)** — exponential. Avoid for any non-trivial N.\n\n"
            "Rule of thumb: every nested loop over the same data multiplies "
            "the exponent on N. A loop calling a function that itself loops "
            "over the input is O(N²), even if it doesn't *look* like a "
            "nested loop."
        ),
        worked_example_md=(
            "```python\n"
            "# O(N): one pass.\n"
            "def has_negative(xs):\n"
            "    for x in xs:\n"
            "        if x < 0: return True\n"
            "    return False\n"
            "\n"
            "# O(N²): hidden inner loop.\n"
            "def has_duplicate(xs):\n"
            "    for i, x in enumerate(xs):\n"
            "        if x in xs[i+1:]:        # `in` walks the slice\n"
            "            return True\n"
            "    return False\n"
            "\n"
            "# O(N): set membership is O(1) each.\n"
            "def has_duplicate_fast(xs):\n"
            "    return len(xs) != len(set(xs))\n"
            "```"
        ),
        play_widget_kind="complexity-plotter",
        play_widget={
            "title": "Growth families on a log/linear plot",
            "x_label": "N (input size)",
            "y_label": "operations",
            "curves": [
                {"label": "O(1)", "kind": "constant"},
                {"label": "O(log N)", "kind": "log"},
                {"label": "O(N)", "kind": "linear"},
                {"label": "O(N log N)", "kind": "nlogn"},
                {"label": "O(N²)", "kind": "quadratic"},
            ],
            "controls": {"max_n": {"min": 100, "max": 10000, "step": 100, "default": 1000}},
        },
        check_mcqs=[
            {
                "q": (
                    "What's the time complexity of this?\n\n"
                    "```\n"
                    "def f(xs):\n"
                    "    seen = set()\n"
                    "    for x in xs:\n"
                    "        seen.add(x)\n"
                    "    return len(seen)\n"
                    "```"
                ),
                "options": ["O(1)", "O(log N)", "O(N)", "O(N²)"],
                "correct": 2,
                "why": "Single pass through xs; set ops are O(1) on average.",
            },
            {
                "q": (
                    "If algorithm A takes 1 second on N = 1000 and is O(N²), "
                    "how long should it take on N = 10000?"
                ),
                "options": ["~10 seconds", "~100 seconds", "~1000 seconds", "~1 second"],
                "correct": 1,
                "why": "N grew 10×; cost grows as N² → 100×.",
            },
        ],
        apply_challenge_slug=None,
        reflect_question=(
            "In two sentences, explain what `O(N²)` means — and give one "
            "common code shape that produces it."
        ),
        reflect_rubric={
            "must_mention": ["input size", "operations", "grow"],
            "must_distinguish": [["O(N)", "O(N²)"]],
            "must_explain": [
                "operations grow as the square of the input size",
                "doubling N quadruples cost",
                "nested loops over the same data are the canonical source",
            ],
        },
        recall_checks=[
            {
                "kind": "mcq",
                "q": "Doubling N in an O(N²) algorithm multiplies cost by:",
                "options": ["2", "4", "8"],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "Hash-set membership is typically:",
                "options": ["O(1)", "O(log N)", "O(N)"],
                "correct": 0,
            },
            {
                "kind": "mcq",
                "q": "A single pass over a list is:",
                "options": ["O(1)", "O(N)", "O(N²)"],
                "correct": 1,
            },
        ],
    ),
    # ------------------------------------------------------------------
    # Concept 7: code as a state machine — first Layer-2 concept.
    # Uses state-machine-animator. Builds on control-flow.
    # ------------------------------------------------------------------
    Concept(
        n=7,
        slug="code-as-state-machine",
        layer="topic",
        topic_slug="mental-models",
        title="Code as a state machine",
        one_line="Many programs are finite states plus rules for transitioning between them.",
        order_index=700,
        prereqs=["control-flow"],
        try_prompt_md=(
            "**Try.** A traffic light cycles RED → GREEN → YELLOW → RED, "
            "one tick per second. Starting from RED at tick 0, what colour "
            "is the light at tick 5?"
        ),
        try_kind="text-reasoning",
        try_expected_attempts=[
            {
                "pattern": r"\bGREEN\b",
                "callback_md": (
                    "Correct: 0→RED, 1→GREEN, 2→YELLOW, 3→RED, 4→GREEN, "
                    "5→YELLOW. Wait — that's YELLOW. Re-check your trace; "
                    "the Read clarifies."
                ),
            },
            {
                "pattern": r"\bYELLOW\b",
                "callback_md": (
                    "Correct. Each transition advances exactly one state; "
                    "with three states the pattern repeats every 3 ticks."
                ),
            },
        ],
        exposition_md=(
            "Many programs are **state machines**: a finite set of "
            "named states, a starting state, and rules describing which "
            "state-to-state transitions an event triggers. Once you see "
            "code this way you can answer two questions reliably: 'what "
            "state am I in?' and 'which transitions are allowed from here?'\n\n"
            "Concrete examples in the wild:\n\n"
            "- A TCP connection: CLOSED → LISTEN → SYN_RCVD → ESTABLISHED → ...\n"
            "- A vending machine: IDLE → COIN_INSERTED → SELECTION_MADE → DISPENSING → IDLE\n"
            "- A form's submission flow: empty → in_progress → submitting → submitted | error\n\n"
            "When you draw the state diagram you stop forgetting "
            "transitions — and you catch impossible transitions (like "
            "DISPENSING → COIN_INSERTED) before they cause bugs.\n\n"
            "Code that *implements* a state machine often uses an enum "
            "for states and a dispatch dict (or `match` statement) for "
            "transitions. The bug is usually that someone introduced a "
            "fourth state but only updated three of the transition rules."
        ),
        worked_example_md=(
            "```python\n"
            "# Traffic light as an explicit state machine.\n"
            "NEXT = {'RED': 'GREEN', 'GREEN': 'YELLOW', 'YELLOW': 'RED'}\n"
            "\n"
            "state = 'RED'\n"
            "for tick in range(6):\n"
            "    print(tick, state)\n"
            "    state = NEXT[state]\n"
            "# 0 RED / 1 GREEN / 2 YELLOW / 3 RED / 4 GREEN / 5 YELLOW\n"
            "```\n\n"
            "The `NEXT` dict makes the transition rules *data*, not "
            "control-flow. Adding a state to the cycle is a one-line "
            "change; missing a transition is a KeyError at runtime, not "
            "a silent bug."
        ),
        play_widget_kind="state-machine-animator",
        play_widget={
            "title": "Traffic light cycle",
            "states": ["RED", "GREEN", "YELLOW"],
            "initial": "RED",
            "transitions": [
                {"from": "RED", "event": "tick", "to": "GREEN"},
                {"from": "GREEN", "event": "tick", "to": "YELLOW"},
                {"from": "YELLOW", "event": "tick", "to": "RED"},
            ],
        },
        check_mcqs=[
            {
                "q": (
                    "A vending machine has states IDLE, COIN_INSERTED, "
                    "DISPENSING. Which transition is most suspicious in a "
                    "real implementation?"
                ),
                "options": [
                    "IDLE → COIN_INSERTED on `insert_coin`",
                    "COIN_INSERTED → DISPENSING on `select`",
                    "DISPENSING → COIN_INSERTED on `insert_coin`",
                    "DISPENSING → IDLE on `done`",
                ],
                "correct": 2,
                "why": (
                    "Inserting a coin while dispensing is almost certainly "
                    "an error path — most state machines block input "
                    "during the busy state."
                ),
            },
            {
                "q": (
                    "Which is the best reason to model a workflow as an "
                    "explicit state machine in code?"
                ),
                "options": [
                    "It's faster at runtime",
                    "It makes invalid transitions visible — and catchable",
                    "It uses less memory",
                    "It avoids exceptions",
                ],
                "correct": 1,
                "why": (
                    "The structural win is debuggability — illegal "
                    "transitions become explicit instead of accidental."
                ),
            },
        ],
        apply_challenge_slug=None,
        reflect_question=(
            "In two sentences, explain what it means to model a piece of "
            "code as a *state machine* — and why doing so often makes "
            "bugs easier to spot."
        ),
        reflect_rubric={
            "must_mention": ["state", "transition", "explicit"],
            "must_distinguish": [["state", "transition"]],
            "must_explain": [
                "a state machine is a finite set of named states plus transition rules",
                "making transitions explicit data flags impossible transitions",
                "current-state plus allowed-transitions answers debugging questions reliably",
            ],
        },
        recall_checks=[
            {
                "kind": "mcq",
                "q": "A state machine is:",
                "options": [
                    "a class with no methods",
                    "a finite set of states + transition rules",
                    "any loop with break",
                ],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "Encoding transitions as data (e.g. a dict) helps because:",
                "options": [
                    "It's faster than if/elif",
                    "Adding a state is a one-line edit",
                    "It uses less memory",
                ],
                "correct": 1,
            },
            {
                "kind": "mcq",
                "q": "TCP, vending machines, and form workflows are all examples of:",
                "options": ["sorted data", "state machines", "pure functions"],
                "correct": 1,
            },
        ],
    ),
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
# APPLY SKELETONS — M2 (Apply made real)
# ============================================================================
#
# One tiny Pyodide skeleton per concept. Each is:
#   instructions_md: rendered above the runner
#   starter_code:    appears pre-filled in the textarea
#   hidden_test:     run by pytest; the learner does NOT see this directly
#
# The skeletons are intentionally small (~5-10 lines starter + ~5-10 lines
# test) — the goal is "apply the concept once on something runnable", not a
# full task. The challenges in the existing tracks remain the bigger lifts.

APPLY_SKELETONS: dict[str, dict] = {
    "variables-names": {
        "instructions_md": (
            "Write `update_in_place(target, source)` that copies every element "
            "of `source` into `target` **without rebinding `target`** — so the "
            "caller's reference still sees the new values."
        ),
        "starter_code": (
            "def update_in_place(target, source):\n"
            "    # TODO: mutate `target` so it ends up equal to `source`.\n"
            "    # Do not write `target = source` — that rebinds the parameter\n"
            "    # locally and the caller sees no change.\n"
            "    pass\n"
        ),
        "hidden_test": (
            "from solution import update_in_place\n"
            "\n"
            "def test_target_is_mutated():\n"
            "    a = [1, 2, 3]\n"
            "    original_id = id(a)\n"
            "    update_in_place(a, [9, 8, 7, 6])\n"
            "    assert a == [9, 8, 7, 6]\n"
            "    assert id(a) == original_id, (\n"
            "        'target was rebound; caller would not see the change'\n"
            "    )\n"
        ),
    },
    "references-values": {
        "instructions_md": (
            "Implement `add_one_safe(xs=None)` that appends `1` to `xs` and "
            "returns it — but does **not** share state across calls when no "
            "argument is passed. Use the None-sentinel pattern."
        ),
        "starter_code": (
            "def add_one_safe(xs=None):\n"
            "    # TODO: handle the default safely.\n"
            "    xs.append(1)\n"
            "    return xs\n"
        ),
        "hidden_test": (
            "from solution import add_one_safe\n"
            "\n"
            "def test_independent_calls():\n"
            "    assert add_one_safe() == [1]\n"
            "    assert add_one_safe() == [1]\n"
            "\n"
            "def test_caller_list_is_extended():\n"
            "    xs = [0]\n"
            "    out = add_one_safe(xs)\n"
            "    assert out == [0, 1]\n"
            "    assert xs is out\n"
        ),
    },
    "control-flow": {
        "instructions_md": (
            "Implement `count_evens(nums)` — return the number of even values "
            "in the iterable `nums`. Use a loop, not `sum(... % 2 == 0 ...)`."
        ),
        "starter_code": (
            "def count_evens(nums):\n"
            "    # TODO: iterate; count evens.\n"
            "    return 0\n"
        ),
        "hidden_test": (
            "from solution import count_evens\n"
            "\n"
            "def test_count_evens():\n"
            "    assert count_evens([]) == 0\n"
            "    assert count_evens([1, 3, 5]) == 0\n"
            "    assert count_evens([2, 4, 6]) == 3\n"
            "    assert count_evens([1, 2, 3, 4]) == 2\n"
        ),
    },
    "functions": {
        "instructions_md": (
            "Implement `apply_twice(fn, x)` — return `fn(fn(x))`. Then make "
            "sure `apply_twice(lambda v: v + 1, 5)` returns 7."
        ),
        "starter_code": (
            "def apply_twice(fn, x):\n"
            "    # TODO: call fn twice on x.\n"
            "    return x\n"
        ),
        "hidden_test": (
            "from solution import apply_twice\n"
            "\n"
            "def test_apply_twice():\n"
            "    assert apply_twice(lambda v: v + 1, 5) == 7\n"
            "    assert apply_twice(lambda v: v * 2, 3) == 12\n"
            "    assert apply_twice(str.upper, 'hi') == 'HI'\n"
        ),
    },
    "complexity": {
        "instructions_md": (
            "Implement `has_duplicate(xs)` in O(n) time — return True iff any "
            "value appears twice. The obvious O(n²) version (two nested loops) "
            "will time out on the large test."
        ),
        "starter_code": (
            "def has_duplicate(xs):\n"
            "    # TODO: O(n). A set is your friend.\n"
            "    return False\n"
        ),
        "hidden_test": (
            "from solution import has_duplicate\n"
            "\n"
            "def test_small():\n"
            "    assert has_duplicate([1, 2, 3]) is False\n"
            "    assert has_duplicate([1, 2, 1]) is True\n"
            "    assert has_duplicate([]) is False\n"
            "\n"
            "def test_large_unique():\n"
            "    # 5_000 unique values — naive O(n^2) would still finish here,\n"
            "    # but the next test forces the linear path.\n"
            "    assert has_duplicate(list(range(5_000))) is False\n"
            "\n"
            "def test_large_with_dup():\n"
            "    xs = list(range(5_000)) + [42]\n"
            "    assert has_duplicate(xs) is True\n"
        ),
    },
    "code-as-state-machine": {
        "instructions_md": (
            "Model a traffic light. `step(state)` returns the next state in the "
            "cycle `red → green → yellow → red`. Anything else raises "
            "`ValueError`."
        ),
        "starter_code": (
            "def step(state):\n"
            "    # TODO: red → green → yellow → red. Else: ValueError.\n"
            "    return state\n"
        ),
        "hidden_test": (
            "import pytest\n"
            "from solution import step\n"
            "\n"
            "def test_cycle():\n"
            "    assert step('red') == 'green'\n"
            "    assert step('green') == 'yellow'\n"
            "    assert step('yellow') == 'red'\n"
            "\n"
            "def test_invalid_state():\n"
            "    with pytest.raises(ValueError):\n"
            "        step('purple')\n"
        ),
    },
    "recursion": {
        "instructions_md": (
            "Implement `factorial(n)` recursively. Define `factorial(0) == 1` "
            "and `factorial(n) == n * factorial(n-1)`. Negative inputs raise "
            "`ValueError`."
        ),
        "starter_code": (
            "def factorial(n):\n"
            "    # TODO: base case + recursive case.\n"
            "    return 1\n"
        ),
        "hidden_test": (
            "import pytest\n"
            "from solution import factorial\n"
            "\n"
            "def test_base_case():\n"
            "    assert factorial(0) == 1\n"
            "    assert factorial(1) == 1\n"
            "\n"
            "def test_recursive():\n"
            "    assert factorial(5) == 120\n"
            "    assert factorial(7) == 5040\n"
            "\n"
            "def test_negative():\n"
            "    with pytest.raises(ValueError):\n"
            "        factorial(-1)\n"
        ),
    },
}

# Wire skeletons onto the CONCEPTS list. Done as a post-pass so the skeleton
# content lives in one block above (easier to scan + edit) and individual
# Concept constructors stay focused on the 6-stage content.
for _c in CONCEPTS:
    if _c.slug in APPLY_SKELETONS:
        _c.apply_skeleton = APPLY_SKELETONS[_c.slug]


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

    # M0 (non-destructive seed):
    #   - concept rows are UPSERTed by slug. No wipe.
    #   - concept_prereqs is replaced ONLY for the concept slugs we ship.
    #   - concept_mastery is NEVER touched. Re-running this seed preserves
    #     every learner's progress.
    #   - diagnostic_questions is wiped + reinserted for this track only;
    #     no foreign key references it, so this stays safe.
    #
    # The order matters: clear prereqs BEFORE upserting concepts (so removed
    # edges don't linger), then upsert, then insert the new edges.
    concept_slug_list = ", ".join(f"'{c.slug}'" for c in CONCEPTS)
    lines.append(
        "delete from public.concept_prereqs where concept_id in ("
        f"select id from public.concepts where slug in ({concept_slug_list}));"
    )
    lines.append(
        "delete from public.diagnostic_questions where track_slug = "
        f"'{TRACK_SLUG}';"
    )
    lines.append("")

    # Columns updated on conflict — everything except the natural key (slug)
    # and the surrogate id (which is also derived from the generator). Kept
    # in one constant so additions don't drift between insert + update.
    upsert_columns = (
        "layer",
        "topic_slug",
        "title",
        "one_line",
        "try_prompt_md",
        "try_kind",
        "try_expected_attempts_json",
        "exposition_md",
        "worked_example_md",
        "play_widget_kind",
        "play_widget_json",
        "check_mcqs_json",
        "apply_challenge_slug",
        "apply_skeleton_json",
        "reflect_question",
        "reflect_rubric_json",
        "recall_checks_json",
        "order_index",
    )

    for concept in CONCEPTS:
        lines.append("insert into public.concepts (")
        lines.append(
            "  id, slug, layer, topic_slug, title, one_line,"
            " try_prompt_md, try_kind, try_expected_attempts_json,"
            " exposition_md, worked_example_md,"
            " play_widget_kind, play_widget_json,"
            " check_mcqs_json, apply_challenge_slug, apply_skeleton_json,"
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
        if concept.apply_skeleton:
            lines.append(f"  {jsonb_lit(concept.apply_skeleton)},")
        else:
            lines.append("  null,")
        lines.append(f"  E'{sql_escape(concept.reflect_question)}',")
        lines.append(f"  {jsonb_lit(concept.reflect_rubric)},")
        lines.append(f"  {jsonb_lit(concept.recall_checks)},")
        lines.append(f"  {concept.order_index}")
        lines.append(")")
        lines.append("on conflict (slug) do update set")
        for i, col in enumerate(upsert_columns):
            suffix = "," if i < len(upsert_columns) - 1 else ";"
            lines.append(f"  {col} = excluded.{col}{suffix}")
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
