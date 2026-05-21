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
    # Bundled CSV slugs the lesson reads. The worker pre-mounts each under
    # /data/quant/<slug>.csv inside Pyodide's FS before the user code runs.
    datasets: list[str] = field(default_factory=list)

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
        n=6, stage=1, mode="fillblank",
        title="Variance from scratch",
        scenario="Before you reach for `arr.var()`, derive it once. Variance is the mean of squared deviations from the mean — three ops in numpy. Doing this by hand once is what makes a covariance matrix obvious later.",
        learner_goal="Compute variance from the definition, without using `.var()`, and verify against numpy's built-in.",
        concept="Variance σ² = mean((x - μ)²). In numpy: take the deviations (`x - x.mean()`), square them (`** 2`), take the mean. That's it. The square is elementwise broadcasting; the mean is a single reduction.",
        example_code=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "x = rng.normal(loc=0.0, scale=0.02, size=10_000)\n"
            "\n"
            "# By hand — the textbook formula.\n"
            "mu = x.mean()\n"
            "deviations = x - mu\n"
            "var_manual = (deviations ** 2).mean()\n"
            "\n"
            "# Sanity-check against numpy.\n"
            "print(round(var_manual, 6), round(x.var(), 6))\n"
            "print(np.isclose(var_manual, x.var()))"
        ),
        template=(
            "import numpy as np\n"
            "rng = np.random.default_rng(0)\n"
            "x = rng.normal(loc=0.0, scale=0.02, size=10_000)\n"
            "mu = x.mean()\n"
            "deviations = x - mu\n"
            "var_manual = (deviations ___ 2).mean()\n"
            "print(round(var_manual, 6), round(x.var(), 6))\n"
            "print(np.isclose(var_manual, x.var()))"
        ),
        your_turn="Replace `___` with the operator that elementwise-squares the deviations.",
        expected_stdout="0.000408 0.000408\nTrue",
        hint="Two asterisks.",
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
        n=12, stage=1, mode="fillblank",
        title="Vectorising with cumsum",
        scenario="Same answer as yesterday's double-loop, ~200× faster. The cumulative-sum trick — `c[i] − c[i−w]` — is one of the most useful identities in numerical Python. Every senior quant carries it in their head; you should too.",
        learner_goal="Replace the Python rolling-mean loop with `np.cumsum`.",
        concept="If `c = cumsum(x)`, then the window-`w` sum ending at index `i` equals `c[i] − c[i−w]`. Prepend a zero to `c` so the slice arithmetic is clean. One pass, no inner loop, all in C. The same trick gives you rolling sums of any cost function — drawdowns, exposures, anything.",
        example_code=(
            "import numpy as np\n"
            "x = np.array([1, 2, 3, 4, 5, 6], dtype=float)\n"
            "w = 3\n"
            "# Prepend 0 so c[w:] - c[:-w] gives clean window sums.\n"
            "c = np.concatenate(([0], np.cumsum(x)))\n"
            "rolling = (c[w:] - c[:-w]) / w\n"
            "print(rolling)"
        ),
        template=(
            "import numpy as np\n"
            "x = np.array([1, 2, 3, 4, 5, 6], dtype=float)\n"
            "w = 3\n"
            "c = np.concatenate(([0], np.___(x)))\n"
            "rolling = (c[w:] - c[:-w]) / w\n"
            "print(rolling)"
        ),
        your_turn="Replace `___` with the cumulative-sum function.",
        expected_stdout="[2. 3. 4. 5.]",
        hint="Three letters then `sum`.",
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
        n=11, stage=2, mode="fillblank",
        title="DataFrames from CSV",
        scenario="A DataFrame is the workhorse of every research notebook. Loading 10 years of SPY prices takes one call.",
        learner_goal="Load the bundled SPY CSV into a DataFrame and report its shape.",
        concept="`pd.read_csv(path)` returns a DataFrame. `df.shape` gives `(rows, cols)`. The bundled file `/data/quant/spy.csv` has daily OHLCV bars 2015–2025.",
        example_code=(
            "import pandas as pd\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
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
        n=12, stage=2, mode="predict",
        title="Loc versus iloc",
        scenario="`.loc` indexes by label, `.iloc` indexes by position. Mixing them up is the most common pandas bug.",
        learner_goal="Predict the values returned by .iloc and .loc on a small frame.",
        concept="`.iloc[0]` is always the first row. `.loc[0]` is the row labelled `0` — usually the same, until you sort or filter, then the label and the position diverge.",
        example_code=(
            "import pandas as pd\n"
            "df = pd.DataFrame({'price': [100, 101, 99]}, index=['a', 'b', 'c'])\n"
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
        n=13, stage=2, mode="fillblank",
        title="Boolean filtering on real prices",
        scenario="`(df['close'] > df['open'])` returns a boolean Series. Pass it to `df[...]` and you've filtered the frame — vectorised, fast, idiomatic.",
        learner_goal="Count the SPY days where the close was above the open.",
        concept="A comparison between two Series returns a boolean Series the same length. Using it as `df[mask]` keeps only rows where the mask is True. The number of up-days is `mask.sum()`.",
        example_code=(
            "import pandas as pd\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
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
        n=14, stage=2, mode="matplot",
        title="Daily and log returns",
        scenario="Two ways to express returns: simple `(p_t / p_{t-1}) - 1` and log `ln(p_t / p_{t-1})`. They're nearly identical for small moves and additively neat for the log version.",
        learner_goal="Compute simple and log returns from SPY adj_close and plot a histogram of each.",
        concept="`series.pct_change()` is the simple return. Log returns are `np.log(p / p.shift(1))`. Plot histograms with `plt.hist(series.dropna(), bins=50)`.",
        example_code=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "simple = df['adj_close'].pct_change().dropna()\n"
            "log_r = np.log(df['adj_close'] / df['adj_close'].shift(1)).dropna()\n"
            "plt.hist(log_r, bins=60)\n"
            "plt.title('SPY log returns'); plt.xlabel('return'); plt.ylabel('count')\n"
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
        n=15, stage=2, mode="matplot",
        title="Rolling volatility",
        scenario="A 30-day rolling standard deviation of returns, annualised, is the canonical 'realised vol' a strategy gates on.",
        learner_goal="Compute SPY's 30-day rolling vol and plot it against time.",
        concept="`r.rolling(window).std()` is the rolling std. Annualise daily vol with `* np.sqrt(252)`. The first 29 rows are NaN — that's expected.",
        example_code=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change()\n"
            "vol = r.rolling(30).std() * np.sqrt(252)\n"
            "plt.plot(vol)\n"
            "plt.title('SPY 30-day rolling vol'); plt.xlabel('day'); plt.ylabel('annualised vol')\n"
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
        n=16, stage=2, mode="fillblank",
        title="Groupby year",
        scenario="Pandas groupby is split-apply-combine. Group by calendar year and you can answer 'how did each year score?' in two lines.",
        learner_goal="Compute SPY's mean daily return by calendar year.",
        concept="`pd.to_datetime(df['date']).dt.year` extracts the year. `df.groupby(year_series)['adj_close'].pct_change().mean()` then averages within each group. Use `.agg(...)` or a single reduction.",
        example_code=(
            "import pandas as pd\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "df['year'] = pd.to_datetime(df['date']).dt.year\n"
            "by_year = df.groupby('year')['adj_close'].apply(lambda s: s.pct_change().mean())\n"
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
        n=17, stage=2, mode="fillblank",
        title="Aligning two series",
        scenario="Real research mixes tickers with different calendars (BTC trades weekends; SPY doesn't). Aligning on a shared index is the first step of any cross-asset analysis.",
        learner_goal="Merge SPY and AAPL on the date column and confirm row count.",
        concept="`pd.merge(a, b, on='date', how='inner')` keeps rows where both have data. The result has all the columns of both frames, suffixed `_x` and `_y` when names collide.",
        example_code=(
            "import pandas as pd\n"
            "spy = pd.read_csv('/data/quant/spy.csv')\n"
            "aapl = pd.read_csv('/data/quant/aapl.csv')\n"
            "joined = pd.merge(spy, aapl, on='date', how='inner', suffixes=('_spy', '_aapl'))\n"
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
        n=18, stage=2, mode="matplot",
        title="Fitting a normal to returns",
        scenario="Daily returns look gaussian-ish until you check the tails. Plotting a normal pdf over the empirical histogram makes the mismatch visible.",
        learner_goal="Fit a normal to SPY's daily returns and overlay it on the histogram.",
        concept="`scipy.stats.norm.fit(data)` returns `(mu, sigma)`. Generate the pdf with `norm.pdf(xs, mu, sigma)` and overlay with `plt.plot(xs, pdf)`. Set `plt.hist(..., density=True)` so the histogram is on the same scale.",
        example_code=(
            "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
            "from scipy.stats import norm\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change().dropna()\n"
            "mu, sigma = norm.fit(r)\n"
            "xs = np.linspace(r.min(), r.max(), 200)\n"
            "plt.hist(r, bins=80, density=True, alpha=0.6)\n"
            "plt.plot(xs, norm.pdf(xs, mu, sigma))\n"
            "plt.title('SPY daily returns vs normal fit')\n"
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
        n=19, stage=2, mode="fillblank",
        title="OLS beta of AAPL on SPY",
        scenario="Beta of a single stock to the market is the simplest factor regression. statsmodels reports an inference summary — coefficient, std error, p-value, R².",
        learner_goal="Run OLS of AAPL returns on SPY returns and read the slope coefficient.",
        concept="`statsmodels.api.OLS(y, X).fit()` returns a result. `X` must include a constant (use `sm.add_constant`). `.params` is the coefficient vector; the slope is index 1.",
        example_code=(
            "import pandas as pd, statsmodels.api as sm\n"
            "spy = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "aapl = pd.read_csv('/data/quant/aapl.csv')['adj_close'].pct_change()\n"
            "df = pd.concat([spy, aapl], axis=1).dropna()\n"
            "X = sm.add_constant(df.iloc[:, 0])\n"
            "res = sm.OLS(df.iloc[:, 1], X).fit()\n"
            "print(round(res.params.iloc[1], 2))"
        ),
        template=(
            "import pandas as pd, statsmodels.api as sm\n"
            "spy = pd.read_csv('/data/quant/spy.csv')['adj_close'].pct_change()\n"
            "aapl = pd.read_csv('/data/quant/aapl.csv')['adj_close'].pct_change()\n"
            "df = pd.concat([spy, aapl], axis=1).dropna()\n"
            "X = sm.add_constant(df.iloc[:, 0])\n"
            "res = sm.___(df.iloc[:, 1], X).fit()\n"
            "print(round(res.params.iloc[1], 2))"
        ),
        your_turn="Replace `___` with the linear-regression constructor.",
        expected_stdout="1.21",
        hint="Three letters in caps.",
        skills=["quant", "pandas", "statistics", "regression"],
        datasets=["spy", "aapl"],
    ),
    Lesson(
        n=20, stage=2, mode="predict",
        title="Stationarity preview",
        scenario="An ARIMA model needs stationary input. The Augmented Dickey-Fuller test gives a p-value: small p → reject 'unit root' → series is stationary.",
        learner_goal="Read an ADF p-value on SPY prices vs returns and predict which is stationary.",
        concept="`statsmodels.tsa.stattools.adfuller(s)` returns a tuple; element `[1]` is the p-value. Price series usually have p ≈ 1 (random walk, non-stationary); returns usually have p << 0.05.",
        example_code=(
            "import pandas as pd\n"
            "from statsmodels.tsa.stattools import adfuller\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "p_price = adfuller(df['adj_close'])[1]\n"
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
        n=21, stage=3, mode="fillblank",
        title="Present value of a single cash flow",
        scenario="A pound tomorrow is worth less than a pound today. Discounting is the simplest version of every pricing model in finance.",
        learner_goal="Compute the present value of £1000 received in 5 years at a 4% discount rate.",
        concept="`PV = CF / (1 + r)**t` for a single cash flow. With continuous compounding the formula is `PV = CF * exp(-r*t)`. Either is fine; pick the one the textbook is using.",
        example_code=(
            "cf, r, t = 1000, 0.04, 5\n"
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
        n=22, stage=3, mode="fillblank",
        title="Bond yield to maturity",
        scenario="The YTM of a bond is the rate `r` that makes the discounted cash flows equal the price. There's no closed-form solution — you solve it numerically.",
        learner_goal="Find the YTM of a 5-year bond paying a 5% coupon, priced at par (face=100).",
        concept="The price of an annual-coupon bond is `sum(c / (1+r)**t for t in 1..N) + face / (1+r)**N`. When the bond trades at par, YTM equals the coupon rate by definition. `scipy.optimize.brentq` finds the root.",
        example_code=(
            "from scipy.optimize import brentq\n"
            "face, coupon, n, price = 100, 5, 5, 100\n"
            "def npv(r):\n"
            "    return sum(coupon / (1+r)**t for t in range(1, n+1)) + face / (1+r)**n - price\n"
            "ytm = brentq(npv, 0.0001, 0.5)\n"
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
        n=23, stage=3, mode="matplot",
        title="Option payoff diagrams",
        scenario="A call's payoff at expiry is `max(S - K, 0)`. A put's is `max(K - S, 0)`. Plot them and you've drawn every derivatives textbook's first figure.",
        learner_goal="Plot the payoff of a long call with strike 100 over spot prices 60..140.",
        concept="`np.maximum(S - K, 0)` is the vectorised call payoff. Subtract the premium to get profit. `plt.plot(S, payoff)` does the rest.",
        example_code=(
            "import numpy as np, matplotlib.pyplot as plt\n"
            "S = np.linspace(60, 140, 81)\n"
            "K, premium = 100, 5\n"
            "payoff = np.maximum(S - K, 0) - premium\n"
            "plt.plot(S, payoff)\n"
            "plt.title('Long call (K=100)'); plt.xlabel('spot'); plt.ylabel('profit')\n"
            "plt.axhline(0, color='gray', lw=0.5)\n"
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
        n=24, stage=3, mode="fillblank",
        title="Put-call parity",
        scenario="Put-call parity says `C - P = S - K * exp(-r*T)`. It's a no-arbitrage identity — if it breaks, someone is leaving money on the table.",
        learner_goal="Verify put-call parity numerically using the Black-Scholes prices.",
        concept="From parity, given a call price, the matching put is `P = C - S + K * exp(-r*T)`. Compute both sides and they should match to machine precision.",
        example_code=(
            "import numpy as np\n"
            "S, K, r, T, C = 100, 100, 0.04, 1.0, 9.6\n"
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
        n=25, stage=3, mode="fillblank",
        title="Black-Scholes from scratch",
        scenario="The Black-Scholes call price is `S*N(d1) - K*exp(-r*T)*N(d2)` where `d1 = (ln(S/K) + (r + σ²/2)*T) / (σ*sqrt(T))` and `d2 = d1 - σ*sqrt(T)`.",
        learner_goal="Implement the Black-Scholes call price and verify against a textbook example.",
        concept="`scipy.stats.norm.cdf` is N(). Hull's example: S=100, K=100, r=5%, σ=20%, T=1 gives C ≈ 10.45. Match it.",
        example_code=(
            "import numpy as np\n"
            "from scipy.stats import norm\n"
            "S, K, r, sigma, T = 100, 100, 0.05, 0.20, 1.0\n"
            "d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))\n"
            "d2 = d1 - sigma*np.sqrt(T)\n"
            "C = S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)\n"
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
        n=26, stage=3, mode="fillblank",
        title="Greeks: delta of a call",
        scenario="Delta is `dC/dS` — how much the option price moves when the underlying moves £1. For a Black-Scholes call, delta is just `N(d1)`.",
        learner_goal="Compute the delta of an at-the-money call.",
        concept="From the BS derivation, `Δ_call = N(d1)`. For an at-the-money option (S=K), d1 ≈ 0.35 at typical parameters, so delta ≈ 0.64.",
        example_code=(
            "import numpy as np\n"
            "from scipy.stats import norm\n"
            "S, K, r, sigma, T = 100, 100, 0.05, 0.20, 1.0\n"
            "d1 = (np.log(S/K) + (r + sigma**2/2)*T) / (sigma*np.sqrt(T))\n"
            "delta = norm.cdf(d1)\n"
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
        n=27, stage=3, mode="fillblank",
        title="Binomial tree pricer",
        scenario="The CRR (Cox-Ross-Rubinstein) tree builds N steps of up/down moves and prices the option by backward induction. With enough steps it converges to Black-Scholes.",
        learner_goal="Price a European call with a 50-step binomial tree.",
        concept="Set `u = exp(σ * sqrt(dt))`, `d = 1/u`, risk-neutral probability `p = (exp(r*dt) - d)/(u - d)`. Build terminal payoffs, then walk back to t=0 discounting at each step.",
        example_code=(
            "import numpy as np\n"
            "S, K, r, sigma, T, N = 100, 100, 0.05, 0.20, 1.0, 50\n"
            "dt = T/N; u = np.exp(sigma*np.sqrt(dt)); d = 1/u\n"
            "p = (np.exp(r*dt) - d)/(u - d)\n"
            "ST = S * u**np.arange(N+1) * d**(N - np.arange(N+1))\n"
            "vals = np.maximum(ST - K, 0)\n"
            "for _ in range(N):\n"
            "    vals = np.exp(-r*dt) * (p*vals[1:] + (1-p)*vals[:-1])\n"
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
        n=28, stage=3, mode="matplot",
        title="Monte Carlo option pricing",
        scenario="Simulate many terminal stock prices under risk-neutral dynamics; average the discounted payoffs. The estimate converges as `1 / sqrt(N)` — plot to see it.",
        learner_goal="Price a European call by Monte Carlo and plot the running estimate's convergence.",
        concept="Under risk-neutral GBM, `S_T = S0 * exp((r - σ²/2)*T + σ*sqrt(T)*Z)` with `Z ~ N(0,1)`. Average `exp(-r*T) * max(S_T - K, 0)`. As N grows, the running mean settles on the BS price.",
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
        n=29, stage=3, mode="matplot",
        title="Mean-variance frontier",
        scenario="Markowitz's efficient frontier is the locus of minimum-variance portfolios for each target return. Plot it for SPY + AAPL + TLT and you've recreated the most-cited chart in finance.",
        learner_goal="Sweep target returns and plot the resulting min-variance volatilities.",
        concept="With covariance `Σ` and means `μ`, the closed-form min-variance frontier uses constants `a = 1ᵀΣ⁻¹1`, `b = μᵀΣ⁻¹1`, `c = μᵀΣ⁻¹μ`. Variance at target `t` is `(a·t² − 2bt + c) / (ac − b²)`. No optimisation loop — one pass.",
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
        n=30, stage=3, mode="fillblank",
        title="Sharpe, max drawdown",
        scenario="The Sharpe ratio is mean return divided by standard deviation, annualised. Max drawdown is the worst peak-to-trough on the equity curve.",
        learner_goal="Compute SPY's annualised Sharpe ratio and max drawdown.",
        concept="Annualised Sharpe = `(r.mean() * 252) / (r.std() * sqrt(252))` for daily data. Max drawdown is `(equity / equity.cummax() - 1).min()`. Both are scalar — print them rounded.",
        example_code=(
            "import pandas as pd, numpy as np\n"
            "df = pd.read_csv('/data/quant/spy.csv')\n"
            "r = df['adj_close'].pct_change().dropna()\n"
            "sharpe = (r.mean()*252) / (r.std()*np.sqrt(252))\n"
            "eq = (1 + r).cumprod()\n"
            "dd = (eq / eq.cummax() - 1).min()\n"
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
        n=31, stage=4, mode="fillblank",
        title="sklearn fit and predict",
        scenario="scikit-learn's API is the same for every estimator: `.fit(X, y)` learns, `.predict(X)` infers, `.score(X, y)` reports R² or accuracy.",
        learner_goal="Train a linear regression on a toy dataset and verify the perfect fit.",
        concept="Every sklearn estimator inherits `fit/predict/score`. With perfectly linear data, `LinearRegression` recovers the coefficient exactly and `.score` returns 1.0.",
        example_code=(
            "import numpy as np\n"
            "from sklearn.linear_model import LinearRegression\n"
            "X = np.arange(10).reshape(-1, 1)\n"
            "y = 2 * X.ravel() + 3\n"
            "model = LinearRegression().fit(X, y)\n"
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
        n=32, stage=4, mode="predict",
        title="Lookahead bias",
        scenario="In finance ML the order of your rows matters. A random `train_test_split` lets the model see the future — and inflates your Sharpe spectacularly.",
        learner_goal="Recognise why a chronological split is the honest baseline.",
        concept="`sklearn.model_selection.train_test_split(shuffle=False)` keeps order intact. The first 80% becomes training, last 20% becomes test. Anything else for time series is a bug.",
        example_code=(
            "from sklearn.model_selection import train_test_split\n"
            "import numpy as np\n"
            "X = np.arange(10).reshape(-1, 1); y = np.arange(10)\n"
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
        n=33, stage=4, mode="fillblank",
        title="Momentum signal regression",
        scenario="A 5-day momentum is a classic feature: did the stock go up over the last week? Regressing next-day return on this is the smallest non-trivial ML model in finance.",
        learner_goal="Fit a linear regression of next-day SPY return on lagged 5-day return; report the R².",
        concept="`mom_5 = r.shift(1).rolling(5).sum()`. Drop NaNs, split chronologically with shuffle=False, fit `LinearRegression`. R² near zero is *expected* — markets are hard.",
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
        n=34, stage=4, mode="fillblank",
        title="Random forest direction classifier",
        scenario="A forest of decision trees can spot non-linear patterns a linear model would miss — at the cost of being a black box.",
        learner_goal="Train a 100-tree random forest to predict next-day direction from 5-day momentum and rolling volatility.",
        concept="`RandomForestClassifier(n_estimators=100)` builds 100 trees. Two features: 5-day momentum and 20-day rolling std. The label is `np.sign(next_return)`. Score is accuracy on a chronological test split.",
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
        n=35, stage=4, mode="fillblank",
        title="Time-series cross-validation",
        scenario="`TimeSeriesSplit` slices a chronological frame into expanding-window CV folds. Every test fold starts after its train fold — no leakage.",
        learner_goal="Run a 5-fold time-series CV on a linear model and average the fold scores.",
        concept="`TimeSeriesSplit(n_splits=5)` yields five (train_idx, test_idx) pairs. Loop, fit on train_idx, score on test_idx, average. Use `cross_val_score(...)` for the one-liner.",
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
        n=36, stage=4, mode="predict",
        title="The p-hacked Sharpe trap",
        scenario="Try 1000 random strategies; the best one will look brilliant by chance. Lopez de Prado calls this 'backtest overfitting' and warns it dwarfs every other risk in quant ML.",
        learner_goal="Predict the maximum Sharpe of 1000 pure-noise strategies — and feel why a 'great' backtest in isolation is meaningless.",
        concept="Generate 1000 random return series with mean 0 and σ=0.01. Compute each one's annualised Sharpe. The MAX across them is several standard deviations above zero — pure chance, not skill.",
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
        n=37, stage=5, mode="cwasm",
        title="Why C",
        scenario="Python is where research lives. C is where the inner loop of a matching engine runs a billion times a day. The latency budget is the difference.",
        learner_goal="Read a real C limit-order-book node and see it execute.",
        concept="The demo below is a small sorted-list LOB written in C, compiled to WASM at `-O3`. Even this tiny example is faster than the equivalent pure-Python: no per-element interpreter overhead, no object headers, just contiguous memory and direct pointer chasing.",
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
        n=38, stage=5, mode="cscript",
        title="Hello C",
        scenario="The simplest C program — `printf` plus `return 0`. Same shape every C program in the world has at its core.",
        learner_goal="Print 'hello, C!' from a C program.",
        concept="`#include <stdio.h>` exposes `printf`. `main` must return an `int`. Strings live between double quotes; `\\n` is a newline.",
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
        n=39, stage=5, mode="cscript",
        title="Types and arithmetic",
        scenario="C has explicit types: `int` is integer, `double` is 8-byte float. Mixing them follows promotion rules — division is the most surprising.",
        learner_goal="Print the integer division of 7/2 and the floating-point division of 7.0/2.0.",
        concept="`7 / 2` is integer division in C — it gives `3`, not `3.5`. To get the real quotient, one operand must be a float: `7.0 / 2` or `(double)7 / 2`.",
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
        n=40, stage=5, mode="cscript",
        title="Conditionals and loops",
        scenario="C's `for` loop has three parts: init, test, increment. Same idea as Python but with explicit types and braces.",
        learner_goal="Print the first 5 squares using a for-loop.",
        concept="`for (int i = 1; i <= 5; i++) { ... }` runs the body 5 times with i from 1 to 5. `printf(\"%d \", i*i)` prints each square. After the loop, print a newline.",
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
        n=41, stage=5, mode="cscript",
        title="Arrays and pointers",
        scenario="In C, an array's name decays to a pointer to its first element. Pointer arithmetic walks the array byte-by-byte — `*(p + 2)` is the same as `p[2]`.",
        learner_goal="Use pointer arithmetic to print the third element of an array.",
        concept="Given `int a[5] = {10,20,30,40,50};` and `int *p = a;`, all of `a[2]`, `p[2]`, `*(p+2)`, `*(a+2)` are `30`. They're four ways of writing the same thing.",
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
        n=42, stage=5, mode="cscript",
        title="Structs",
        scenario="A struct groups related fields. Every market-data tick, every order, every position in a quant system is a struct.",
        learner_goal="Define a Bond struct and print its fields.",
        concept="`struct Bond { double face; int years; };` declares the shape. `struct Bond b;` declares an instance. Fields are set via `.` (`b.face = 1000.0;`).",
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
        n=43, stage=5, mode="cscript",
        title="Function pointers",
        scenario="A function pointer lets you pass behaviour, not just data. C's `qsort` takes one — every C program that sorts a struct uses this pattern.",
        learner_goal="Pass a comparison function to `apply` and print the result.",
        concept="`int (*f)(int)` is the type 'pointer to a function taking int and returning int'. Pass `square` to `apply(square, 5)` and `apply` calls it as `f(x)`.",
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
        n=44, stage=5, mode="cscript",
        title="malloc and free",
        scenario="C makes you allocate and free memory yourself. Forgetting `free` is a leak; freeing twice is a crash. Modern languages hide this; C surfaces it.",
        learner_goal="Allocate a 3-int buffer with malloc, write to it, print it, then free it.",
        concept="`malloc(3 * sizeof(int))` allocates 12 bytes (on most systems). Cast the result to `int *`. Always `free(p)` when done. The pattern: allocate → use → free.",
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
        n=45, stage=5, mode="cwasm",
        title="C ring buffer",
        scenario="A ring buffer wraps a fixed-size array with head/tail indices. Every HFT feed handler has one. Same pattern: push when not full, pop when not empty.",
        learner_goal="Read a fixed-size ring buffer in C and run it to see push/pop in action.",
        concept="`head` and `tail` indices wrap modulo CAP. `count` distinguishes empty from full. Real production buffers use atomic ops on the indices for SPSC lock-free use; this demo skips that — same pattern, single-threaded.",
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
        n=46, stage=5, mode="fillblank",
        title="The same ring buffer in Python",
        scenario="The Python translation works. It's also slow. Same algorithm, same memory pattern — what's missing is the compiled inner loop.",
        learner_goal="Implement a fixed-size ring buffer in Python and time it.",
        concept="A Python list with manual head/tail indices reproduces the C ring buffer's logic. Each push or pop is one method call — Python's per-call overhead is roughly 1µs, so a million ops takes ~1s where C takes ~10ms.",
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
        n=47, stage=5, mode="predict",
        title="Cython preview",
        scenario="Cython is Python with C type annotations. Add `cdef int` to a hot loop and you've trimmed most of the interpreter overhead — same code shape, 50–100× speedup.",
        learner_goal="Read a Cython-style snippet and recognise the type annotations.",
        concept="A Cython hot loop looks like Python with extra declarations: `cdef int i, n = len(arr)`. The compiler turns the loop body into a C loop with no Python object lookups. Real Cython needs a build step; here we read.",
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
        n=48, stage=5, mode="predict",
        title="cffi preview",
        scenario="cffi lets Python call functions from a `.so` you compiled yourself. The same loop in a C library, called from Python, is what numpy does internally for every ufunc.",
        learner_goal="Recognise the cffi binding pattern — declare the function signature, load the shared object, call it.",
        concept="cffi's pattern: `ffi.cdef('long c_sum(long *arr, int n);')`, `lib = ffi.dlopen('libsum.so')`, then `lib.c_sum(arr, len(arr))`. You're calling C from Python through a thin shim — the speed is the C code's, not Python's.",
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
