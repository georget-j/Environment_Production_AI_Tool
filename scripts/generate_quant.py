"""Generate the Quant Programmer track challenge SQL + TypeScript runner config.

Run from repo root:

    python scripts/generate_quant.py

Writes two files:

- supabase/quant_lessons_seed.generated.sql
    Idempotent INSERTs for each lesson into public.challenges, plus the
    skills graph. The track + 5 active modules (Stages 1–5) are already
    seeded by supabase/quant_programmer_seed.sql; this generator does not
    re-insert them.

- apps/web/src/lib/quant-config.generated.ts
    CHALLENGE_CONFIG entries for each lesson, keyed by slug.

Lesson modes supported (extending Python Basics' 'predict' + 'fillblank'):
- 'matplot'  — Python + matplotlib; SVG captured + rendered inline.
- 'cscript'  — editable C in the picoc interpreter (CDN).
- 'cwasm'    — read-only C source + a Run button that loads a pre-built
               Emscripten WASM demo from /wasm/quant/<slug>.js.

Same 4-part instruction template as Python Basics (60–80 words):
    **Concept.** ...
    **Example.** ```python (or c) ...```
    **Your turn.** ... (predict-mode uses "Predict.")
    **Expected.** `...`
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK_UUID = "00000000-0000-0000-0000-000000000003"

# Module UUIDs must match supabase/quant_programmer_seed.sql.
# Stage 1 → …0031, Stage 2 → …0032, …, Stage 5 → …0035.
STAGE_MODULE_UUID = {
    1: "00000000-0000-0000-0000-000000000031",
    2: "00000000-0000-0000-0000-000000000032",
    3: "00000000-0000-0000-0000-000000000033",
    4: "00000000-0000-0000-0000-000000000034",
    5: "00000000-0000-0000-0000-000000000035",
}

LESSON_MODES = frozenset({"predict", "fillblank", "matplot", "cscript", "cwasm"})
EXAMPLE_LANGUAGE_FOR_MODE = {
    "predict": "python",
    "fillblank": "python",
    "matplot": "python",
    "cscript": "c",
    "cwasm": "c",
}


@dataclass
class Lesson:
    """One quant lesson. Same shape across all modes; only the mode-specific
    payload fields differ. Unused fields stay empty strings.

    n              global lesson number (1..N) — drives the UUID and the slug
    stage          which Stage (1..5) the lesson belongs to (maps to a module)
    title, scenario, learner_goal: as Python Basics
    mode           one of LESSON_MODES
    concept / example_code / your_turn: the 4-part instruction template
    expected_stdout / hint: how the lesson is scored
    code           predict-only — read-only snippet shown to the learner
    template       fillblank / matplot / cscript — Monaco initial content
    source         cwasm only — the .c source rendered read-only
    wasm_demo      cwasm only — slug under /wasm/quant/<slug>.js
    expected_stdout_contains: cwasm only — substring match for pass
    skills         array of skill slugs (joins into the skills table)
    """

    n: int
    stage: int
    title: str
    mode: str
    scenario: str
    learner_goal: str
    concept: str
    example_code: str
    your_turn: str

    expected_stdout: str = ""
    expected_stdout_contains: str = ""
    code: str = ""
    template: str = ""
    source: str = ""
    wasm_demo: str = ""
    prompt: str = ""
    hint: str = ""
    skills: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in LESSON_MODES:
            raise ValueError(f"lesson {self.n}: unknown mode {self.mode!r}")
        if self.stage not in STAGE_MODULE_UUID:
            raise ValueError(f"lesson {self.n}: stage {self.stage} not in 1..5")

    @property
    def slug(self) -> str:
        kebab = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return f"quant-{self.n:02d}-{kebab}"

    @property
    def uuid(self) -> str:
        # Use the 0x300 .. 0x3ff range; Python Basics uses 0x200..0x2ff.
        return f"00000000-0000-0000-0000-{0x300 + (self.n - 1):012x}"

    @property
    def module_uuid(self) -> str:
        return STAGE_MODULE_UUID[self.stage]

    def instructions(self) -> str:
        lang = EXAMPLE_LANGUAGE_FOR_MODE[self.mode]
        lines = [
            f"**Concept.** {self.concept.strip()}",
            "",
            "**Example.**",
            "",
            f"```{lang}",
            self.example_code.strip("\n"),
            "```",
            "",
        ]
        if self.mode == "predict":
            lines.append(f"**Predict.** {self.your_turn.strip()}")
        else:
            lines.append(f"**Your turn.** {self.your_turn.strip()}")
        lines.append("")
        expected = self.expected_stdout or self.expected_stdout_contains
        expected_one_line = expected.replace("\n", " · ")
        if expected_one_line:
            lines.append(f"**Expected.** `{expected_one_line}`")
        return "\n".join(lines)

    def runner_config(self) -> dict[str, object]:
        if self.mode == "predict":
            payload: dict[str, object] = {
                "mode": "predict",
                "code": self.code,
                "expected_stdout": self.expected_stdout,
            }
            if self.prompt:
                payload["prompt"] = self.prompt
            return payload
        if self.mode == "fillblank":
            payload = {
                "mode": "fillblank",
                "template": self.template,
                "expected_stdout": self.expected_stdout,
            }
            if self.hint:
                payload["hint"] = self.hint
            return payload
        if self.mode == "matplot":
            payload = {"mode": "matplot", "template": self.template}
            if self.expected_stdout:
                payload["expected_stdout"] = self.expected_stdout
            if self.hint:
                payload["hint"] = self.hint
            return payload
        if self.mode == "cscript":
            payload = {
                "mode": "cscript",
                "template": self.template,
                "expected_stdout": self.expected_stdout,
            }
            if self.hint:
                payload["hint"] = self.hint
            return payload
        if self.mode == "cwasm":
            payload = {
                "mode": "cwasm",
                "source": self.source,
                "wasm_demo": self.wasm_demo,
                "expected_stdout_contains": self.expected_stdout_contains,
            }
            if self.hint:
                payload["hint"] = self.hint
            return payload
        raise ValueError(f"unhandled mode {self.mode}")


# Skill catalogue used by the quant track. Keep slugs short and lowercase.
SKILL_TITLES: dict[str, str] = {
    "quant": "Quantitative finance",
    "numpy": "NumPy",
    "vectorisation": "Vectorisation",
    "linear-algebra": "Linear algebra",
    "random-numbers": "Random number generation",
    "matplotlib": "Matplotlib",
    "pandas": "pandas",
    "time-series": "Time series",
    "statistics": "Statistics",
    "regression": "Regression",
    "options": "Options",
    "black-scholes": "Black-Scholes",
    "greeks": "Greeks",
    "monte-carlo": "Monte Carlo",
    "portfolio": "Portfolio theory",
    "risk-metrics": "Risk metrics",
    "machine-learning": "Machine learning",
    "backtesting": "Backtesting",
    "performance": "Performance engineering",
    "c-language": "C language",
    "memory": "Memory & layout",
    "low-latency": "Low latency",
}


# fmt: off
LESSONS: list[Lesson] = [
    # ============ Stage 1 — Numerical Python (10 lessons) ============
    Lesson(
        n=1, stage=1, mode="predict",
        title="Why numpy",
        scenario="Python's for-loops feel friendly until you sum a million numbers. numpy's array operations push the work down into C — same answer, ~50× faster.",
        learner_goal="See the speed gap between pure Python and numpy on a simple sum.",
        concept="numpy arrays look like Python lists but store data contiguously in memory and operate on it in compiled code. The same logical work runs an order of magnitude faster — without any loop appearing in your Python.",
        example_code=(
            "import numpy as np, time\n"
            "n = 1_000_000\n"
            "xs = list(range(n))\n"
            "arr = np.arange(n)\n"
            "print(sum(xs) == int(arr.sum()))"
        ),
        code=(
            "import numpy as np, time\n"
            "n = 1_000_000\n"
            "xs = list(range(n))\n"
            "arr = np.arange(n)\n"
            "print(sum(xs) == int(arr.sum()))"
        ),
        your_turn="Both compute the same sum 0+1+…+999999. Predict the printed result.",
        expected_stdout="True",
        prompt="True or False?",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=2, stage=1, mode="fillblank",
        title="Creating arrays",
        scenario="Three constructors handle 95% of real array creation: a literal list, all-zeros of a given shape, and an evenly-spaced range.",
        learner_goal="Use np.array, np.zeros, and np.linspace to build arrays from different starting points.",
        concept="`np.array([…])` lifts a Python list. `np.zeros(n)` allocates `n` zeros. `np.linspace(start, stop, n)` returns `n` evenly spaced points including both endpoints — the canonical x-axis builder.",
        example_code=(
            "import numpy as np\n"
            "a = np.array([1.0, 2.0, 3.0])\n"
            "b = np.zeros(3)\n"
            "c = np.linspace(0, 1, 5)\n"
            "print(a, b, c, sep=' | ')"
        ),
        template=(
            "import numpy as np\n"
            "a = np.array([1.0, 2.0, 3.0])\n"
            "b = np.___(3)\n"
            "c = np.___(0, 1, 5)\n"
            "print(a, b, c, sep=' | ')"
        ),
        your_turn="Fill the blanks so the output shows the literal, three zeros, and five evenly-spaced points from 0 to 1.",
        expected_stdout="[1. 2. 3.] | [0. 0. 0.] | [0.   0.25 0.5  0.75 1.  ]",
        hint="One blank is `zeros`, the other is `linspace`.",
        skills=["quant", "numpy"],
    ),
    Lesson(
        n=3, stage=1, mode="predict",
        title="Broadcasting",
        scenario="When you add a 1-D array to a 2-D array, numpy stretches the smaller one along the missing axis. It saves you from writing nested loops.",
        learner_goal="Read a broadcast expression and predict the resulting shape and values.",
        concept="If a `(3,)` array meets a `(4, 3)` array, numpy treats the row as if repeated four times. The shapes must align from the trailing axis — `(3,)` vs `(4, 3)` works; `(4,)` vs `(4, 3)` doesn't.",
        example_code=(
            "import numpy as np\n"
            "M = np.zeros((4, 3))\n"
            "row = np.array([10, 20, 30])\n"
            "print(M + row)"
        ),
        code=(
            "import numpy as np\n"
            "M = np.zeros((4, 3))\n"
            "row = np.array([10, 20, 30])\n"
            "print((M + row)[0])"
        ),
        your_turn="The first row of `M + row` is printed. What does it look like?",
        expected_stdout="[10. 20. 30.]",
        prompt="Type the row exactly as numpy prints it.",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=4, stage=1, mode="fillblank",
        title="Boolean masks",
        scenario="A boolean mask is an array of True/False the same shape as your data. Indexing with it keeps the True entries — a vectorised filter.",
        learner_goal="Keep only the positive entries of an array using a boolean mask.",
        concept="`arr > 0` returns a boolean array of the same shape. Using it as an index (`arr[mask]`) returns just the elements where the mask is True. No loops, no list comprehension — pure vectorised filtering.",
        example_code=(
            "import numpy as np\n"
            "r = np.array([-0.02, 0.01, -0.005, 0.015, 0.0, 0.03])\n"
            "positive = r[r > 0]\n"
            "print(positive)"
        ),
        template=(
            "import numpy as np\n"
            "r = np.array([-0.02, 0.01, -0.005, 0.015, 0.0, 0.03])\n"
            "positive = r[r ___ 0]\n"
            "print(positive)"
        ),
        your_turn="Replace `___` with the operator that keeps strictly positive returns only.",
        expected_stdout="[0.01  0.015 0.03 ]",
        hint="Strictly positive — zero doesn't count.",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=5, stage=1, mode="fillblank",
        title="Covariance via matrix algebra",
        scenario="Covariance between asset returns underpins portfolio theory. The textbook formula `(X - μ).T @ (X - μ) / n` is one line of numpy.",
        learner_goal="Compute a 2x2 covariance matrix from two return series using matrix multiplication.",
        concept="Stack two demeaned return series as columns of `X` (shape `(n, 2)`). Then `X.T @ X / n` is the 2x2 covariance matrix. The diagonal is each series' variance; off-diagonal is their covariance.",
        example_code=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "X = rng.normal(size=(1000, 2))\n"
            "Xd = X - X.mean(axis=0)\n"
            "cov = Xd.T @ Xd / X.shape[0]\n"
            "print(np.round(cov, 2))"
        ),
        template=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "X = rng.normal(size=(1000, 2))\n"
            "Xd = X - X.mean(axis=0)\n"
            "cov = Xd.___ @ Xd / X.shape[0]\n"
            "print(np.round(cov, 2))"
        ),
        your_turn="Replace `___` with the attribute that transposes the matrix.",
        expected_stdout="[[ 1.04 -0.02]\n [-0.02  0.96]]",
        hint="Two-letter attribute on every numpy array.",
        skills=["quant", "numpy", "linear-algebra", "statistics"],
    ),
    Lesson(
        n=6, stage=1, mode="fillblank",
        title="Reproducible random numbers",
        scenario="Every backtest you write touches a random number generator. Seeding it makes your work reproducible — same input, same answer.",
        learner_goal="Generate two arrays of standard-normal draws and confirm the seed makes them identical.",
        concept="`np.random.default_rng(seed)` returns a Generator. Same seed in, same draws out — every time. The legacy `np.random.seed` global is fine for scripts; default_rng is the modern, thread-safe API.",
        example_code=(
            "import numpy as np\n"
            "a = np.random.default_rng(42).normal(size=3)\n"
            "b = np.random.default_rng(42).normal(size=3)\n"
            "print(np.array_equal(a, b))"
        ),
        template=(
            "import numpy as np\n"
            "a = np.random.default_rng(___).normal(size=3)\n"
            "b = np.random.default_rng(42).normal(size=3)\n"
            "print(np.array_equal(a, b))"
        ),
        your_turn="Replace `___` so both generators draw the same sequence.",
        expected_stdout="True",
        hint="Use 42.",
        skills=["quant", "numpy", "random-numbers"],
    ),
    Lesson(
        n=7, stage=1, mode="fillblank",
        title="Statistical reductions",
        scenario="Mean, standard deviation, and percentiles let you summarise a return distribution in one line each — they're the vocabulary of every research note.",
        learner_goal="Compute the mean, standard deviation, and 95th percentile of a sample.",
        concept="numpy reductions take an axis (or none, for the whole array). `arr.mean()` and `arr.std()` are methods; `np.percentile(arr, q)` is a function — `q` is in 0–100, not 0–1.",
        example_code=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "r = rng.normal(loc=0.001, scale=0.02, size=10_000)\n"
            "print(round(r.mean(), 4), round(r.std(), 4), round(np.percentile(r, 95), 4))"
        ),
        template=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "r = rng.normal(loc=0.001, scale=0.02, size=10_000)\n"
            "print(round(r.___(), 4), round(r.___(), 4), round(np.___(r, 95), 4))"
        ),
        your_turn="Fill the three blanks with the reduction names.",
        expected_stdout="0.0011 0.02 0.0338",
        hint="Two methods, one function. All three are short, common names.",
        skills=["quant", "numpy", "statistics"],
    ),
    Lesson(
        n=8, stage=1, mode="predict",
        title="Why numpy is fast",
        scenario="numpy's headline numbers don't come from magic — they come from C. Real quant libraries like HFT-Orderbook ship pure-Python LOBs that show exactly what 'slow' looks like.",
        learner_goal="Recognise that numpy is fast because the inner loop is compiled C, not Python.",
        concept="numpy stores arrays as contiguous C buffers and runs ufuncs as tight C loops with no Python overhead per element. The same loop in pure Python pays interpreter overhead per iteration — typically 50–100× slower.",
        example_code=(
            "import numpy as np\n"
            "x = np.arange(1_000_000)\n"
            "# Both compute (1+2+...+999999) but only one is a Python loop.\n"
            "print(int(x.sum()))"
        ),
        code=(
            "import numpy as np\n"
            "x = np.arange(1_000_000)\n"
            "print(int(x.sum()))"
        ),
        your_turn="Predict the printed sum of 0..999999.",
        expected_stdout="499999500000",
        prompt="Type the integer.",
        skills=["quant", "numpy", "performance"],
    ),
    Lesson(
        n=9, stage=1, mode="fillblank",
        title="Vectorising a rolling mean",
        scenario="A 30-day rolling mean of returns is one of the most common features in quant work. The naive loop is O(n*window); numpy's cumulative-sum trick makes it O(n).",
        learner_goal="Replace a Python for-loop with `np.cumsum` to compute a rolling mean.",
        concept="If `c = np.cumsum(x)`, then the window-`w` sum ending at index `i` is `c[i] - c[i-w]`. Divide by `w` for the mean. One pass, no inner loop.",
        example_code=(
            "import numpy as np\n"
            "x = np.array([1, 2, 3, 4, 5, 6], dtype=float)\n"
            "w = 3\n"
            "c = np.concatenate(([0], np.cumsum(x)))\n"
            "roll = (c[w:] - c[:-w]) / w\n"
            "print(roll)"
        ),
        template=(
            "import numpy as np\n"
            "x = np.array([1, 2, 3, 4, 5, 6], dtype=float)\n"
            "w = 3\n"
            "c = np.concatenate(([0], np.___(x)))\n"
            "roll = (c[w:] - c[:-w]) / w\n"
            "print(roll)"
        ),
        your_turn="Fill in the cumulative-sum function name.",
        expected_stdout="[2. 3. 4. 5.]",
        hint="It's literally called the cumulative sum.",
        skills=["quant", "numpy", "vectorisation", "performance"],
    ),
    Lesson(
        n=10, stage=1, mode="matplot",
        title="Plot a price path",
        scenario="Every quant chart starts with `plt.plot`. Get the first one right — labeled axes, a title — and the rest follow.",
        learner_goal="Plot a simulated geometric Brownian motion price path with labelled axes.",
        concept="`plt.plot(x, y)` draws a line. `plt.xlabel`, `plt.ylabel`, `plt.title` annotate the chart. matplotlib's pyplot API mirrors MATLAB — one statement per directive.",
        example_code=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "rng = np.random.default_rng(0)\n"
            "shocks = rng.normal(0, 0.01, 252)\n"
            "price = 100 * np.exp(np.cumsum(shocks))\n"
            "plt.plot(price)\n"
            "plt.title('Simulated price path'); plt.xlabel('day'); plt.ylabel('price')\n"
            "print('plotted')"
        ),
        template=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "rng = np.random.default_rng(0)\n"
            "shocks = rng.normal(0, 0.01, 252)\n"
            "price = 100 * np.exp(np.cumsum(shocks))\n"
            "plt.plot(___)\n"
            "plt.title('Simulated price path'); plt.xlabel('day'); plt.ylabel('price')\n"
            "print('plotted')"
        ),
        your_turn="Replace `___` with the variable holding the price series.",
        expected_stdout="plotted",
        hint="It's a single variable name.",
        skills=["quant", "numpy", "matplotlib", "monte-carlo"],
    ),
]
# fmt: on


def sql_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n")


def write_sql() -> Path:
    lines: list[str] = []
    lines.append("-- AUTO-GENERATED by scripts/generate_quant.py")
    lines.append("-- Quant track challenge inserts. Track + modules live in")
    lines.append("-- supabase/quant_programmer_seed.sql — apply that first.")
    lines.append("")

    for lesson in LESSONS:
        skills_array = (
            "array["
            + ", ".join(f"'{sql_escape(s)}'" for s in lesson.skills)
            + "]"
        )
        lines.append(
            "insert into public.challenges (\n"
            "  id, module_id, slug, title, scenario, learner_goal, instructions,\n"
            "  repo_template_url, repo_branch, validation_config_json, ai_rules_json,\n"
            "  skills, is_free, order_index\n"
            ") values ("
        )
        lines.append(f"  '{lesson.uuid}',")
        lines.append(f"  '{lesson.module_uuid}',")
        lines.append(f"  '{lesson.slug}',")
        lines.append(f"  E'{sql_escape(lesson.title)}',")
        lines.append(f"  E'{sql_escape(lesson.scenario)}',")
        lines.append(f"  E'{sql_escape(lesson.learner_goal)}',")
        lines.append(f"  E'{sql_escape(lesson.instructions())}',")
        lines.append("  null,")
        lines.append("  null,")
        lines.append("  '{}',")
        lines.append(
            "  '{\"max_hint_level\": 2, \"do_not_reveal_solution\": false,"
            ' "encourage_tests_first": false}\','
        )
        lines.append(f"  {skills_array},")
        lines.append("  true,")
        lines.append(f"  {lesson.n}")
        lines.append(")")
        lines.append("on conflict (slug) do update set")
        lines.append(
            "  module_id = excluded.module_id,\n"
            "  title = excluded.title,\n"
            "  scenario = excluded.scenario,\n"
            "  learner_goal = excluded.learner_goal,\n"
            "  instructions = excluded.instructions,\n"
            "  repo_template_url = excluded.repo_template_url,\n"
            "  repo_branch = excluded.repo_branch,\n"
            "  validation_config_json = excluded.validation_config_json,\n"
            "  ai_rules_json = excluded.ai_rules_json,\n"
            "  skills = excluded.skills,\n"
            "  is_free = excluded.is_free,\n"
            "  order_index = excluded.order_index;"
        )
        lines.append("")

    used_skills = sorted({s for lesson in LESSONS for s in lesson.skills})
    if used_skills:
        lines.append("insert into public.skills (slug, name) values")
        rows = [
            f"  ('{s}', '{sql_escape(SKILL_TITLES.get(s, s.title()))}')"
            for s in used_skills
        ]
        lines.append(",\n".join(rows))
        lines.append("on conflict (slug) do update set name = excluded.name;")
        lines.append("")

    out_path = ROOT / "supabase" / "quant_lessons_seed.generated.sql"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_ts() -> Path:
    entries: list[str] = []
    for lesson in LESSONS:
        payload = lesson.runner_config()
        entries.append(f"  {json.dumps(lesson.slug)}: {json.dumps(payload, indent=2)},")

    body = (
        "// AUTO-GENERATED by scripts/generate_quant.py\n"
        "// Runner config for the Quant Programmer track lessons.\n\n"
        'import type { ChallengeRunnerConfig } from "@/lib/featured-files";\n\n'
        "export const QUANT_CONFIG: Record<string, ChallengeRunnerConfig> = {\n"
        + ("\n".join(entries) if entries else "  // (no lessons defined yet)")
        + "\n};\n"
    )
    out_path = ROOT / "apps" / "web" / "src" / "lib" / "quant-config.generated.ts"
    out_path.write_text(body, encoding="utf-8")
    return out_path


def word_count_report() -> None:
    if not LESSONS:
        print("\n(no lessons yet — fill in LESSONS list and re-run)")
        return
    print("\nInstruction word counts:")
    for lesson in LESSONS:
        wc = len(lesson.instructions().split())
        print(f"  {lesson.slug}: {wc} words")


if __name__ == "__main__":
    if TRACK_UUID != "00000000-0000-0000-0000-000000000003":
        raise SystemExit("TRACK_UUID changed — keep it consistent with quant_programmer_seed.sql")
    sql_path = write_sql()
    ts_path = write_ts()
    print(f"Wrote {sql_path.relative_to(ROOT)}")
    print(f"Wrote {ts_path.relative_to(ROOT)}")
    word_count_report()
