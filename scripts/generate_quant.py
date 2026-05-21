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

LESSON_MODES = frozenset(
    {
        "predict",
        "fillblank",
        "matplot",
        "cscript",
        "cwasm",
        "debug",
        "skeleton",
        "apifetch",
    }
)
EXAMPLE_LANGUAGE_FOR_MODE = {
    "predict": "python",
    "fillblank": "python",
    "matplot": "python",
    "cscript": "c",
    "cwasm": "c",
    "debug": "python",
    "skeleton": "python",
    "apifetch": "python",
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
    # Bundled CSV slugs the lesson reads. The worker pre-mounts each under
    # /data/quant/<slug>.csv inside Pyodide's FS before the user code runs.
    datasets: list[str] = field(default_factory=list)

    # debug / skeleton / apifetch modes share these fields:
    #   editable_template: contents of solution.py the learner edits.
    #     - For "debug": working-LOOKING code with one (occasionally two)
    #       subtle bug(s) that make at least one test fail.
    #     - For "skeleton": function signature + docstring + raise
    #       NotImplementedError(...) — the learner implements the body.
    #     - For "apifetch": same shape as skeleton but the body must
    #       use the mock_api.py module's HTTP-like client to fetch data.
    #   tests_py: contents of tests/test_solution.py (readonly). Discovered
    #     by pytest automatically; same shape as the project tests.
    #   reference_solution: the correct implementation. NEVER shipped to
    #     the learner — verifier-only, proves the tests are well-formed.
    editable_template: str = ""
    tests_py: str = ""
    reference_solution: str = ""
    # apifetch-only: contents of mock_api.py (readonly). A small module
    # that imitates a requests-shaped HTTP client. The learner reads it
    # to discover the available endpoints, then writes the client code
    # in solution.py.
    mock_api_py: str = ""
    # List of (pytest_id, description) pairs for the TestCase[] array in
    # the generated TS config. Description shown in the runner's tests
    # panel before the learner clicks Run.
    pytest_targets: list[tuple[str, str]] = field(default_factory=list)

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
        # debug / skeleton / apifetch lessons render a different shape —
        # no "**Example.**" block (which would give away the bug or
        # solution), and the action label changes to fit the task. The
        # editor itself IS the example in those modes.
        if self.mode in ("debug", "skeleton", "apifetch"):
            action_label = {
                "debug": "**Find the bug.** ",
                "skeleton": "**Implement the function.** ",
                "apifetch": "**Build the client.** ",
            }[self.mode]
            lines = [
                f"**Concept.** {self.concept.strip()}",
                "",
                f"{action_label}{self.your_turn.strip()}",
                "",
                "**Expected.** All tests pass.",
            ]
            if self.mode == "apifetch":
                lines.insert(
                    -2,
                    "Read **`mock_api.py`** for the available endpoints and the "
                    "shape of the `Response` object. Use it from "
                    "`solution.py` to fetch what you need.",
                )
                lines.insert(-2, "")
            return "\n".join(lines)
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
            if self.datasets:
                payload["datasets"] = list(self.datasets)
            return payload
        if self.mode == "matplot":
            payload = {"mode": "matplot", "template": self.template}
            if self.expected_stdout:
                payload["expected_stdout"] = self.expected_stdout
            if self.hint:
                payload["hint"] = self.hint
            if self.datasets:
                payload["datasets"] = list(self.datasets)
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
        if self.mode in ("debug", "skeleton", "apifetch"):
            # All three modes emit the same pyodide shape; only the inline
            # file map differs. apifetch adds a readonly mock_api.py the
            # learner reads to discover the available endpoints.
            readonly_files = ["tests/test_solution.py"]
            inline_map: dict[str, str] = {
                "solution.py": self.editable_template,
                "tests/test_solution.py": self.tests_py,
            }
            if self.mode == "apifetch":
                readonly_files.insert(0, "mock_api.py")
                inline_map["mock_api.py"] = self.mock_api_py
            payload = {
                "mode": "pyodide",
                "editable": ["solution.py"],
                "readonly": readonly_files,
                "tests": [
                    {"id": pid, "description": desc}
                    for pid, desc in self.pytest_targets
                ],
                "inline": inline_map,
            }
            if self.datasets:
                payload["datasets"] = list(self.datasets)
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
    # ============ Stage 1 — Numerical Python (13 lessons, v2) ============
    Lesson(
        n=1, stage=1, mode="predict",
        title="Why numpy",
        scenario="First morning at AQR. Your manager hands you a notebook with 7 years of minute-bar SPY data — 12 million rows — and wants a 10-day momentum signal by lunch. In pure Python the iteration would take 6 minutes per run; in numpy it's 4 seconds. That gap is the whole reason quants live in numpy.",
        learner_goal="Measure the real speed gap between a Python sum and a numpy sum on a million numbers.",
        concept="numpy arrays store fixed-size numbers contiguously in memory. A `.sum()` runs as one C loop with no Python interpreter overhead per element — typically 50-100× faster than the equivalent Python for-loop. The work being done is identical; the dispatch cost is what disappears.",
        example_code=(
            "import numpy as np, time\n"
            "n = 1_000_000\n"
            "xs = list(range(n))\n"
            "arr = np.arange(n)\n"
            "\n"
            "t0 = time.perf_counter()\n"
            "s1 = sum(xs)\n"
            "t1 = time.perf_counter()\n"
            "s2 = int(arr.sum())\n"
            "t2 = time.perf_counter()\n"
            "\n"
            "print(f'loop:  {(t1-t0)*1e3:6.1f}ms')\n"
            "print(f'numpy: {(t2-t1)*1e3:6.1f}ms')\n"
            "print('answers match:', s1 == s2)"
        ),
        code=(
            "import numpy as np\n"
            "n = 1_000_000\n"
            "xs = list(range(n))\n"
            "arr = np.arange(n)\n"
            "print(sum(xs) == int(arr.sum()))"
        ),
        your_turn="Both compute the same sum 0+1+…+999999. Predict the boolean result.",
        expected_stdout="True",
        prompt="True or False?",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=2, stage=1, mode="fillblank",
        title="Creating arrays",
        scenario="The Citadel research team's morning ritual: load yesterday's tape, slice it, line it up against a benchmark grid. Three constructors handle nearly every input you'll ever build — `np.array` for known data, `np.zeros` for pre-allocated buffers, `np.linspace` for evenly-spaced sampling grids (the canonical y-axis builder for IV surfaces).",
        learner_goal="Use np.array, np.zeros, and np.linspace to build the three array shapes you'll actually use.",
        concept="`np.array([…])` lifts a Python list. `np.zeros(n)` pre-allocates `n` zeros — useful when you'll fill values in a loop. `np.linspace(start, stop, n)` returns `n` evenly spaced points including both endpoints — used for plot grids and parameter sweeps.",
        example_code=(
            "import numpy as np\n"
            "# A literal list — known coupon rates on three bonds.\n"
            "coupons = np.array([0.025, 0.032, 0.041])\n"
            "# Pre-allocated buffer for tomorrow's signals.\n"
            "signals = np.zeros(252)\n"
            "# Evenly-spaced strikes for an IV surface — 80% to 120% of spot.\n"
            "strikes = np.linspace(80, 120, 5)\n"
            "print(coupons, signals[:3], strikes, sep=' | ')"
        ),
        template=(
            "import numpy as np\n"
            "coupons = np.array([0.025, 0.032, 0.041])\n"
            "signals = np.___(252)\n"
            "strikes = np.___(80, 120, 5)\n"
            "print(coupons, signals[:3], strikes, sep=' | ')"
        ),
        your_turn="Fill the two blanks: zero-buffer for `signals`, evenly-spaced grid for `strikes`.",
        expected_stdout="[0.025 0.032 0.041] | [0. 0. 0.] | [ 80.  90. 100. 110. 120.]",
        hint="One is `zeros`, the other is `linspace`.",
        skills=["quant", "numpy"],
    ),
    Lesson(
        n=3, stage=1, mode="predict",
        title="Broadcasting basics",
        scenario="Your strategy holds 4 positions on each of 3 days. You want to subtract the risk-free rate (a single 3-day vector) from every row of returns. Two for-loops? No. numpy's broadcasting handles it as one expression — adds about a microsecond, regardless of how many positions you have.",
        learner_goal="Read a broadcast subtraction and predict the resulting first row.",
        concept="When a `(3,)` vector meets a `(4, 3)` matrix, numpy implicitly stretches the vector along the missing axis — as if you'd repeated it four times. Shapes must align from the *trailing* axis. The big win is no temporary copies — the C loop just reuses the smaller buffer.",
        example_code=(
            "import numpy as np\n"
            "# 4 positions × 3 days of raw daily returns.\n"
            "raw = np.full((4, 3), 0.012)\n"
            "# Risk-free rate per day (3-vector).\n"
            "rf = np.array([0.0001, 0.0001, 0.0002])\n"
            "excess = raw - rf\n"
            "print(excess[0])"
        ),
        code=(
            "import numpy as np\n"
            "raw = np.full((4, 3), 0.012)\n"
            "rf = np.array([0.0001, 0.0001, 0.0002])\n"
            "excess = raw - rf\n"
            "print(excess[0])"
        ),
        your_turn="Predict the first row of `excess` — the 4-position raw returns minus the 3-day risk-free vector.",
        expected_stdout="[0.0119 0.0119 0.0118]",
        prompt="Type the row as numpy prints it.",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=4, stage=1, mode="predict",
        title="Broadcasting gotchas",
        scenario="Most numpy errors a junior research engineer raises are shape mismatches. Take 30 seconds to learn what 'can't broadcast (4,) with (4, 3)' actually means — then you'll fix it in 30 seconds instead of 30 minutes.",
        learner_goal="Recognise when shapes do not align and how to reshape to make them.",
        concept="Broadcasting aligns dimensions from the *right*. A `(4,)` vector vs a `(4, 3)` matrix doesn't align — the trailing dimensions are 4 and 3. Reshape the vector to `(4, 1)` (a column) and now the trailing dimensions are 1 and 3 — broadcastable, because size-1 axes stretch.",
        example_code=(
            "import numpy as np\n"
            "raw = np.full((4, 3), 0.01)\n"
            "weights = np.array([1.0, 0.5, 2.0, 1.5])  # one per position\n"
            "# This would fail: raw - weights  (shapes (4,3) vs (4,) — won't align)\n"
            "# Reshape to a column so each row of `raw` gets its own weight:\n"
            "scaled = raw * weights.reshape(4, 1)\n"
            "print(scaled[:, 0])"
        ),
        code=(
            "import numpy as np\n"
            "raw = np.full((4, 3), 0.01)\n"
            "weights = np.array([1.0, 0.5, 2.0, 1.5])\n"
            "scaled = raw * weights.reshape(4, 1)\n"
            "print(scaled[:, 0])"
        ),
        your_turn="`scaled` is shape (4, 3) with each row multiplied by its weight. Predict its first column.",
        expected_stdout="[0.01  0.005 0.02  0.015]",
        prompt="Type the column as numpy prints it.",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=5, stage=1, mode="fillblank",
        title="Boolean masks",
        scenario="You're scanning a day of NYSE trade prints for outliers — anything more than 2 standard deviations above the running mean. The pure-Python way: a for-loop with an if. The numpy way: one comparison, one indexing operation, no loop. Every research desk uses this pattern daily.",
        learner_goal="Filter an array of returns to keep only the strictly-positive entries.",
        concept="`arr > 0` returns a boolean array of the same shape. Using it as an index (`arr[mask]`) keeps just the True entries. The comparison and indexing run in C — no Python iteration. This pattern scales: replace `> 0` with `> 2 * arr.std()` for outlier detection.",
        example_code=(
            "import numpy as np\n"
            "# Six minutes of mid-quote returns.\n"
            "r = np.array([-0.02, 0.01, -0.005, 0.015, 0.0, 0.03])\n"
            "# Keep only minutes the price strictly went up.\n"
            "up_only = r[r > 0]\n"
            "print(up_only)\n"
            "print(f'kept {len(up_only)} of {len(r)} minutes')"
        ),
        template=(
            "import numpy as np\n"
            "r = np.array([-0.02, 0.01, -0.005, 0.015, 0.0, 0.03])\n"
            "up_only = r[r ___ 0]\n"
            "print(up_only)\n"
            "print(f'kept {len(up_only)} of {len(r)} minutes')"
        ),
        your_turn="Replace `___` with the operator that keeps strictly-positive returns only.",
        expected_stdout="[0.01  0.015 0.03 ]\nkept 3 of 6 minutes",
        hint="Strictly positive — zero doesn't count.",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=6, stage=1, mode="debug",
        title="Variance from scratch",
        scenario="Junior on the risk team ships a position-sizing script. Production runs fine for two weeks; vol-targeting numbers look believable. Until the head of risk runs the same calculation in a spreadsheet and the numbers don't match. The function below — same shape as what landed in production — divides by the wrong denominator. Spot the bug, then read the test that catches it.",
        learner_goal="Find the one-character bug in `sample_variance` that makes its output disagree with numpy's `.var(ddof=1)`.",
        concept="Sample variance divides the sum of squared deviations by `n - 1`, not `n`. The `n` form is *population* variance — correct when your data IS the whole population, wrong when it's a sample. numpy defaults to `ddof=0` (population); statisticians and pandas default to `ddof=1` (sample). For finance returns, sample is correct — you only ever have a sample of the future.",
        # Unused for debug-mode rendering — kept empty so the dataclass stays uniform.
        example_code="",
        editable_template=(
            "\"\"\"Compute sample variance from first principles.\n"
            "\n"
            "This is the function we ship to production. It's been reviewed by\n"
            "two engineers and passes a smoke test against a small array. But\n"
            "the head of risk has just emailed: 'your vol numbers are\n"
            "systematically smaller than mine.' Find why.\n"
            "\"\"\"\n"
            "import numpy as np\n"
            "\n"
            "\n"
            "def sample_variance(x: np.ndarray) -> float:\n"
            "    \"\"\"Sample variance: sum of squared deviations from the mean,\n"
            "    divided by the appropriate denominator for an unbiased estimator.\n"
            "    \"\"\"\n"
            "    mu = x.mean()\n"
            "    deviations = x - mu\n"
            "    squared = deviations ** 2\n"
            "    # Bug lives on the next line. Read the docstring above.\n"
            "    return float(squared.sum() / len(x))\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "\n"
            "\n"
            "def sample_variance(x: np.ndarray) -> float:\n"
            "    mu = x.mean()\n"
            "    deviations = x - mu\n"
            "    squared = deviations ** 2\n"
            "    return float(squared.sum() / (len(x) - 1))\n"
        ),
        tests_py=(
            "\"\"\"Sample-variance correctness against numpy's ddof=1 reference.\"\"\"\n"
            "import numpy as np\n"
            "import pytest\n"
            "\n"
            "from solution import sample_variance\n"
            "\n"
            "\n"
            "def test_matches_numpy_ddof_1_on_small_array():\n"
            "    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])\n"
            "    assert abs(sample_variance(x) - x.var(ddof=1)) < 1e-12\n"
            "\n"
            "\n"
            "def test_matches_numpy_ddof_1_on_returns_like_array():\n"
            "    rng = np.random.default_rng(0)\n"
            "    x = rng.normal(0.0, 0.02, 1000)\n"
            "    assert abs(sample_variance(x) - x.var(ddof=1)) < 1e-12\n"
            "\n"
            "\n"
            "def test_two_element_sample_variance_is_half_squared_diff():\n"
            "    # For a 2-element sample, var = (x1 - x2)^2 / 2.\n"
            "    assert abs(sample_variance(np.array([10.0, 12.0])) - 2.0) < 1e-12\n"
            "\n"
            "\n"
            "def test_constant_array_has_zero_variance():\n"
            "    x = np.full(50, 3.14)\n"
            "    # `mean()` of a constant array can leave a tiny float residual,\n"
            "    # so allow numerical-precision slack rather than == 0.\n"
            "    assert sample_variance(x) < 1e-20\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_matches_numpy_ddof_1_on_small_array",
                "sample_variance on [1..5] matches numpy's ddof=1 result.",
            ),
            (
                "tests/test_solution.py::test_matches_numpy_ddof_1_on_returns_like_array",
                "Matches numpy on a 1000-element return-like series.",
            ),
            (
                "tests/test_solution.py::test_two_element_sample_variance_is_half_squared_diff",
                "For [10, 12], sample variance is 2.0 (=(12-10)^2 / 2).",
            ),
            (
                "tests/test_solution.py::test_constant_array_has_zero_variance",
                "Constant array has zero variance — must hold even with the fix.",
            ),
        ],
        your_turn="The function looks right but ships the wrong number. Read its docstring carefully and adjust the denominator on the return line.",
        hint="The docstring says 'unbiased estimator' — for a sample, that means dividing by n-1.",
        skills=["quant", "numpy", "statistics"],
    ),
    Lesson(
        n=7, stage=1, mode="fillblank",
        title="Covariance via matrix algebra",
        scenario="Covariance between asset returns underpins everything in portfolio construction — Sharpe, Markowitz, principal components. The textbook formula `(X − μ)ᵀ(X − μ) / n` is one line in numpy and the building block of every Risk Engine you'll ever work on.",
        learner_goal="Compute a 2×2 covariance matrix from two return series using matrix multiplication.",
        concept="Stack two demeaned return series as columns of `X` (shape `(n, 2)`). Then `Xᵀ X / n` is the 2×2 covariance matrix. The diagonal is each series' variance; the off-diagonals are the covariance. The matrix product runs as one BLAS call — fastest possible.",
        example_code=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "# 1000 days of returns for two synthetic assets, independent.\n"
            "X = rng.normal(size=(1000, 2))\n"
            "# Demean each column before the dot product.\n"
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
        n=8, stage=1, mode="fillblank",
        title="Reproducible random numbers",
        scenario="Two Sigma's research review board will reject a backtest that can't be reproduced bit-for-bit. Every random draw in a research notebook gets a seed — usually a module-level constant, sometimes per-experiment. Reproducibility is non-negotiable.",
        learner_goal="Seed two generators with the same value and confirm they produce identical draws.",
        concept="`np.random.default_rng(seed)` returns a Generator object. Same seed → same draws, every time. The legacy `np.random.seed(...)` global is fine for scripts but `default_rng` is the modern, thread-safe API — use it.",
        example_code=(
            "import numpy as np\n"
            "# Two researchers, same seed, must get the same sample.\n"
            "alice = np.random.default_rng(42).normal(size=3)\n"
            "bob   = np.random.default_rng(42).normal(size=3)\n"
            "print('alice:', alice)\n"
            "print('bob:  ', bob)\n"
            "print('identical:', np.array_equal(alice, bob))"
        ),
        template=(
            "import numpy as np\n"
            "alice = np.random.default_rng(___).normal(size=3)\n"
            "bob   = np.random.default_rng(42).normal(size=3)\n"
            "print('alice:', alice)\n"
            "print('bob:  ', bob)\n"
            "print('identical:', np.array_equal(alice, bob))"
        ),
        your_turn="Replace `___` so both generators draw the same sequence.",
        expected_stdout="alice: [ 0.30471708 -1.03998411  0.7504512 ]\nbob:   [ 0.30471708 -1.03998411  0.7504512 ]\nidentical: True",
        hint="Match the integer Bob used.",
        skills=["quant", "numpy", "random-numbers"],
    ),
    Lesson(
        n=9, stage=1, mode="fillblank",
        title="Statistical reductions",
        scenario="Every research note ends with a one-liner: 'over the period, mean daily return was X bps with σ = Y bps, 95th percentile drawdown Z.' Three reductions, one line, the whole story.",
        learner_goal="Compute the mean, standard deviation, and 95th percentile of a 10k-sample return distribution.",
        concept="numpy reductions take an axis (default: whole array). `arr.mean()` and `arr.std()` are methods; `np.percentile(arr, q)` is a function — `q` is in 0–100, NOT 0–1. They all run in C under the hood; on a million points each takes microseconds.",
        example_code=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "# 10k daily returns from a slightly-positive-drift, 2%-vol distribution.\n"
            "r = rng.normal(loc=0.001, scale=0.02, size=10_000)\n"
            "\n"
            "mu    = r.mean()\n"
            "sigma = r.std()\n"
            "p95   = np.percentile(r, 95)\n"
            "\n"
            "print(f'mean  = {mu:.4f}')\n"
            "print(f'std   = {sigma:.4f}')\n"
            "print(f'p95   = {p95:.4f}')"
        ),
        template=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "r = rng.normal(loc=0.001, scale=0.02, size=10_000)\n"
            "mu    = r.___()\n"
            "sigma = r.___()\n"
            "p95   = np.___(r, 95)\n"
            "print(f'mean  = {mu:.4f}')\n"
            "print(f'std   = {sigma:.4f}')\n"
            "print(f'p95   = {p95:.4f}')"
        ),
        your_turn="Fill the three blanks with the reduction names: average, standard deviation, percentile.",
        expected_stdout="mean  = 0.0011\nstd   = 0.0200\np95   = 0.0338",
        hint="Two methods, one function. All three are short, common names.",
        skills=["quant", "numpy", "statistics"],
    ),
    Lesson(
        n=10, stage=1, mode="predict",
        title="Why numpy is fast",
        scenario="numpy isn't magic. It's a thin Python skin over carefully-optimised C and BLAS libraries written over 30 years. When you call `arr.sum()`, what runs is roughly 8 lines of C with SIMD intrinsics. When you write a Python `for` loop, what runs is 1 million dispatches through the interpreter. Hence the gap.",
        learner_goal="Run a sum of one million elements and recognise the printed value.",
        concept="numpy stores arrays as contiguous C buffers and runs ufuncs as tight C loops with no per-element Python overhead. The same loop in pure Python pays interpreter overhead per iteration — 50-100× slower. Open one of numpy's C-level source files some weekend — they're surprisingly readable.",
        example_code=(
            "import numpy as np\n"
            "x = np.arange(1_000_000)\n"
            "# Sum 0 + 1 + 2 + ... + 999999.\n"
            "# In numpy: one C loop, no per-element Python overhead.\n"
            "# In Python: 1,000,000 trips through the interpreter.\n"
            "print(int(x.sum()))"
        ),
        code=(
            "import numpy as np\n"
            "x = np.arange(1_000_000)\n"
            "print(int(x.sum()))"
        ),
        your_turn="Predict the printed sum of 0..999999. (Hint: n(n−1)/2 with n = 1,000,000.)",
        expected_stdout="499999500000",
        prompt="Type the integer.",
        skills=["quant", "numpy", "performance"],
    ),
    Lesson(
        n=11, stage=1, mode="predict",
        title="The slow Python rolling-mean",
        scenario="A junior at a prop shop writes a 30-day rolling mean as a Python double-loop. The desk's nightly batch goes from 4 minutes to 28. Senior glares. Tomorrow's lesson is `np.cumsum` — today, FEEL the slow path so you'll never write it.",
        learner_goal="Read the naive Python rolling-mean loop and predict its output on a small input.",
        concept="The naive rolling mean iterates outer × window times. For 100k points and window 30: 3 million Python operations. Same answer as numpy, but ~200× slower. The fix is the cumulative-sum trick (next lesson). First, see what it replaces.",
        example_code=(
            "x = [1, 2, 3, 4, 5, 6]\n"
            "w = 3\n"
            "rolling = []\n"
            "for i in range(w - 1, len(x)):\n"
            "    # Inner loop: w Python ops per output row.\n"
            "    s = 0\n"
            "    for j in range(i - w + 1, i + 1):\n"
            "        s += x[j]\n"
            "    rolling.append(s / w)\n"
            "print(rolling)"
        ),
        code=(
            "x = [1, 2, 3, 4, 5, 6]\n"
            "w = 3\n"
            "rolling = []\n"
            "for i in range(w - 1, len(x)):\n"
            "    s = 0\n"
            "    for j in range(i - w + 1, i + 1):\n"
            "        s += x[j]\n"
            "    rolling.append(s / w)\n"
            "print(rolling)"
        ),
        your_turn="Predict the printed list of rolling means.",
        expected_stdout="[2.0, 3.0, 4.0, 5.0]",
        prompt="Type the list as Python prints it.",
        skills=["quant", "numpy", "performance"],
    ),
    Lesson(
        n=12, stage=1, mode="skeleton",
        title="Vectorising with cumsum",
        scenario="Yesterday's double-loop ran in 28 minutes. Your manager wants the same answer in 8 seconds before tomorrow's standup. The cumulative-sum identity `c[i] − c[i−w]` is the canonical trick — every senior quant carries it in their head; pandas, vectorbt, and every market-data smoother use it internally. Today you build it from the function signature.",
        learner_goal="Implement `rolling_mean(x, w)` using numpy's `cumsum` so it matches the naive double-loop on every input.",
        concept="If `c = cumsum(x)` (with a 0 prepended so the slice arithmetic is clean), then the sum of the window of width `w` ending at index `i` equals `c[i+1] − c[i+1-w]`. One numpy pass, no inner loop. The output has shape `(len(x) - w + 1,)` — the first `w-1` positions have no full window. Same identity drives rolling sums of drawdowns, exposures, anything cumulative.",
        # Skeleton mode doesn't render the **Example.** block; field stays empty.
        example_code="",
        editable_template=(
            "\"\"\"Vectorised rolling mean via the cumulative-sum identity.\"\"\"\n"
            "import numpy as np\n"
            "\n"
            "\n"
            "def rolling_mean(x: np.ndarray, w: int) -> np.ndarray:\n"
            "    \"\"\"Mean of every contiguous window of width `w` in `x`.\n"
            "\n"
            "    Use the cumsum trick: prepend a zero to cumsum(x), then\n"
            "    each window sum is one subtraction of two prefix sums.\n"
            "    Divide by `w` to get the mean.\n"
            "\n"
            "    Parameters\n"
            "    ----------\n"
            "    x : 1-D float ndarray\n"
            "    w : window width (1 <= w <= len(x))\n"
            "\n"
            "    Returns\n"
            "    -------\n"
            "    ndarray of shape (len(x) - w + 1,) with the rolling means.\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement rolling_mean\")\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "\n"
            "\n"
            "def rolling_mean(x: np.ndarray, w: int) -> np.ndarray:\n"
            "    c = np.concatenate(([0.0], np.cumsum(x)))\n"
            "    return (c[w:] - c[:-w]) / w\n"
        ),
        tests_py=(
            "\"\"\"Tests for the vectorised rolling mean.\"\"\"\n"
            "import numpy as np\n"
            "import pytest\n"
            "\n"
            "from solution import rolling_mean\n"
            "\n"
            "\n"
            "def test_simple_input_matches_hand_calc():\n"
            "    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])\n"
            "    out = rolling_mean(x, 3)\n"
            "    assert np.allclose(out, [2.0, 3.0, 4.0, 5.0])\n"
            "\n"
            "\n"
            "def test_window_one_returns_input():\n"
            "    x = np.array([10.0, 20.0, 30.0])\n"
            "    assert np.allclose(rolling_mean(x, 1), x)\n"
            "\n"
            "\n"
            "def test_window_equals_length_returns_single_mean():\n"
            "    x = np.array([1.0, 2.0, 3.0, 4.0])\n"
            "    out = rolling_mean(x, 4)\n"
            "    assert out.shape == (1,)\n"
            "    assert abs(out[0] - 2.5) < 1e-12\n"
            "\n"
            "\n"
            "def test_shape_is_n_minus_w_plus_1():\n"
            "    rng = np.random.default_rng(0)\n"
            "    x = rng.normal(size=100)\n"
            "    out = rolling_mean(x, 7)\n"
            "    assert out.shape == (100 - 7 + 1,)\n"
            "\n"
            "\n"
            "def test_matches_naive_loop_on_random_input():\n"
            "    rng = np.random.default_rng(42)\n"
            "    x = rng.normal(size=200)\n"
            "    w = 12\n"
            "    naive = np.array([x[i : i + w].mean() for i in range(len(x) - w + 1)])\n"
            "    assert np.allclose(rolling_mean(x, w), naive)\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_simple_input_matches_hand_calc",
                "rolling_mean([1..6], 3) is [2, 3, 4, 5].",
            ),
            (
                "tests/test_solution.py::test_window_one_returns_input",
                "Window of 1 returns the input unchanged.",
            ),
            (
                "tests/test_solution.py::test_window_equals_length_returns_single_mean",
                "Window equal to len(x) returns a single mean.",
            ),
            (
                "tests/test_solution.py::test_shape_is_n_minus_w_plus_1",
                "Output shape is (len(x) - w + 1,).",
            ),
            (
                "tests/test_solution.py::test_matches_naive_loop_on_random_input",
                "Matches a Python double-loop reference on a 200-element random series.",
            ),
        ],
        your_turn="The body is empty. Read the docstring, then implement the cumsum identity in two or three lines.",
        hint="`np.concatenate(([0.0], np.cumsum(x)))` is your friend; then a single slice subtraction divided by w.",
        skills=["quant", "numpy", "vectorisation", "performance"],
    ),
    Lesson(
        n=13, stage=1, mode="matplot",
        title="Plot a price path",
        scenario="Every research note ships with a chart. The first one's always the same: simulate a price path, plot it, label axes, title. Get that muscle memory and the rest of matplotlib is just more of the same.",
        learner_goal="Simulate a geometric Brownian motion price path and plot it with labelled axes.",
        concept="GBM in one line: `price = S0 * exp(cumsum(shocks))`. `plt.plot(price)` draws the line; `plt.xlabel`, `plt.ylabel`, `plt.title` annotate it. matplotlib's pyplot API mirrors MATLAB — one statement per directive, which makes it easy to read in code review.",
        example_code=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "rng = np.random.default_rng(0)\n"
            "# 252 trading days of small daily shocks (~1% daily vol).\n"
            "shocks = rng.normal(0, 0.01, 252)\n"
            "# GBM: log-returns sum, prices are the exp.\n"
            "price = 100 * np.exp(np.cumsum(shocks))\n"
            "plt.plot(price)\n"
            "plt.title('Simulated price path')\n"
            "plt.xlabel('trading day')\n"
            "plt.ylabel('price (USD)')\n"
            "print('plotted')"
        ),
        template=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "rng = np.random.default_rng(0)\n"
            "shocks = rng.normal(0, 0.01, 252)\n"
            "price = 100 * np.exp(np.cumsum(shocks))\n"
            "plt.plot(___)\n"
            "plt.title('Simulated price path')\n"
            "plt.xlabel('trading day')\n"
            "plt.ylabel('price (USD)')\n"
            "print('plotted')"
        ),
        your_turn="Replace `___` with the variable holding the price series.",
        expected_stdout="plotted",
        hint="It's a single variable name.",
        skills=["quant", "numpy", "matplotlib", "monte-carlo"],
    ),

    # ============ Stage 2 — Pandas & Statistics (10 lessons) ============
    Lesson(
        n=14, stage=2, mode="fillblank",
        title="DataFrames from CSV",
        scenario="Citadel's day-1 onboarding stub sends the new researcher a notebook: load five tickers, line them up by date, draw a chart. Step one is always `pd.read_csv`. The bundled SPY tape here is 10 years of daily OHLCV — same shape you'd land at any prop shop, modulo field names.",
        learner_goal="Load the bundled SPY CSV into a DataFrame and report its shape.",
        concept="`pd.read_csv(path)` returns a DataFrame — pandas's tabular workhorse. `df.shape` gives `(rows, cols)`. The bundled file `/data/quant/spy.csv` carries daily bars from 2015-01-01 through 2025-12-31, seven columns: date, open, high, low, close, volume, adj_close. About 2,766 rows — almost exactly 252 × 11.",
        example_code=(
            "import pandas as pd\n"
            "# Bundled tape: SPY 2015-01-01 → 2025-12-31, daily OHLCV.\n"
            "# 7 columns: date, open, high, low, close, volume, adj_close.\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "# Almost exactly 252 trading days × 11 years.\n"
            "print(df.shape)"
        ),
        template=(
            "import pandas as pd\n"
            "df = pd.___('/data/quant/spy.csv')\n"
            "print(df.shape)"
        ),
        your_turn="Fill in the pandas function that reads a CSV.",
        expected_stdout="(2766, 7)",
        hint="Three letters, then _csv.",
        skills=["quant", "pandas"],
        datasets=["spy"],
    ),
    Lesson(
        n=15, stage=2, mode="predict",
        title="Loc versus iloc",
        scenario="The most common bug juniors at any prop shop ship in a pandas notebook: a `.loc` where they meant `.iloc`, or vice versa. The strategy returns the wrong row, the backtest looks great, the strategy live-trades and loses money. Five seconds to learn the difference, then it's automatic for the rest of your career.",
        learner_goal="Predict the values returned by .iloc and .loc on a small frame.",
        concept="`.iloc[i]` is *position* — always the i-th physical row, no matter how the frame is labelled or sorted. `.loc[label]` is *label* — looks up by the index value. For an unsorted, integer-indexed frame they coincide. After a sort or filter, they diverge — and that's when wrong-row bugs ship.",
        example_code=(
            "import pandas as pd\n"
            "# Tiny 3-row frame with custom labels a/b/c, not the default 0/1/2.\n"
            "df = pd.DataFrame({'price': [100, 101, 99]}, index=['a', 'b', 'c'])\n"
            "# .iloc[0] is the first physical row → price 100.\n"
            "# .loc['b','price'] is the row LABELLED 'b' → price 101.\n"
            "print(df.iloc[0]['price'], df.loc['b', 'price'])"
        ),
        code=(
            "import pandas as pd\n"
            "df = pd.DataFrame({'price': [100, 101, 99]}, index=['a', 'b', 'c'])\n"
            "print(df.iloc[0]['price'], df.loc['b', 'price'])"
        ),
        your_turn="Predict what the print statement outputs.",
        expected_stdout="100 101",
        prompt="Two space-separated numbers.",
        skills=["quant", "pandas"],
    ),
    Lesson(
        n=16, stage=2, mode="fillblank",
        title="Boolean filtering on real prices",
        scenario="First analytic anyone runs against a new tape at a mid-frequency shop: 'how many up-days in this window?' If your data has a hidden corruption — duplicated date, mis-aligned column — this 30-second sanity check usually catches it before you build a strategy on top.",
        learner_goal="Count the SPY days where the close was above the open.",
        concept="Comparing two pandas Series returns a boolean Series the same length. Use it as `df[mask]` and you've filtered rows where the mask is True — vectorised, no Python loop, runs in C under the hood. `.sum()` on a bool Series counts the Trues. The same one-liner pattern scans for gap-ups, breakouts, or any condition that's expressible as a comparison.",
        example_code=(
            "import pandas as pd\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "# Boolean Series, one entry per row, True when close > open.\n"
            "# Summing booleans in pandas counts the Trues — vectorised, no loop.\n"
            "up = (df['close'] > df['open']).sum()\n"
            "print(up)"
        ),
        template=(
            "import pandas as pd\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "up = (df['close'] ___ df['open']).sum()\n"
            "print(up)"
        ),
        your_turn="Replace `___` with the operator that counts strictly-up days.",
        expected_stdout="1487",
        hint="Same comparison operator you'd use on plain numbers.",
        skills=["quant", "pandas", "vectorisation"],
        datasets=["spy"],
    ),
    Lesson(
        n=17, stage=2, mode="matplot",
        title="Daily and log returns",
        scenario="Risk team at AQR uses log returns for everything that sums (multi-period returns add up cleanly). The strategy team uses simple returns because the P&L sheet expects them. The numbers match to 4 decimals on any single day — pick whichever the downstream consumer needs. Mismatch them and the year-end attribution is off by the convexity correction.",
        learner_goal="Compute simple and log returns from SPY adj_close and plot a histogram of each.",
        concept="`series.pct_change()` is the simple return `(p_t / p_{t-1}) - 1`. Log returns are `np.log(p / p.shift(1))` — equal to `log(1 + simple)`. For small moves (say |r| < 5%) they agree to three or four decimals; the log version is preferred in research notebooks because `log(p_T/p_0) = sum(log_returns)`, which makes multi-period maths a sum instead of a product.",
        example_code=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "# pct_change: (p_t / p_{t-1}) - 1  — strategy-team convention.\n"
            "simple = df['adj_close'].pct_change().dropna()\n"
            "# log(p_t / p_{t-1}) — risk/research convention because it sums.\n"
            "log_r = np.log(df['adj_close'] / df['adj_close'].shift(1)).dropna()\n"
            "plt.hist(log_r, bins=60)\n"
            "plt.title('SPY log returns'); plt.xlabel('return'); plt.ylabel('count')\n"
            "# Same stdev to 4 decimals — convexity correction is small at daily horizon.\n"
            "print(round(simple.std(), 4), round(log_r.std(), 4))"
        ),
        template=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "simple = df['adj_close'].___().dropna()\n"
            "log_r = np.log(df['adj_close'] / df['adj_close'].shift(1)).dropna()\n"
            "plt.hist(log_r, bins=60)\n"
            "plt.title('SPY log returns'); plt.xlabel('return'); plt.ylabel('count')\n"
            "print(round(simple.std(), 4), round(log_r.std(), 4))"
        ),
        your_turn="Replace `___` with the pandas method that gives the simple return.",
        expected_stdout="0.0112 0.0112",
        hint="It's the method that gives one-period percentage change.",
        skills=["quant", "pandas", "time-series", "statistics"],
        datasets=["spy"],
    ),
    Lesson(
        n=18, stage=2, mode="matplot",
        title="Rolling volatility",
        scenario="Every long-only fund has a vol-targeting overlay: scale exposure up when realised vol drops below target, cut when it spikes. 30-day rolling std of daily returns annualised by √252 is the canonical input. The chart you'll draw here is what risk dashboards at Bridgewater, AHL, and every other systematic shop plot in real time.",
        learner_goal="Compute SPY's 30-day rolling vol and plot it against time.",
        concept="`r.rolling(window).std()` builds a rolling-window std Series. Multiply by `np.sqrt(252)` to annualise daily vol (252 trading days per year, std scales with √n). The first 29 values are NaN because there's no 30-day window yet — pandas handles that automatically; downstream consumers expect it.",
        example_code=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change()\n"
            "# Rolling 30-day std, scaled by √252 → annualised vol.\n"
            "vol = r.rolling(30).std() * np.sqrt(252)\n"
            "plt.plot(vol)\n"
            "plt.title('SPY 30-day rolling vol'); plt.xlabel('day'); plt.ylabel('annualised vol')\n"
            "# Peak realised vol over the 11-year window — likely COVID-March-2020.\n"
            "print(round(vol.max(), 3))"
        ),
        template=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change()\n"
            "vol = r.rolling(30).___() * np.sqrt(252)\n"
            "plt.plot(vol)\n"
            "plt.title('SPY 30-day rolling vol'); plt.xlabel('day'); plt.ylabel('annualised vol')\n"
            "print(round(vol.max(), 3))"
        ),
        your_turn="Replace `___` with the reduction that gives standard deviation.",
        expected_stdout="0.821",
        hint="Three letters.",
        skills=["quant", "pandas", "time-series", "statistics"],
        datasets=["spy"],
    ),
    Lesson(
        n=19, stage=2, mode="fillblank",
        title="Groupby year",
        scenario="Year-end performance attribution at any fund: 'how did we do per calendar year?' Three pandas lines — `to_datetime`, `groupby('year')`, a reduction. Same pattern works for by-month (monthly attribution), by-quarter (board-deck format), or by-regime (vol-bucket attribution). Once you internalise split-apply-combine, half of pandas is the same shape.",
        learner_goal="Compute SPY's mean daily return by calendar year.",
        concept="`pd.to_datetime(col).dt.year` extracts the calendar year. `df.groupby(year)['adj_close']` splits the frame into one slice per year. `.apply(lambda s: s.pct_change().mean())` computes the mean daily return inside each slice and combines back into a Series indexed by year. Split → apply → combine.",
        example_code=(
            "import pandas as pd\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "# Add a year column so groupby has something to split on.\n"
            "df['year'] = pd.to_datetime(df['date']).dt.year\n"
            "# For each year, compute pct_change inside that year's slice, then mean.\n"
            "by_year = df.groupby('year')['adj_close'].apply(lambda s: s.pct_change().mean())\n"
            "# 2020 was the COVID year — mean daily return survived to slightly positive.\n"
            "print(round(by_year[2020], 5))"
        ),
        template=(
            "import pandas as pd\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "df['year'] = pd.to_datetime(df['date']).dt.year\n"
            "by_year = df.___('year')['adj_close'].apply(lambda s: s.pct_change().mean())\n"
            "print(round(by_year[2020], 5))"
        ),
        your_turn="Replace `___` with the pandas split-apply-combine method.",
        expected_stdout="0.00085",
        hint="Seven letters.",
        skills=["quant", "pandas", "time-series"],
        datasets=["spy"],
    ),
    Lesson(
        n=20, stage=2, mode="fillblank",
        title="Aligning two series",
        scenario="Crypto trades 24/7; equities don't. Cross-asset research at a global-macro shop spends half its time aligning calendars — BTC vs SPY, US vs Europe, holidays vs sessions. `pd.merge(..., how='inner')` is the safest default: only days both sides have a print. Outer joins are sometimes right (carry forward holidays), but inner is the easier mental model and far less likely to leak.",
        learner_goal="Merge SPY and AAPL on the date column and confirm row count.",
        concept="`pd.merge(a, b, on='date', how='inner')` keeps only rows where both frames have a date in common. The result has all columns of both — colliding names get the suffixes you pass. SPY and AAPL share the US equity calendar so the inner join keeps the full 2,766 rows; with BTC on one side, the inner result would lose every weekend.",
        example_code=(
            "import pandas as pd\n"
            "spy = pd.read_csv('/data/quant/spy.csv')\n"
            "aapl = pd.read_csv('/data/quant/aapl.csv')\n"
            "# Inner join on date — keep only days both tickers traded.\n"
            "# Suffixes disambiguate the colliding column names (open, high, …).\n"
            "joined = pd.merge(spy, aapl, on='date', how='inner', suffixes=('_spy', '_aapl'))\n"
            "# SPY + AAPL share the US equity calendar, so all 2766 rows survive.\n"
            "print(joined.shape)"
        ),
        template=(
            "import pandas as pd\n"
            "spy = pd.read_csv('/data/quant/spy.csv')\n"
            "aapl = pd.read_csv('/data/quant/aapl.csv')\n"
            "joined = pd.merge(spy, aapl, on='date', how='___', suffixes=('_spy', '_aapl'))\n"
            "print(joined.shape)"
        ),
        your_turn="Replace `___` with the join type that keeps only common dates.",
        expected_stdout="(2766, 13)",
        hint="Same name as the SQL join.",
        skills=["quant", "pandas", "time-series"],
        datasets=["spy", "aapl"],
    ),
    Lesson(
        n=21, stage=2, mode="matplot",
        title="Fitting a normal to returns",
        scenario="Risk team's first question on a new strategy: 'are these returns Gaussian enough for VaR?' Quick answer: fit a normal, overlay it, look at the tails. The body of SPY returns looks gaussian; the tails are 5× what the normal predicts — exactly the gap the 2008 risk-management literature was written about. That mismatch is why VaR alone isn't enough.",
        learner_goal="Fit a normal to SPY's daily returns and overlay it on the histogram.",
        concept="`scipy.stats.norm.fit(data)` does an MLE — returns `(mu, sigma)` of the best-fit normal. Generate the pdf at a grid of x values with `norm.pdf(xs, mu, sigma)`, plot. Use `plt.hist(..., density=True)` so the histogram is a density (area = 1), not raw counts, and the two are on the same scale.",
        example_code=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "from scipy.stats import norm\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change().dropna()\n"
            "# MLE fit of a normal — gives (mean, std) of the best-fit Gaussian.\n"
            "mu, sigma = norm.fit(r)\n"
            "xs = np.linspace(r.min(), r.max(), 200)\n"
            "# density=True scales the histogram so it sits on the pdf's y-axis.\n"
            "plt.hist(r, bins=80, density=True, alpha=0.6)\n"
            "plt.plot(xs, norm.pdf(xs, mu, sigma))\n"
            "plt.title('SPY daily returns vs normal fit')\n"
            "# Best-fit daily std — about 1.1%, in line with quoted index vol.\n"
            "print(round(sigma, 4))"
        ),
        template=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "from scipy.stats import norm\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change().dropna()\n"
            "mu, sigma = norm.___(r)\n"
            "xs = np.linspace(r.min(), r.max(), 200)\n"
            "plt.hist(r, bins=80, density=True, alpha=0.6)\n"
            "plt.plot(xs, norm.pdf(xs, mu, sigma))\n"
            "plt.title('SPY daily returns vs normal fit')\n"
            "print(round(sigma, 4))"
        ),
        your_turn="Replace `___` with scipy's MLE call.",
        expected_stdout="0.0112",
        hint="Three letters.",
        skills=["quant", "pandas", "statistics"],
        datasets=["spy"],
    ),
    Lesson(
        n=22, stage=2, mode="apifetch",
        title="OLS beta of AAPL on SPY",
        scenario="Day three on a hedge-fund risk desk. The senior asks for the beta of AAPL on SPY — but the return series don't live in a CSV; they sit behind an internal /returns/<ticker> HTTP API, with the usual realities: 200 means OK, 404 means the ticker isn't known, and an unknown ticker should bubble up as a real exception so the trade ticket gets blocked. Today's task: build the client.",
        learner_goal="Implement `compute_beta(ticker, market)` so it fetches both return series from the mock API, runs OLS, and returns the slope. Unknown tickers must raise.",
        concept="In production, return data comes through a service boundary — HTTP, gRPC, an internal feed library. The mock API in `mock_api.py` behaves like `requests`: `mock_api.get(path)` returns a `Response` with `.status_code` (int), `.ok` (bool), and `.json()` (dict). Routes: `/returns/SPY`, `/returns/AAPL`, and `/returns/QQQ` exist; anything else returns 404. Your job is to check `.ok` before reading `.json()`, raise on errors, then run an OLS regression on the two series to get the slope (beta).",
        # Unused for apifetch rendering.
        example_code="",
        mock_api_py=(
            "\"\"\"In-process mock of a `/returns/<ticker>` HTTP API.\n"
            "\n"
            "Imitates the `requests` library so your solution.py reads like\n"
            "production code. No network involved: routes return deterministic\n"
            "synthetic return series so tests reproduce bit-for-bit.\n"
            "\"\"\"\n"
            "from dataclasses import dataclass\n"
            "from typing import Any\n"
            "import numpy as np\n"
            "\n"
            "\n"
            "@dataclass\n"
            "class Response:\n"
            "    status_code: int\n"
            "    _payload: dict\n"
            "\n"
            "    @property\n"
            "    def ok(self) -> bool:\n"
            "        return 200 <= self.status_code < 300\n"
            "\n"
            "    def json(self) -> Any:\n"
            "        return self._payload\n"
            "\n"
            "\n"
            "# Deterministic per-ticker return series. SPY is the market.\n"
            "# AAPL is constructed as 1.2 * SPY + idiosyncratic noise so the\n"
            "# OLS beta lands near 1.2 — a realistic ballpark for AAPL.\n"
            "def _build_series() -> dict[str, list[float]]:\n"
            "    rng = np.random.default_rng(2025)\n"
            "    spy = rng.normal(0.0004, 0.011, 1_000)\n"
            "    aapl = 1.20 * spy + rng.normal(0.0, 0.008, 1_000)\n"
            "    qqq = 1.10 * spy + rng.normal(0.0, 0.006, 1_000)\n"
            "    return {\n"
            "        \"SPY\": spy.tolist(),\n"
            "        \"AAPL\": aapl.tolist(),\n"
            "        \"QQQ\": qqq.tolist(),\n"
            "    }\n"
            "\n"
            "\n"
            "_DATA = _build_series()\n"
            "\n"
            "\n"
            "def get(path: str) -> Response:\n"
            "    \"\"\"Mock HTTP GET. Supports /returns/<ticker> only.\n"
            "\n"
            "    200 + payload {ticker, returns: [...]}  for known tickers.\n"
            "    404 + payload {error: 'unknown ticker'} otherwise.\n"
            "    \"\"\"\n"
            "    if path.startswith(\"/returns/\"):\n"
            "        ticker = path[len(\"/returns/\"):].upper()\n"
            "        if ticker in _DATA:\n"
            "            return Response(200, {\"ticker\": ticker, \"returns\": _DATA[ticker]})\n"
            "        return Response(404, {\"error\": f\"unknown ticker: {ticker}\"})\n"
            "    return Response(404, {\"error\": f\"unknown path: {path}\"})\n"
        ),
        editable_template=(
            "\"\"\"Fetch returns via the mock API and compute beta of one ticker on another.\"\"\"\n"
            "import numpy as np\n"
            "import statsmodels.api as sm\n"
            "\n"
            "import mock_api\n"
            "\n"
            "\n"
            "def compute_beta(ticker: str, market: str = \"SPY\") -> float:\n"
            "    \"\"\"Single-stock beta from the mock returns API.\n"
            "\n"
            "    Steps:\n"
            "      1. GET /returns/<market> and /returns/<ticker> via mock_api.\n"
            "      2. If either response is not .ok, raise ValueError with the\n"
            "         API's error message (read it from response.json()['error']).\n"
            "      3. Align the two return series — drop the first index of each\n"
            "         (they're synthesised lock-step, but a real API might not be).\n"
            "      4. Run OLS: `sm.OLS(y, sm.add_constant(x)).fit()`.\n"
            "      5. Return the slope (params index 1) as a float.\n"
            "\n"
            "    Parameters\n"
            "    ----------\n"
            "    ticker : the stock whose beta to measure (e.g. 'AAPL')\n"
            "    market : the index series to regress on (default 'SPY')\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement compute_beta\")\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "import statsmodels.api as sm\n"
            "\n"
            "import mock_api\n"
            "\n"
            "\n"
            "def compute_beta(ticker: str, market: str = \"SPY\") -> float:\n"
            "    m_resp = mock_api.get(f\"/returns/{market}\")\n"
            "    if not m_resp.ok:\n"
            "        raise ValueError(m_resp.json()[\"error\"])\n"
            "    t_resp = mock_api.get(f\"/returns/{ticker}\")\n"
            "    if not t_resp.ok:\n"
            "        raise ValueError(t_resp.json()[\"error\"])\n"
            "    market_returns = np.asarray(m_resp.json()[\"returns\"])\n"
            "    ticker_returns = np.asarray(t_resp.json()[\"returns\"])\n"
            "    n = min(len(market_returns), len(ticker_returns))\n"
            "    x = market_returns[:n]\n"
            "    y = ticker_returns[:n]\n"
            "    res = sm.OLS(y, sm.add_constant(x)).fit()\n"
            "    return float(res.params[1])\n"
        ),
        tests_py=(
            "\"\"\"Beta computation + error-path tests for the mock returns API.\"\"\"\n"
            "import pytest\n"
            "\n"
            "from solution import compute_beta\n"
            "\n"
            "\n"
            "def test_aapl_beta_lands_in_expected_range():\n"
            "    beta = compute_beta(\"AAPL\")\n"
            "    # AAPL constructed as 1.20 * SPY + noise; OLS recovers ~1.2.\n"
            "    assert 1.15 < beta < 1.25\n"
            "\n"
            "\n"
            "def test_qqq_beta_lands_in_expected_range():\n"
            "    beta = compute_beta(\"QQQ\")\n"
            "    # QQQ constructed as 1.10 * SPY + smaller noise; OLS recovers ~1.1.\n"
            "    assert 1.05 < beta < 1.15\n"
            "\n"
            "\n"
            "def test_unknown_ticker_raises_with_api_error_message():\n"
            "    with pytest.raises(ValueError) as exc:\n"
            "        compute_beta(\"NVDA\")\n"
            "    assert \"NVDA\" in str(exc.value)\n"
            "\n"
            "\n"
            "def test_unknown_market_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        compute_beta(\"AAPL\", market=\"NIKKEI\")\n"
            "\n"
            "\n"
            "def test_beta_of_market_against_itself_is_one():\n"
            "    beta = compute_beta(\"SPY\")\n"
            "    assert abs(beta - 1.0) < 1e-9\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_aapl_beta_lands_in_expected_range",
                "AAPL beta on SPY lands between 1.15 and 1.25 (true value ≈ 1.20).",
            ),
            (
                "tests/test_solution.py::test_qqq_beta_lands_in_expected_range",
                "QQQ beta on SPY lands between 1.05 and 1.15.",
            ),
            (
                "tests/test_solution.py::test_unknown_ticker_raises_with_api_error_message",
                "Unknown ticker 'NVDA' raises ValueError with the API's error message.",
            ),
            (
                "tests/test_solution.py::test_unknown_market_raises",
                "Unknown market 'NIKKEI' raises ValueError.",
            ),
            (
                "tests/test_solution.py::test_beta_of_market_against_itself_is_one",
                "Beta of SPY on itself is exactly 1.0.",
            ),
        ],
        your_turn="`compute_beta` is empty. Read `mock_api.py` for the route shape, then fetch both series, check `.ok`, parse `.json()`, and regress.",
        hint="Two calls to `mock_api.get`, one if-not-ok-raise on each, then `sm.OLS(y, sm.add_constant(x)).fit().params[1]`.",
        skills=["quant", "pandas", "statistics", "regression"],
    ),
    Lesson(
        n=23, stage=2, mode="predict",
        title="Stationarity preview",
        scenario="Before any time-series team at a stat-arb fund fits an ARIMA or runs a mean-reversion strategy, they ADF-test the input. Small p-value → reject 'this looks like a random walk' → ok to fit a stationary model. Big p → the series wanders, and a mean-reverting strategy on it will blow up the first time the wander goes far. Prices wander; returns don't. Fit on returns, not prices.",
        learner_goal="Read an ADF p-value on SPY prices vs returns and predict which is stationary.",
        concept="`statsmodels.tsa.stattools.adfuller(s)` runs the Augmented Dickey-Fuller test and returns a tuple — element `[1]` is the p-value. Price series almost always have p ≈ 1 (it's effectively a random walk — non-stationary by construction). Daily returns almost always have p << 0.05 — they reject the unit-root null overwhelmingly. This is the cleanest one-pager of why returns, not prices, are the modelling target.",
        example_code=(
            "import pandas as pd\n"
            "from statsmodels.tsa.stattools import adfuller\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "# Test the price series — should fail to reject (p > 0.05): non-stationary.\n"
            "p_price = adfuller(df['adj_close'])[1]\n"
            "# Test the daily returns — should reject (p << 0.05): stationary.\n"
            "p_ret = adfuller(df['adj_close'].pct_change().dropna())[1]\n"
            "print(p_price > 0.05, p_ret < 0.05)"
        ),
        code=(
            "import pandas as pd\n"
            "from statsmodels.tsa.stattools import adfuller\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "p_price = adfuller(df['adj_close'])[1]\n"
            "p_ret = adfuller(df['adj_close'].pct_change().dropna())[1]\n"
            "print(p_price > 0.05, p_ret < 0.05)"
        ),
        your_turn="Predict the two booleans. The first asks 'is prices non-stationary?'; the second asks 'are returns stationary?'.",
        expected_stdout="True True",
        prompt="Two booleans.",
        skills=["quant", "pandas", "time-series", "statistics"],
        datasets=["spy"],
    ),

    # ============ Stage 3 — Financial Foundations / Options (10 lessons) ============
    Lesson(
        n=24, stage=3, mode="fillblank",
        title="Present value of a single cash flow",
        scenario="A pound tomorrow is worth less than a pound today. Discounting is the simplest version of every pricing model in finance — bond pricing, DCF valuation, option pricing, all of it starts with PV. Junior analysts at a rates desk derive this once on a whiteboard, then never think about it again. Today's your whiteboard.",
        learner_goal="Compute the present value of £1000 received in 5 years at a 4% discount rate.",
        concept="`PV = CF / (1 + r)**t` for a single cash flow, discrete compounding. With continuous compounding it's `PV = CF * exp(-r*t)`. Both are economically equivalent for the right `r`; conventions just differ by desk. Equity desks tend to use discrete; rates desks and option pricers use continuous.",
        example_code=(
            "# £1000 received in 5 years at a 4% discrete-compounding discount rate.\n"
            "cf, r, t = 1000, 0.04, 5\n"
            "# Discount factor 1/(1+r)**t shrinks the cashflow back to today.\n"
            "pv = cf / (1 + r)**t\n"
            "print(round(pv, 2))"
        ),
        template=(
            "cf, r, t = 1000, 0.04, 5\n"
            "pv = cf / (1 + r)___t\n"
            "print(round(pv, 2))"
        ),
        your_turn="Replace `___` with the Python exponentiation operator.",
        expected_stdout="821.93",
        hint="Two asterisks.",
        skills=["quant", "options"],
    ),
    Lesson(
        n=25, stage=3, mode="fillblank",
        title="Bond yield to maturity",
        scenario="The Treasury desk at a primary dealer quotes prices, the buy-side asks for YTMs. There's no closed-form for YTM — you solve `price = sum_of_discounted_cashflows(r)` for `r` numerically. Every desk uses `brentq` or Newton-Raphson under the hood; the bond math doesn't care which.",
        learner_goal="Find the YTM of a 5-year bond paying a 5% coupon, priced at par (face=100).",
        concept="An annual-coupon bond's fair price is `sum(c / (1+r)**t for t in 1..N) + face / (1+r)**N` — coupons plus principal, all discounted at YTM `r`. `scipy.optimize.brentq(f, lo, hi)` does a robust bisection that needs `f(lo)` and `f(hi)` to straddle zero. At par (price = face) the YTM exactly equals the coupon rate — useful sanity check.",
        example_code=(
            "from scipy.optimize import brentq\n"
            "# 5-year coupon bond, 5% annual coupon, face 100, priced at par.\n"
            "face, coupon, n, price = 100, 5, 5, 100\n"
            "# NPV(r) = PV of all cash flows minus the price — zero at the YTM.\n"
            "def npv(r):\n"
            "    return sum(coupon / (1+r)**t for t in range(1, n+1)) + face / (1+r)**n - price\n"
            "# brentq bisects between 0.01% and 50% — finds the root reliably.\n"
            "ytm = brentq(npv, 0.0001, 0.5)\n"
            "# At par, YTM == coupon rate exactly.\n"
            "print(round(ytm, 4))"
        ),
        template=(
            "from scipy.optimize import brentq\n"
            "face, coupon, n, price = 100, 5, 5, 100\n"
            "def npv(r):\n"
            "    return sum(coupon / (1+r)**t for t in range(1, n+1)) + face / (1+r)**n - price\n"
            "ytm = ___(npv, 0.0001, 0.5)\n"
            "print(round(ytm, 4))"
        ),
        your_turn="Replace `___` with the root-finder we imported.",
        expected_stdout="0.05",
        hint="Imported above. Six letters.",
        skills=["quant", "options"],
    ),
    Lesson(
        n=26, stage=3, mode="matplot",
        title="Option payoff diagrams",
        scenario="Hull's chapter 9 opens with the hockey-stick payoff diagram, and so does every derivatives interview at a market-maker. Trader's first question to a junior: 'draw the payoff at expiry of a long call'. If you can sketch this in 10 seconds you'll do fine; if you stall, you won't. Five minutes of plotting now to lock it in.",
        learner_goal="Plot the payoff of a long call with strike 100 over spot prices 60..140.",
        concept="A call's terminal payoff is `max(S - K, 0)` — zero below the strike, linearly increasing above. Subtract the premium paid to get profit. `np.maximum(S - K, 0)` is the vectorised form (`np.max` collapses to a single scalar — wrong function here). The break-even point is `S = K + premium`.",
        example_code=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "# Spot prices from 60 to 140 in 81 steps (one per unit).\n"
            "S = np.linspace(60, 140, 81)\n"
            "K, premium = 100, 5\n"
            "# Vectorised hockey-stick: max(S - K, 0) per element, minus premium.\n"
            "payoff = np.maximum(S - K, 0) - premium\n"
            "plt.plot(S, payoff)\n"
            "plt.title('Long call (K=100)'); plt.xlabel('spot'); plt.ylabel('profit')\n"
            "plt.axhline(0, color='gray', lw=0.5)\n"
            "# At S=140 the payoff is 140-100 minus 5 premium = 35.\n"
            "print(round(payoff[-1], 1))"
        ),
        template=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "S = np.linspace(60, 140, 81)\n"
            "K, premium = 100, 5\n"
            "payoff = np.___(S - K, 0) - premium\n"
            "plt.plot(S, payoff)\n"
            "plt.title('Long call (K=100)'); plt.xlabel('spot'); plt.ylabel('profit')\n"
            "plt.axhline(0, color='gray', lw=0.5)\n"
            "print(round(payoff[-1], 1))"
        ),
        your_turn="Replace `___` with the elementwise max function.",
        expected_stdout="35.0",
        hint="It's `maximum`, not `max`.",
        skills=["quant", "options", "matplotlib"],
    ),
    Lesson(
        n=27, stage=3, mode="fillblank",
        title="Put-call parity",
        scenario="Put-call parity is the model-free no-arbitrage relation that every options market-maker checks intuitively on every quote. If the relationship breaks by more than the bid-offer spread, that's free money — and the market-makers' algos snap it up in microseconds. A junior who can derive it has demonstrated they understand derivatives. One who can't, hasn't.",
        learner_goal="Verify put-call parity numerically using the Black-Scholes prices.",
        concept="Parity: `C - P = S - K * exp(-r*T)`. It comes from a no-arbitrage portfolio argument that needs no distributional assumption — it holds for any model, any vol surface, any underlying. Rearranged: given a call price, the matching put is `P = C - S + K * exp(-r*T)`. Memorise the sign convention: the `-r*T` term goes inside the exp.",
        example_code=(
            "import numpy as np\n"
            "# Spot=100, Strike=100, rate=4%, T=1y, call=9.6 (textbook example).\n"
            "S, K, r, T, C = 100, 100, 0.04, 1.0, 9.6\n"
            "# Parity-implied put price — should match a direct BS put calc.\n"
            "P_from_parity = C - S + K * np.exp(-r * T)\n"
            "print(round(P_from_parity, 2))"
        ),
        template=(
            "import numpy as np\n"
            "S, K, r, T, C = 100, 100, 0.04, 1.0, 9.6\n"
            "P_from_parity = C - S + K * np.exp(___ * T)\n"
            "print(round(P_from_parity, 2))"
        ),
        your_turn="Replace `___` so the discount factor is correct (negative rate times time).",
        expected_stdout="5.68",
        hint="The exponent should be negative.",
        skills=["quant", "options"],
    ),
    Lesson(
        n=28, stage=3, mode="fillblank",
        title="Black-Scholes from scratch",
        scenario="In any options interview at a market-maker — Citadel Securities, IMC, Optiver — you will be asked to derive or implement Black-Scholes from first principles. It's the equivalent of FizzBuzz for derivatives engineers. Today you implement it once, by hand, no library, and verify against Hull's textbook example. Twenty years from now it'll still be one of the five formulas you remember cold.",
        learner_goal="Implement the Black-Scholes call price and verify against a textbook example.",
        concept="Call price = `S·N(d1) − K·exp(−rT)·N(d2)` where `d1 = (ln(S/K) + (r + σ²/2)·T) / (σ·√T)` and `d2 = d1 − σ·√T`. `N(·)` is the standard normal CDF — `scipy.stats.norm.cdf`. Intuition: `N(d1)` is the risk-neutral delta (probability-weighted exposure); `N(d2)` is the risk-neutral probability of finishing in the money. Hull's example (S=K=100, r=5%, σ=20%, T=1y) gives C ≈ 10.45.",
        example_code=(
            "import numpy as np\n"
            "from scipy.stats import norm\n"
            "# Hull's canonical example, used to verify any new BS implementation.\n"
            "S, K, r, sigma, T = 100, 100, 0.05, 0.20, 1.0\n"
            "# d1 and d2 are the standardised log-moneyness terms.\n"
            "d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))\n"
            "d2 = d1 - sigma*np.sqrt(T)\n"
            "# Call = spot * N(d1) - PV(strike) * N(d2). N(·) is the standard normal CDF.\n"
            "C = S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)\n"
            "# Hull p.299: C ≈ 10.45. Verify to 4 dp.\n"
            "print(round(C, 4))"
        ),
        template=(
            "import numpy as np\n"
            "from scipy.stats import norm\n"
            "S, K, r, sigma, T = 100, 100, 0.05, 0.20, 1.0\n"
            "d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))\n"
            "d2 = d1 - sigma*np.sqrt(T)\n"
            "C = S*norm.___(d1) - K*np.exp(-r*T)*norm.___(d2)\n"
            "print(round(C, 4))"
        ),
        your_turn="Fill the two blanks with the normal CDF function.",
        expected_stdout="10.4506",
        hint="Three letters — cumulative distribution function.",
        skills=["quant", "options", "black-scholes"],
    ),
    Lesson(
        n=29, stage=3, mode="fillblank",
        title="Greeks: delta of a call",
        scenario="The vol-trading desk at any market-maker runs a 'delta-neutral' book — for every short option they're long the corresponding delta in the underlying. The system recomputes the desk's net delta many times a second from positions × Black-Scholes Greeks. A trader who can't quote N(d1) on a whiteboard hasn't earned the seat. Today: compute it.",
        learner_goal="Compute the delta of an at-the-money call.",
        concept="Delta is `∂C/∂S` — the change in option value per unit change in spot. Take the partial derivative of the BS formula and the terms collapse: `Δ_call = N(d1)`, exactly. At-the-money (S = K), d1 ≈ 0.35 for typical parameters, so delta ≈ 0.64. Out-of-the-money calls have low delta (small N(d1)); deep-in-the-money calls have delta near 1 (large N(d1)).",
        example_code=(
            "import numpy as np\n"
            "from scipy.stats import norm\n"
            "# Same parameters as Hull's BS example.\n"
            "S, K, r, sigma, T = 100, 100, 0.05, 0.20, 1.0\n"
            "d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))\n"
            "# Δ_call = N(d1) — falls straight out of the BS derivation.\n"
            "delta = norm.cdf(d1)\n"
            "# ATM call delta ≈ 0.64 — not 0.5, because of the (r + σ²/2)·T drift.\n"
            "print(round(delta, 4))"
        ),
        template=(
            "import numpy as np\n"
            "from scipy.stats import norm\n"
            "S, K, r, sigma, T = 100, 100, 0.05, 0.20, 1.0\n"
            "d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))\n"
            "delta = ___.cdf(d1)\n"
            "print(round(delta, 4))"
        ),
        your_turn="Replace `___` with the scipy.stats object we imported.",
        expected_stdout="0.6368",
        hint="Four letters.",
        skills=["quant", "options", "greeks"],
    ),
    Lesson(
        n=30, stage=3, mode="fillblank",
        title="Binomial tree pricer",
        scenario="Before Black-Scholes' PDE became standard in vol-desk software, the CRR (Cox-Ross-Rubinstein) tree was *the* pricing algorithm. It still is for American options — early exercise needs a backward induction that the closed-form BS can't do. Every Hull chapter on exotic options starts here; every options engineer can sketch the recurrence on a whiteboard.",
        learner_goal="Price a European call with a 50-step binomial tree.",
        concept="Set `u = exp(σ·√dt)`, `d = 1/u` (Cox-Ross-Rubinstein parameterisation, multiplicatively symmetric). Risk-neutral up-probability `p = (exp(r·dt) − d) / (u − d)`. Build terminal payoffs at expiry, then walk back to t=0: at each node, value = `exp(−r·dt) · (p·V_up + (1−p)·V_down)`. As N → ∞ the price converges to Black-Scholes.",
        example_code=(
            "import numpy as np\n"
            "# 50-step CRR tree on Hull's BS example.\n"
            "S, K, r, sigma, T, N = 100, 100, 0.05, 0.20, 1.0, 50\n"
            "# Up/down factors and risk-neutral probability.\n"
            "dt = T/N; u = np.exp(sigma*np.sqrt(dt)); d = 1/u\n"
            "p = (np.exp(r*dt) - d)/(u - d)\n"
            "# Terminal prices at expiry: S * u^i * d^(N-i) for i = 0..N.\n"
            "ST = S * u**np.arange(N+1) * d**(N - np.arange(N+1))\n"
            "vals = np.maximum(ST - K, 0)\n"
            "# Backward induction — discount + risk-neutral average at each step.\n"
            "for _ in range(N):\n"
            "    vals = np.exp(-r*dt) * (p*vals[1:] + (1-p)*vals[:-1])\n"
            "# vals[0] is t=0. Compare to BS 10.4506 — convergence is monotonic in N.\n"
            "print(round(vals[0], 4))"
        ),
        template=(
            "import numpy as np\n"
            "S, K, r, sigma, T, N = 100, 100, 0.05, 0.20, 1.0, 50\n"
            "dt = T/N; u = np.exp(sigma*np.sqrt(dt)); d = 1/u\n"
            "p = (np.exp(r*dt) - d)/(u - d)\n"
            "ST = S * u**np.arange(N+1) * d**(N - np.arange(N+1))\n"
            "vals = np.maximum(ST - K, 0)\n"
            "for _ in range(N):\n"
            "    vals = np.exp(-r*dt) * (p*vals[1:] + (1-p)*vals[___])\n"
            "print(round(vals[0], 4))"
        ),
        your_turn="Replace `___` with the slice that gives 'all but the last' (the down-branch values).",
        expected_stdout="10.4107",
        hint="Two-character slice.",
        skills=["quant", "options", "black-scholes"],
    ),
    Lesson(
        n=31, stage=3, mode="matplot",
        title="Monte Carlo option pricing",
        scenario="Path-dependent and high-dimensional payoffs (basket options, Asian options, callable structured notes) defeat both Black-Scholes and trees — but Monte Carlo handles them with one tweak per payoff function. Every quant library (QuantLib, py_vollib) ships MC pricers; the exotics desk at every major bank lives on them. The downside: convergence at `1/√N`, which is *slow*. Plot it once and you'll never forget.",
        learner_goal="Price a European call by Monte Carlo and plot the running estimate's convergence.",
        concept="Under risk-neutral GBM, `S_T = S₀·exp((r − σ²/2)·T + σ·√T·Z)` with `Z ~ N(0,1)`. The call price is the discounted expected payoff: `exp(−r·T) · E[max(S_T − K, 0)]`. Replace `E[·]` with the sample mean of N draws. The running mean's standard error shrinks as `σ/√N` — quadrupling N halves the error, but never faster.",
        example_code=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "S0, K, r, sigma, T, N = 100, 100, 0.05, 0.20, 1.0, 50_000\n"
            "rng = np.random.default_rng(0)\n"
            "Z = rng.standard_normal(N)\n"
            "ST = S0 * np.exp((r - sigma**2/2)*T + sigma*np.sqrt(T)*Z)\n"
            "payoffs = np.exp(-r*T) * np.maximum(ST - K, 0)\n"
            "running = np.cumsum(payoffs) / np.arange(1, N+1)\n"
            "plt.plot(running)\n"
            "plt.axhline(10.4506, color='red', lw=0.5, label='Black-Scholes')\n"
            "plt.legend(); plt.title('MC call price convergence')\n"
            "print(round(running[-1], 3))"
        ),
        template=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "S0, K, r, sigma, T, N = 100, 100, 0.05, 0.20, 1.0, 50_000\n"
            "rng = np.random.default_rng(0)\n"
            "Z = rng.standard_normal(N)\n"
            "ST = S0 * np.exp((r - sigma**2/2)*T + sigma*np.sqrt(T)*Z)\n"
            "payoffs = np.exp(-r*T) * np.maximum(ST - K, 0)\n"
            "running = np.___(payoffs) / np.arange(1, N+1)\n"
            "plt.plot(running)\n"
            "plt.axhline(10.4506, color='red', lw=0.5, label='Black-Scholes')\n"
            "plt.legend(); plt.title('MC call price convergence')\n"
            "print(round(running[-1], 3))"
        ),
        your_turn="Replace `___` so the running mean accumulates correctly.",
        expected_stdout="10.48",
        hint="Cumulative sum.",
        skills=["quant", "options", "monte-carlo"],
    ),
    Lesson(
        n=32, stage=3, mode="matplot",
        title="Mean-variance frontier",
        scenario="Markowitz's efficient frontier is the most-cited chart in finance, full stop. Every multi-asset allocator at every pension fund, family office, and asset manager produces some version of it before sizing a portfolio. The closed-form version below sidesteps the numerical optimiser entirely — three matrix-algebra constants, one sweep, done. Then you can argue with an econometrician about whether the inputs are stationary (spoiler: they're not).",
        learner_goal="Sweep target returns and plot the resulting min-variance volatilities.",
        concept="Given covariance Σ and means μ, the closed-form min-variance portfolio at target return `t` uses three constants: `a = 1ᵀΣ⁻¹1`, `b = μᵀΣ⁻¹1`, `c = μᵀΣ⁻¹μ`. Variance at target `t` is `(a·t² − 2bt + c) / (a·c − b²)`. No optimiser, no constraints — just linear algebra. Adding a no-short constraint would force you back to a numerical solver.",
        example_code=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "def ret(t): return pd.read_csv(f'/data/quant/{t}.csv')['adj_close'].pct_change().dropna().values[-1000:]\n"
            "R = np.column_stack([ret('spy'), ret('aapl'), ret('tlt')])\n"
            "mu, S = R.mean(axis=0), np.cov(R, rowvar=False)\n"
            "Sinv = np.linalg.inv(S); ones = np.ones(3)\n"
            "a = ones @ Sinv @ ones; b = mu @ Sinv @ ones; c = mu @ Sinv @ mu\n"
            "targets = np.linspace(mu.min(), mu.max(), 50)\n"
            "vars_ = (a*targets**2 - 2*b*targets + c) / (a*c - b**2)\n"
            "plt.plot(np.sqrt(vars_), targets); plt.xlabel('vol'); plt.ylabel('return')\n"
            "print(round(float(np.sqrt(vars_).min()), 4))"
        ),
        template=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "def ret(t): return pd.read_csv(f'/data/quant/{t}.csv')['adj_close'].pct_change().dropna().values[-1000:]\n"
            "R = np.column_stack([ret('spy'), ret('aapl'), ret('tlt')])\n"
            "mu, S = R.mean(axis=0), np.cov(R, ___=False)\n"
            "Sinv = np.linalg.inv(S); ones = np.ones(3)\n"
            "a = ones @ Sinv @ ones; b = mu @ Sinv @ ones; c = mu @ Sinv @ mu\n"
            "targets = np.linspace(mu.min(), mu.max(), 50)\n"
            "vars_ = (a*targets**2 - 2*b*targets + c) / (a*c - b**2)\n"
            "plt.plot(np.sqrt(vars_), targets); plt.xlabel('vol'); plt.ylabel('return')\n"
            "print(round(float(np.sqrt(vars_).min()), 4))"
        ),
        your_turn="Replace `___` with the np.cov keyword that treats each column as one variable.",
        expected_stdout="0.0079",
        hint="It's the opposite of 'rows are variables'.",
        skills=["quant", "portfolio", "linear-algebra"],
        datasets=["spy", "aapl", "tlt"],
    ),
    Lesson(
        n=33, stage=3, mode="fillblank",
        title="Sharpe, max drawdown",
        scenario="The two numbers every allocator asks about a strategy before reading the deck: 'what's the Sharpe and what's the max drawdown?' Sharpe summarises risk-adjusted return; max drawdown summarises the worst the investor would have felt holding it. Compute them in one cell — every backtest framework (vectorbt, zipline, bt) gives them to you, but every quant has at some point implemented them by hand on a whiteboard during an interview.",
        learner_goal="Compute SPY's annualised Sharpe ratio and max drawdown.",
        concept="Annualised Sharpe for daily returns: `(mean × 252) / (std × √252)` — the 252 in the numerator turns daily mean to annual, the √252 in the denominator turns daily std to annual. Max drawdown: build the cumulative equity curve, take running max, divide — the minimum of that ratio minus 1 is the worst peak-to-trough loss as a fraction.",
        example_code=(
            "import pandas as pd, numpy as np\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change().dropna()\n"
            "# Annualised Sharpe: scale mean by 252, std by √252.\n"
            "sharpe = (r.mean()*252) / (r.std()*np.sqrt(252))\n"
            "# Equity curve = compounded returns. cummax tracks the running peak.\n"
            "eq = (1 + r).cumprod()\n"
            "dd = (eq / eq.cummax() - 1).min()\n"
            "# SPY 2015-2025: Sharpe ≈ 0.8, max DD ≈ -34% (COVID March 2020).\n"
            "print(round(sharpe, 2), round(dd, 3))"
        ),
        template=(
            "import pandas as pd, numpy as np\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change().dropna()\n"
            "sharpe = (r.mean()*252) / (r.std()*np.sqrt(252))\n"
            "eq = (1 + r).cumprod()\n"
            "dd = (eq / eq.___() - 1).min()\n"
            "print(round(sharpe, 2), round(dd, 3))"
        ),
        your_turn="Replace `___` with the running-max method.",
        expected_stdout="0.8 -0.337",
        hint="`cum...` something — running maximum.",
        skills=["quant", "pandas", "risk-metrics"],
        datasets=["spy"],
    ),

    # ============ Stage 4 — Machine Learning for Finance (6 lessons) ============
    Lesson(
        n=34, stage=4, mode="fillblank",
        title="sklearn fit and predict",
        scenario="Whether you're at Renaissance fitting a 200-feature tree ensemble or at a quant fund prototyping a single-feature ridge, the sklearn API is the same: `.fit(X, y)` learns, `.predict(X_new)` infers, `.score(X, y)` evaluates. The reason every research group settles on sklearn isn't that it's the fastest — it's that the uniform API makes every model swappable for any other in three lines.",
        learner_goal="Train a linear regression on a toy dataset and verify the perfect fit.",
        concept="Every sklearn estimator implements `fit/predict/score` (regressors return R², classifiers return accuracy). With perfectly linear synthetic data (`y = 2x + 3`), `LinearRegression` recovers the coefficient exactly and `.score` returns 1.0. Anything below 1.0 on a clean linear dataset means a bug in your feature matrix.",
        example_code=(
            "import numpy as np\n"
            "from sklearn.linear_model import LinearRegression\n"
            "# X must be 2D for sklearn — even a single feature gets reshape(-1, 1).\n"
            "X = np.arange(10).reshape(-1, 1)\n"
            "# Perfectly linear target: y = 2x + 3.\n"
            "y = 2 * X.ravel() + 3\n"
            "# Chainable .fit returns the model so you can score in one line.\n"
            "model = LinearRegression().fit(X, y)\n"
            "# R² == 1.0 confirms a perfect fit.\n"
            "print(round(model.score(X, y), 4))"
        ),
        template=(
            "import numpy as np\n"
            "from sklearn.linear_model import LinearRegression\n"
            "X = np.arange(10).reshape(-1, 1)\n"
            "y = 2 * X.ravel() + 3\n"
            "model = LinearRegression().___(X, y)\n"
            "print(round(model.score(X, y), 4))"
        ),
        your_turn="Replace `___` with the method that trains the model.",
        expected_stdout="1.0",
        hint="Three letters.",
        skills=["quant", "machine-learning", "regression"],
    ),
    Lesson(
        n=35, stage=4, mode="predict",
        title="Lookahead bias",
        scenario="The single biggest source of fake-Sharpe in junior quants' backtests: shuffled cross-validation on time series. A random `train_test_split` lets the model train on day t+1 and test on day t — peeking into the future. Sharpe goes up, paper looks brilliant, strategy lives, loses money in production. Lopez de Prado wrote an entire book about this (*Advances in Financial Machine Learning*). The fix is one keyword: `shuffle=False`.",
        learner_goal="Recognise why a chronological split is the honest baseline.",
        concept="`train_test_split(..., shuffle=False)` keeps the original row order: first 80% becomes training, last 20% becomes test. For time series this is non-negotiable. The 'right' way is `TimeSeriesSplit` (next lesson) — but if you only do one thing right, do `shuffle=False`.",
        example_code=(
            "from sklearn.model_selection import train_test_split\n"
            "import numpy as np\n"
            "# Ordered range 0..9 — pretend each integer is a date.\n"
            "X = np.arange(10).reshape(-1, 1); y = np.arange(10)\n"
            "# shuffle=False keeps the original order — last 20% is the test set.\n"
            "_, X_test, _, _ = train_test_split(X, y, test_size=0.2, shuffle=False)\n"
            "print(X_test.ravel().tolist())"
        ),
        code=(
            "from sklearn.model_selection import train_test_split\n"
            "import numpy as np\n"
            "X = np.arange(10).reshape(-1, 1); y = np.arange(10)\n"
            "_, X_test, _, _ = train_test_split(X, y, test_size=0.2, shuffle=False)\n"
            "print(X_test.ravel().tolist())"
        ),
        your_turn="Predict what the test set looks like — last 20% of an ordered range 0..9.",
        expected_stdout="[8, 9]",
        prompt="Type the list as Python prints it.",
        skills=["quant", "machine-learning", "backtesting"],
    ),
    Lesson(
        n=36, stage=4, mode="fillblank",
        title="Momentum signal regression",
        scenario="Time-series momentum (TSMOM) is the most-documented anomaly in finance — Asness, Moskowitz, Pedersen wrote the canonical paper at AQR. The naive form: 5-day past return predicts next-day return. Reality: at the daily horizon on a single liquid index, R² is essentially zero. Trend-following on TSMOM works at *much* longer horizons and across diverse markets, not on one daily SPY series — but you have to feel the small-sample noise before you can size a real strategy honestly.",
        learner_goal="Fit a linear regression of next-day SPY return on lagged 5-day return; report the R².",
        concept="Build a momentum feature: `mom = r.shift(1).rolling(5).sum()` — sum of the prior 5 days' returns, lagged by 1 so it uses only past info. Target: next day's return. Drop NaNs, split chronologically, fit. R² near zero on this single-feature, single-asset version is the honest answer; *don't* believe a positive R² on the same data with shuffled splitting.",
        example_code=(
            "import pandas as pd, numpy as np\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import train_test_split\n"
            "r = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "df = pd.DataFrame({'mom': r.shift(1).rolling(5).sum(), 'next': r}).dropna()\n"
            "X = df[['mom']].values; y = df['next'].values\n"
            "Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, shuffle=False)\n"
            "score = LinearRegression().fit(Xtr, ytr).score(Xte, yte)\n"
            "print(round(score, 4))"
        ),
        template=(
            "import pandas as pd, numpy as np\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import train_test_split\n"
            "r = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "df = pd.DataFrame({'mom': r.shift(1).rolling(5).sum(), 'next': r}).dropna()\n"
            "X = df[['mom']].values; y = df['next'].values\n"
            "Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, ___=False)\n"
            "score = LinearRegression().fit(Xtr, ytr).score(Xte, yte)\n"
            "print(round(score, 4))"
        ),
        your_turn="Replace `___` so the split keeps chronological order (no shuffling).",
        expected_stdout="0.0049",
        hint="Seven letters.",
        skills=["quant", "machine-learning", "regression"],
        datasets=["spy"],
    ),
    Lesson(
        n=37, stage=4, mode="fillblank",
        title="Random forest direction classifier",
        scenario="WorldQuant, Two Sigma, Renaissance — the ML-heavy shops moved from linear models to gradient boosting and forests in the 2010s for one reason: real markets have interaction effects that linear models can't capture (vol × momentum, momentum × yield-curve). A random forest is the simplest non-linear ML model that's still interpretable enough to put in production. Accuracy ~53% on a two-feature daily classifier is unremarkable — that's the point. The 'magic' is in feature engineering, not model complexity.",
        learner_goal="Train a 100-tree random forest to predict next-day direction from 5-day momentum and rolling volatility.",
        concept="`RandomForestClassifier(n_estimators=100)` builds 100 decision trees on bootstrap samples of the training data; the ensemble vote becomes the prediction. Features here: 5-day momentum and 20-day rolling std (a vol proxy). Label: `sign(next_return)`. Use `random_state=0` so results are reproducible across re-runs.",
        example_code=(
            "import pandas as pd, numpy as np\n"
            "from sklearn.ensemble import RandomForestClassifier\n"
            "from sklearn.model_selection import train_test_split\n"
            "r = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "df = pd.DataFrame({\n"
            "    'mom': r.shift(1).rolling(5).sum(),\n"
            "    'vol': r.shift(1).rolling(20).std(),\n"
            "    'next': np.sign(r),\n"
            "}).dropna()\n"
            "X = df[['mom','vol']].values; y = df['next'].values\n"
            "Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, shuffle=False)\n"
            "score = RandomForestClassifier(n_estimators=100, random_state=0).fit(Xtr, ytr).score(Xte, yte)\n"
            "print(round(score, 3))"
        ),
        template=(
            "import pandas as pd, numpy as np\n"
            "from sklearn.ensemble import RandomForestClassifier\n"
            "from sklearn.model_selection import train_test_split\n"
            "r = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "df = pd.DataFrame({\n"
            "    'mom': r.shift(1).rolling(5).sum(),\n"
            "    'vol': r.shift(1).rolling(20).std(),\n"
            "    'next': np.sign(r),\n"
            "}).dropna()\n"
            "X = df[['mom','vol']].values; y = df['next'].values\n"
            "Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, shuffle=False)\n"
            "score = RandomForestClassifier(n_estimators=100, random_state=0).___(Xtr, ytr).score(Xte, yte)\n"
            "print(round(score, 3))"
        ),
        your_turn="Replace `___` with the method that trains the forest.",
        expected_stdout="0.526",
        hint="Same method as every sklearn estimator.",
        skills=["quant", "machine-learning"],
        datasets=["spy"],
    ),
    Lesson(
        n=38, stage=4, mode="fillblank",
        title="Time-series cross-validation",
        scenario="Honest cross-validation on financial time series uses expanding-window splits: train on `[0..t1]`, test on `(t1..t2]`, then train on `[0..t2]`, test on `(t2..t3]`, and so on. Every test fold sits strictly after its train fold — no leakage, no peeking. Lopez de Prado's `purgedKFold` adds embargo gaps for serial-correlated labels; `TimeSeriesSplit` is the entry-level version that catches the worst sins.",
        learner_goal="Run a 5-fold time-series CV on a linear model and average the fold scores.",
        concept="`TimeSeriesSplit(n_splits=5)` yields five (train_idx, test_idx) tuples where every test starts after the previous train ends. `cross_val_score(model, X, y, cv=tscv)` runs them and returns a 5-element array of fold R²s — average to get the headline number. For honest backtests, this is the *minimum* bar.",
        example_code=(
            "import pandas as pd, numpy as np\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import TimeSeriesSplit, cross_val_score\n"
            "r = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "df = pd.DataFrame({'mom': r.shift(1).rolling(5).sum(), 'next': r}).dropna()\n"
            "X = df[['mom']].values; y = df['next'].values\n"
            "tscv = TimeSeriesSplit(n_splits=5)\n"
            "scores = cross_val_score(LinearRegression(), X, y, cv=tscv)\n"
            "print(round(scores.mean(), 4))"
        ),
        template=(
            "import pandas as pd, numpy as np\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import TimeSeriesSplit, cross_val_score\n"
            "r = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "df = pd.DataFrame({'mom': r.shift(1).rolling(5).sum(), 'next': r}).dropna()\n"
            "X = df[['mom']].values; y = df['next'].values\n"
            "tscv = ___(n_splits=5)\n"
            "scores = cross_val_score(LinearRegression(), X, y, cv=tscv)\n"
            "print(round(scores.mean(), 4))"
        ),
        your_turn="Replace `___` with the splitter that respects chronological order.",
        expected_stdout="0.0",
        hint="Imported above — three words run together.",
        skills=["quant", "machine-learning", "backtesting"],
        datasets=["spy"],
    ),
    Lesson(
        n=39, stage=4, mode="predict",
        title="The p-hacked Sharpe trap",
        scenario="Bailey, Lopez de Prado et al published 'The Probability of Backtest Overfitting' (PBO) — a paper every quant risk team treats as required reading. The headline result: if you try 1,000 strategies, the best one's reported Sharpe is meaningless unless you correct for the multiple-testing. This lesson recreates the basic intuition: 1000 pure-noise strategies, the *best* one has annualised Sharpe > 1.5, by chance alone. That's why fund managers grill quants on 'how many alternatives did you try?'.",
        learner_goal="Predict the maximum Sharpe of 1000 pure-noise strategies — and feel why a 'great' backtest in isolation is meaningless.",
        concept="Generate 1000 independent return series, each with mean 0 and σ=0.01. Compute each one's annualised Sharpe (mean/std × √252). The max across the 1000 is several standard deviations above zero — that's the extremum of 1000 draws from a roughly-zero-mean distribution. None of the strategies has any edge; the *best* still looks brilliant. The fix: report Lopez de Prado's *Deflated Sharpe Ratio*, which accounts for the number of trials.",
        example_code=(
            "import numpy as np\n"
            "rng = np.random.default_rng(42)\n"
            "R = rng.normal(0, 0.01, size=(1000, 1000))\n"
            "sharpe = R.mean(axis=1) / R.std(axis=1) * np.sqrt(252)\n"
            "print(round(sharpe.max(), 2) > 1.5)"
        ),
        code=(
            "import numpy as np\n"
            "rng = np.random.default_rng(42)\n"
            "R = rng.normal(0, 0.01, size=(1000, 1000))\n"
            "sharpe = R.mean(axis=1) / R.std(axis=1) * np.sqrt(252)\n"
            "print(round(sharpe.max(), 2) > 1.5)"
        ),
        your_turn="1000 pure-noise strategies — is the best one's annualised Sharpe > 1.5?",
        expected_stdout="True",
        prompt="True or False?",
        skills=["quant", "machine-learning", "backtesting", "risk-metrics"],
    ),

    # ============ Stage 5 — Performance & C (12 lessons) ============
    Lesson(
        n=40, stage=5, mode="cwasm",
        title="Why C",
        scenario="The Citadel Securities matching engine, Jane Street's trading core, every market-maker's pricing loop — all C or C++. Python is where research happens; C is where the inner loop runs a billion times a day. The latency budget for a US equity option quote is ~10µs end-to-end; a single Python attribute lookup costs ~0.1µs. The maths doesn't work in Python. That's why the next 12 lessons exist.",
        learner_goal="Read a real C limit-order-book node and see it execute.",
        concept="The demo below is a sorted-list limit-order-book in C, compiled to WASM at `-O3`. The C version's edge over a pure-Python equivalent isn't from cleverer algorithm — it's the absence of per-element interpreter overhead, the contiguous-memory layout of structs, and the direct pointer chasing the compiler turns into one or two instructions per dereference. Same algorithm, ~100× faster.",
        example_code=(
            "/* Sorted-insert LOB in C — see c-demos/lob_node.c */\n"
            "insert_bid(&book, 1, 100.05, 5);\n"
            "insert_bid(&book, 2, 100.10, 3);"
        ),
        source=(
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "\n"
            "typedef struct Order {\n"
            "    int order_id;\n"
            "    double price;\n"
            "    int qty;\n"
            "    struct Order *next;\n"
            "} Order;\n"
            "\n"
            "/* Insert sorted descending by price (best bid at head). */\n"
            "static Order *insert_bid(Order *head, int id, double price, int qty) {\n"
            "    Order *n = malloc(sizeof *n);\n"
            "    n->order_id = id; n->price = price; n->qty = qty; n->next = NULL;\n"
            "    if (head == NULL || price > head->price) {\n"
            "        n->next = head;\n"
            "        return n;\n"
            "    }\n"
            "    Order *cur = head;\n"
            "    while (cur->next != NULL && cur->next->price >= price) cur = cur->next;\n"
            "    n->next = cur->next;\n"
            "    cur->next = n;\n"
            "    return head;\n"
            "}\n"
            "\n"
            "int main(void) {\n"
            "    Order *bids = NULL;\n"
            "    bids = insert_bid(bids, 1, 100.05, 5);\n"
            "    bids = insert_bid(bids, 2, 100.10, 3);\n"
            "    bids = insert_bid(bids, 3, 99.95, 8);\n"
            "    bids = insert_bid(bids, 4, 100.10, 2);\n"
            "    bids = insert_bid(bids, 5, 100.07, 1);\n"
            "    printf(\"bids: \"); for (Order *c = bids; c; c = c->next)\n"
            "        printf(\"[#%d %.2f x %d] \", c->order_id, c->price, c->qty);\n"
            "    printf(\"\\nbest bid: %.2f (qty %d)\\n\", bids->price, bids->qty);\n"
            "    return 0;\n"
            "}\n"
        ),
        wasm_demo="lob_node",
        expected_stdout_contains="best bid: 100.10",
        your_turn="Click Run demo. The C compiles ahead of time — what you see is `-O3` speed.",
        hint="The best bid should win on price, then time priority.",
        skills=["quant", "c-language", "low-latency"],
    ),
    Lesson(
        n=41, stage=5, mode="cscript",
        title="Hello C",
        scenario="K&R's *The C Programming Language* opens with this exact program in chapter 1. So does every undergraduate systems course at every CS programme. The shape — `#include`, `int main`, `printf`, `return 0` — is older than the World Wide Web and unchanged in every C compiler shipped since. Type it once, and you've started learning the language that quietly runs every kernel, every database, and every exchange in the world.",
        learner_goal="Print 'hello, C!' from a C program.",
        concept="`#include <stdio.h>` brings in standard I/O — that's where `printf` lives. `int main()` is C's entry point; it must return an `int` (0 means success to the OS). Strings live between double quotes; `\\n` is a newline. Semicolons end statements — not optional, unlike Python.",
        example_code=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    printf(\"hello, C!\\n\");\n"
            "    return 0;\n"
            "}"
        ),
        template=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    printf(\"___\\n\");\n"
            "    return 0;\n"
            "}"
        ),
        your_turn="Replace `___` with the exact string `hello, C!`.",
        expected_stdout="hello, C!",
        hint="No quotes — those come from the surrounding code.",
        skills=["quant", "c-language"],
    ),
    Lesson(
        n=42, stage=5, mode="cscript",
        title="Types and arithmetic",
        scenario="The first surprise every Python-to-C convert hits: `7 / 2 == 3`, not `3.5`. C's division operator follows the types of its operands — if both are ints, the result is integer division. Python 3 silently fixed this; C didn't, and never will. The bug shows up at 4am in production when a quant runs `pnl / shares` with integer shares — silent truncation, wrong number, wrong trade. Two minutes here to lock it in.",
        learner_goal="Print the integer division of 7/2 and the floating-point division of 7.0/2.0.",
        concept="In C, `/` operates by the types of its operands. Two ints → integer division, truncating toward zero (`7 / 2` = `3`). One or both operands floating-point → true division (`7.0 / 2` = `3.5`). To force float division on int variables: cast one with `(double)` or write a literal as `.0`.",
        example_code=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    printf(\"%d %.1f\\n\", 7 / 2, 7.0 / 2);\n"
            "    return 0;\n"
            "}"
        ),
        template=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    printf(\"%d %.1f\\n\", 7 / 2, 7.0 / ___);\n"
            "    return 0;\n"
            "}"
        ),
        your_turn="Replace `___` with the literal that keeps the second division floating-point.",
        expected_stdout="3 3.5",
        hint="A single digit.",
        skills=["quant", "c-language"],
    ),
    Lesson(
        n=43, stage=5, mode="cscript",
        title="Conditionals and loops",
        scenario="The C for-loop is the syntactic ancestor of every C-family language's for-loop — JavaScript, Java, Go, C#, Rust all stole this shape. Three clauses, separated by semicolons: init, condition, increment. The compiler knows enough about that structure to vectorise the body if it can. That's why the hot loops in numpy, pandas, BLAS are all written like this.",
        learner_goal="Print the first 5 squares using a for-loop.",
        concept="`for (init; condition; update) { body }` — three clauses, executed init once, condition each pass, update after each pass. `for (int i = 1; i <= 5; i++)` runs the body with i = 1, 2, 3, 4, 5. `i++` is shorthand for `i = i + 1` — every C-family language inherited it. `printf(\"%d \", x)` writes an integer followed by a space; no automatic newline.",
        example_code=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    for (int i = 1; i <= 5; i++) {\n"
            "        printf(\"%d \", i * i);\n"
            "    }\n"
            "    printf(\"\\n\");\n"
            "    return 0;\n"
            "}"
        ),
        template=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    for (int i = 1; i <= 5; ___) {\n"
            "        printf(\"%d \", i * i);\n"
            "    }\n"
            "    printf(\"\\n\");\n"
            "    return 0;\n"
            "}"
        ),
        your_turn="Replace `___` with the increment that advances i by 1 each iteration.",
        expected_stdout="1 4 9 16 25",
        hint="Two characters.",
        skills=["quant", "c-language"],
    ),
    Lesson(
        n=44, stage=5, mode="cscript",
        title="Arrays and pointers",
        scenario="The deepest fact about C: arrays *are* pointers, in disguise. An array name in any expression except `sizeof` decays to a pointer to its first element, and `a[i]` is syntactic sugar for `*(a + i)`. This is why pointer arithmetic and array indexing are interchangeable, why numpy's underlying buffer is one C pointer, why the inner loops of every BLAS routine are written with `p++` instead of `a[i+1]`. Internalise this and the next 7 lessons are easy.",
        learner_goal="Use pointer arithmetic to print the third element of an array.",
        concept="Given `int a[5] = {10,20,30,40,50};` and `int *p = a;`, the expressions `a[2]`, `p[2]`, `*(p+2)`, `*(a+2)` all evaluate to `30`. They're four spellings of the same memory access: 'go to the address `a`, add 2 × sizeof(int) bytes, dereference'. The compiler handles the sizeof scaling — you just write `+ 2`.",
        example_code=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    int a[5] = {10, 20, 30, 40, 50};\n"
            "    int *p = a;\n"
            "    printf(\"%d\\n\", *(p + 2));\n"
            "    return 0;\n"
            "}"
        ),
        template=(
            "#include <stdio.h>\n"
            "int main() {\n"
            "    int a[5] = {10, 20, 30, 40, 50};\n"
            "    int *p = a;\n"
            "    printf(\"%d\\n\", *(p + ___));\n"
            "    return 0;\n"
            "}"
        ),
        your_turn="Replace `___` with the offset that gives you the third element.",
        expected_stdout="30",
        hint="Arrays are zero-indexed.",
        skills=["quant", "c-language", "memory"],
    ),
    Lesson(
        n=45, stage=5, mode="cscript",
        title="Structs",
        scenario="Every market-data tick, every order, every position in a quant trading system is a struct. Look at any HFT feed handler's source — Sym (8 bytes), price (8 bytes), qty (4 bytes), side (1 byte), timestamp (8 bytes). The struct layout is the *contract* between the network wire format and the strategy logic. Get the field order wrong and your strategy reads garbage. The matching engines at CME, Eurex, every exchange — same story.",
        learner_goal="Define a Bond struct and print its fields.",
        concept="`struct Name { type field1; type field2; ... };` declares the struct's shape (no instance yet). `struct Name x;` declares an instance. Field access uses `.` on instances (`x.field1 = 42;`) and `->` on pointers (`p->field1 = 42;`). C struct fields sit in declaration order in memory, plus padding to align natural word boundaries — that's why a `double` followed by an `int` typically takes 16 bytes, not 12.",
        example_code=(
            "#include <stdio.h>\n"
            "struct Bond {\n"
            "    double face;\n"
            "    int years;\n"
            "};\n"
            "int main() {\n"
            "    struct Bond b;\n"
            "    b.face = 1000.0;\n"
            "    b.years = 5;\n"
            "    printf(\"face=%.2f years=%d\\n\", b.face, b.years);\n"
            "    return 0;\n"
            "}"
        ),
        template=(
            "#include <stdio.h>\n"
            "struct Bond {\n"
            "    double face;\n"
            "    int years;\n"
            "};\n"
            "int main() {\n"
            "    struct Bond b;\n"
            "    b.face = 1000.0;\n"
            "    b.years = 5;\n"
            "    printf(\"face=%.2f years=%d\\n\", b.face, b.___);\n"
            "    return 0;\n"
            "}"
        ),
        your_turn="Replace `___` with the field name we set above.",
        expected_stdout="face=1000.00 years=5",
        hint="It's right above — five letters.",
        skills=["quant", "c-language", "memory"],
    ),
    Lesson(
        n=46, stage=5, mode="cscript",
        title="Function pointers",
        scenario="C's `qsort` from `<stdlib.h>` is the canonical example: it takes a function pointer that compares two elements, so the same sort routine works for ints, doubles, structs, or any user type. Every C codebase you'll ever read — kernel code, Postgres, Redis, Nginx — uses function pointers for callbacks, dispatch tables, and polymorphism. C has no classes; function pointers are how you get virtual functions.",
        learner_goal="Pass a comparison function to `apply` and print the result.",
        concept="`int (*f)(int)` reads as 'pointer to a function taking int and returning int'. Function names in expressions decay to function pointers — you can pass `square` directly. Inside `apply`, calling `f(x)` is identical to `(*f)(x)`; C allows both. Pre-C99 syntax conventions vary by codebase.",
        example_code=(
            "#include <stdio.h>\n"
            "int square(int x) { return x * x; }\n"
            "int apply(int (*f)(int), int x) { return f(x); }\n"
            "int main() {\n"
            "    printf(\"%d\\n\", apply(square, 7));\n"
            "    return 0;\n"
            "}"
        ),
        template=(
            "#include <stdio.h>\n"
            "int square(int x) { return x * x; }\n"
            "int apply(int (*f)(int), int x) { return f(x); }\n"
            "int main() {\n"
            "    printf(\"%d\\n\", apply(___, 7));\n"
            "    return 0;\n"
            "}"
        ),
        your_turn="Replace `___` with the function name to pass as a function pointer.",
        expected_stdout="49",
        hint="It's the function defined above main.",
        skills=["quant", "c-language"],
    ),
    Lesson(
        n=47, stage=5, mode="cscript",
        title="malloc and free",
        scenario="Memory bugs are why C has a reputation. Forget `free` and your matching engine leaks a few bytes per order — 100M orders/day × 32 bytes = 3GB/day. Free twice and it crashes mid-trading day. Read from freed memory and you might trade off stale prices and not know. Modern languages (Rust, Go, even modern C++) automate this. Production HFT shops still ship vanilla C because the overhead of even Rust's borrow-checker is more than they're willing to pay.",
        learner_goal="Allocate a 3-int buffer with malloc, write to it, print it, then free it.",
        concept="`malloc(N)` returns a `void *` to N bytes of uninitialised heap memory, or `NULL` on failure. Cast the result to your pointer type. Use `sizeof(T)` so the byte count adapts to the platform's int size. Always `free(p)` when done — every malloc must have a matching free. Production C code wraps these in arena/pool allocators for predictable latency, but the malloc/free pattern is the foundation.",
        example_code=(
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "int main() {\n"
            "    int *p = (int *) malloc(3 * sizeof(int));\n"
            "    p[0] = 7; p[1] = 8; p[2] = 9;\n"
            "    printf(\"%d %d %d\\n\", p[0], p[1], p[2]);\n"
            "    free(p);\n"
            "    return 0;\n"
            "}"
        ),
        template=(
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "int main() {\n"
            "    int *p = (int *) malloc(3 * sizeof(int));\n"
            "    p[0] = 7; p[1] = 8; p[2] = 9;\n"
            "    printf(\"%d %d %d\\n\", p[0], p[1], p[2]);\n"
            "    ___(p);\n"
            "    return 0;\n"
            "}"
        ),
        your_turn="Replace `___` with the function that returns memory to the heap.",
        expected_stdout="7 8 9",
        hint="Opposite of malloc — four letters.",
        skills=["quant", "c-language", "memory"],
    ),
    Lesson(
        n=48, stage=5, mode="cwasm",
        title="C ring buffer",
        scenario="The LMAX Disruptor — the open-source ring buffer that powered LMAX Exchange — handled 6 million orders/second on a single thread. The trick is the data structure here: a fixed-size array, two index counters, no allocations during the hot path, lock-free between a single producer and a single consumer. Every HFT feed handler, every kernel network driver, every audio pipeline ships with one. Today's lesson: read the C, run it, see push and pop in action.",
        learner_goal="Read a fixed-size ring buffer in C and run it to see push/pop in action.",
        concept="`head` and `tail` are indices into a fixed-size `slots` array; both wrap modulo `CAP`. `count` distinguishes empty from full (with two indices alone, head == tail can mean either). Push at head, pop from tail — FIFO. Production single-producer-single-consumer (SPSC) versions use atomic ops on the indices and an extra memory fence to publish writes — same shape, lock-free.",
        example_code=(
            "/* See the full source in c-demos/ring_buffer.c */\n"
            "rb_push(&rb, 10);   // pushes succeed until count == CAP\n"
            "rb_pop(&rb, &out);  // pops out the oldest value (FIFO)"
        ),
        source=(
            "#include <stdio.h>\n"
            "#include <stdbool.h>\n"
            "\n"
            "#define CAP 4\n"
            "\n"
            "typedef struct {\n"
            "    int slots[CAP];\n"
            "    int head, tail, count;\n"
            "} RingBuffer;\n"
            "\n"
            "static bool rb_push(RingBuffer *rb, int x) {\n"
            "    if (rb->count == CAP) return false;\n"
            "    rb->slots[rb->head] = x;\n"
            "    rb->head = (rb->head + 1) % CAP;\n"
            "    rb->count++;\n"
            "    return true;\n"
            "}\n"
            "\n"
            "static bool rb_pop(RingBuffer *rb, int *out) {\n"
            "    if (rb->count == 0) return false;\n"
            "    *out = rb->slots[rb->tail];\n"
            "    rb->tail = (rb->tail + 1) % CAP;\n"
            "    rb->count--;\n"
            "    return true;\n"
            "}\n"
            "\n"
            "int main(void) {\n"
            "    RingBuffer rb = {0};\n"
            "    for (int i = 1; i <= 6; i++)\n"
            "        printf(\"push(%d) %s  count=%d\\n\",\n"
            "               i * 10, rb_push(&rb, i * 10) ? \"ok\" : \"FULL\", rb.count);\n"
            "    int v;\n"
            "    while (rb_pop(&rb, &v))\n"
            "        printf(\"pop -> %d  count=%d\\n\", v, rb.count);\n"
            "    return 0;\n"
            "}\n"
        ),
        wasm_demo="ring_buffer",
        expected_stdout_contains="push(50) FULL",
        your_turn="Click Run demo. Watch what happens when push 5 hits a CAP=4 buffer.",
        hint="One push will fail; pops drain in FIFO order.",
        skills=["quant", "c-language", "low-latency", "memory"],
    ),
    Lesson(
        n=49, stage=5, mode="fillblank",
        title="The same ring buffer in Python",
        scenario="Same algorithm, same memory access pattern, same correctness — and 100× slower. The bottleneck isn't the data structure; it's the interpreter dispatch on every `.push()` and `.pop()`. Every attribute lookup is a dict miss-hit, every method call is a frame allocation. This is exactly why the LOB at Citadel Securities is in C, not Python: the algorithm doesn't need rewriting, the runtime does.",
        learner_goal="Implement a fixed-size ring buffer in Python and time it.",
        concept="The Python class below reproduces the C ring buffer's logic exactly: a list as the slots, head/tail/count as integer attributes, modulo to wrap. Each `.push()` call goes through Python's attribute lookup machinery and method dispatch — about a microsecond of overhead per call. A million push+pop pairs takes ~1 second in Python; the C version runs the same million in ~10 milliseconds.",
        example_code=(
            "import time\n"
            "class RingBuffer:\n"
            "    def __init__(self, cap):\n"
            "        self.slots = [0]*cap; self.cap = cap; self.head = self.tail = self.count = 0\n"
            "    def push(self, x):\n"
            "        if self.count == self.cap: return False\n"
            "        self.slots[self.head] = x; self.head = (self.head + 1) % self.cap; self.count += 1\n"
            "        return True\n"
            "    def pop(self):\n"
            "        if self.count == 0: return None\n"
            "        v = self.slots[self.tail]; self.tail = (self.tail + 1) % self.cap; self.count -= 1\n"
            "        return v\n"
            "rb = RingBuffer(4)\n"
            "for i in (10, 20, 30, 40, 50): rb.push(i)\n"
            "out = []\n"
            "while (v := rb.pop()) is not None:\n"
            "    out.append(v)\n"
            "print(out)"
        ),
        template=(
            "import time\n"
            "class RingBuffer:\n"
            "    def __init__(self, cap):\n"
            "        self.slots = [0]*cap; self.cap = cap; self.head = self.tail = self.count = 0\n"
            "    def push(self, x):\n"
            "        if self.count == self.cap: return False\n"
            "        self.slots[self.head] = x; self.head = (self.head + 1) % self.cap; self.count += 1\n"
            "        return True\n"
            "    def pop(self):\n"
            "        if self.count == 0: return None\n"
            "        v = self.slots[self.tail]; self.tail = (self.tail + 1) % self.cap; self.count -= 1\n"
            "        return v\n"
            "rb = RingBuffer(4)\n"
            "for i in (10, 20, 30, 40, 50): rb.___(i)\n"
            "out = []\n"
            "while (v := rb.pop()) is not None:\n"
            "    out.append(v)\n"
            "print(out)"
        ),
        your_turn="Replace `___` with the method name that adds items to the buffer.",
        expected_stdout="[10, 20, 30, 40]",
        hint="Same name as the C version.",
        skills=["quant", "performance", "memory"],
    ),
    Lesson(
        n=50, stage=5, mode="predict",
        title="Cython preview",
        scenario="Cython is the bridge most real Python codebases reach for first when the profiler points to a hot loop. scikit-learn, pandas, statsmodels, gensim — all of them have Cython-compiled critical paths. Annotate types on the few lines that matter, run `cythonize`, and that section runs at near-C speed while the rest of the codebase stays Python. The win is in the inner loop where every interpreter dispatch was costing you.",
        learner_goal="Read a Cython-style snippet and recognise the type annotations.",
        concept="In a `.pyx` file, `cdef int i, n = len(arr)` tells Cython 'these variables are C ints, not Python objects.' The compiler turns the loop body into a real C `for` loop with no Python-object lookups per iteration. Real Cython needs a `setup.py` build step that emits a `.so`; here we just read the shape. The lesson: typing a few hot variables yields 50–100× speedups on numeric loops.",
        example_code=(
            "# This is what a Cython hot-loop sum looks like.\n"
            "# In .pyx form, the compiler produces a tight C loop.\n"
            "def cy_sum(arr):\n"
            "    # cdef int i, n = len(arr); cdef long total = 0\n"
            "    total = 0\n"
            "    for i in range(len(arr)):\n"
            "        total += arr[i]\n"
            "    return total\n"
            "print(cy_sum(list(range(100))))"
        ),
        code=(
            "def cy_sum(arr):\n"
            "    total = 0\n"
            "    for i in range(len(arr)):\n"
            "        total += arr[i]\n"
            "    return total\n"
            "print(cy_sum(list(range(100))))"
        ),
        your_turn="Predict the sum of 0..99 that the function prints.",
        expected_stdout="4950",
        prompt="Type the integer.",
        skills=["quant", "performance", "c-language"],
    ),
    Lesson(
        n=51, stage=5, mode="predict",
        title="cffi preview",
        scenario="Almost every fast Python library is, secretly, a thin Python skin over a `.so`/`.dll` compiled from C, C++ or Fortran. numpy: BLAS + LAPACK. pandas: numpy plus Cython. xgboost: a C++ core. Even psycopg2 wraps libpq. cffi (and its older sibling ctypes) is how that wrapping happens. Read the binding pattern once; you'll recognise it the next time you `pip install` something fast.",
        learner_goal="Recognise the cffi binding pattern — declare the function signature, load the shared object, call it.",
        concept="cffi's three-line pattern: `ffi.cdef('long c_sum(long *arr, int n);')` tells Python the function's C signature; `lib = ffi.dlopen('libsum.so')` loads the compiled library; `lib.c_sum(buf, n)` invokes the C function with a fraction of one microsecond of FFI overhead. The speed you get from `lib.c_sum` is whatever the C library was compiled to — Python is just dispatching the call.",
        example_code=(
            "# Pseudo-cffi usage — the real call goes to a compiled .so.\n"
            "# Here we simulate the same answer with a Python equivalent so\n"
            "# you can see the call shape and result.\n"
            "def c_sum_simulated(arr, n):\n"
            "    return sum(arr[:n])\n"
            "print(c_sum_simulated(list(range(50)), 50))"
        ),
        code=(
            "def c_sum_simulated(arr, n):\n"
            "    return sum(arr[:n])\n"
            "print(c_sum_simulated(list(range(50)), 50))"
        ),
        your_turn="Predict the sum of 0..49 the (simulated) C call returns.",
        expected_stdout="1225",
        prompt="Type the integer.",
        skills=["quant", "performance", "c-language"],
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
    # Wipe + reinsert so renames/renumbering don't leave orphans. Safe
    # while the track has no live learner progress; revisit when it does.
    lines.append("delete from public.challenges where slug like 'quant-%';")
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
