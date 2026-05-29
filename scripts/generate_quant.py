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
    **<verb>.** ...
    **Expected.** `...`

The action verb in the third slot is unified across modes — one imperative
per mode, same grammar:
    predict   → Predict the output.
    fillblank → Fill in the gap.
    matplot   → Make the plot.
    debug     → Find the bug.        (no Example block; editor IS the code)
    skeleton  → Implement the function.
    apifetch  → Build the client.
    cscript   → Fill in the gap.
    cwasm     → (no third slot; read-only demo)
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
    # One-sentence "Why this matters" tag rendered after **Expected.**.
    # Used selectively (finance lessons especially) to justify the technique
    # rather than just state the mechanic.
    why_this: str = ""
    # If set, replaces the numeric "{n:02d}" in the slug. Used for
    # sub-arc lessons that slot between integer lesson numbers,
    # e.g. n_label="28a" → slug "quant-28a-...". UUID still derives
    # from int n so each lesson is uniquely identified.
    n_label: str = ""
    # If non-zero, overrides the default order_index (= n) used for
    # display ordering in the module. Sub-arc lessons set this so the
    # new lessons display in their intended slot between existing ints.
    order_index_override: int = 0
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
    # Generic multi-file extension. Map of filename → content for additional
    # readonly files mounted alongside tests/test_solution.py — used by
    # multi-file capstones (e.g. mock_market.py for the trading-algorithm
    # lessons). Distinct from `mock_api_py` to keep the apifetch contract
    # uncluttered.
    extra_readonly: dict[str, str] = field(default_factory=dict)
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
        label = self.n_label if self.n_label else f"{self.n:02d}"
        return f"quant-{label}-{kebab}"

    @property
    def display_index(self) -> int:
        # Default: n * 100. Multiplying gives sub-arc lessons room to slot
        # between existing integer lessons via an explicit override
        # (e.g. quant-28a sets order_index_override=2810 to sit between
        # quant-28 at 2800 and quant-29 at 2900).
        return self.order_index_override if self.order_index_override else self.n * 100

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
            if self.why_this:
                lines.append("")
                lines.append(f"**Why this?** {self.why_this.strip()}")
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
        # Action verb is unified across modes: imperative-active, ends with
        # a period. {predict / fillblank / matplot / debug / skeleton /
        # apifetch} — five shapes, five verbs, same grammar slot.
        if self.mode == "predict":
            lines.append(f"**Predict the output.** {self.your_turn.strip()}")
        elif self.mode == "matplot":
            lines.append(f"**Make the plot.** {self.your_turn.strip()}")
        else:
            lines.append(f"**Fill in the gap.** {self.your_turn.strip()}")
        lines.append("")
        expected = self.expected_stdout or self.expected_stdout_contains
        expected_one_line = expected.replace("\n", " · ")
        if expected_one_line:
            lines.append(f"**Expected.** `{expected_one_line}`")
        if self.why_this:
            lines.append("")
            lines.append(f"**Why this?** {self.why_this.strip()}")
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
            for filename, content in self.extra_readonly.items():
                # Multi-file capstones mount additional readonly modules
                # (e.g. mock_market.py) alongside the tests.
                readonly_files.insert(0, filename)
                inline_map[filename] = content
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


# ---- Shared fixtures for multi-file trading-algorithm capstones ----
#
# `mock_market.py` is mounted as a readonly module alongside each capstone's
# tests. It exposes two symbols (SPY synthetic GBM, AAPL synthetic but
# correlated with SPY) so pair-trading lessons can reach for both without
# touching the real disk or shipping a CSV.
MOCK_MARKET_PY = (
    "\"\"\"Read-only synthetic market data feed.\n"
    "\n"
    "Deterministic daily bars for SPY and AAPL. SPY is a GBM with drift\n"
    "and 1.2% daily vol; AAPL is the SPY return path scaled by beta=1.3\n"
    "plus an idiosyncratic noise term. Reproducible across runs.\n"
    "\"\"\"\n"
    "from dataclasses import dataclass\n"
    "import numpy as np\n"
    "\n"
    "\n"
    "@dataclass(frozen=True)\n"
    "class Bar:\n"
    "    date: str\n"
    "    open: float\n"
    "    high: float\n"
    "    low: float\n"
    "    close: float\n"
    "    volume: int\n"
    "\n"
    "\n"
    "def _build_bars(symbol: str, seed: int, n_days: int = 750):\n"
    "    rng = np.random.default_rng(seed)\n"
    "    if symbol == 'SPY':\n"
    "        shocks = rng.normal(0.0003, 0.012, n_days)\n"
    "    elif symbol == 'AAPL':\n"
    "        spy_rng = np.random.default_rng(42)\n"
    "        spy_shocks = spy_rng.normal(0.0003, 0.012, n_days)\n"
    "        # AAPL ≈ 1.3 × SPY + idiosyncratic noise.\n"
    "        idio = rng.normal(0.0005, 0.009, n_days)\n"
    "        shocks = 1.3 * spy_shocks + idio\n"
    "    else:\n"
    "        raise ValueError(f'Unknown symbol seed for: {symbol}')\n"
    "    closes = 100.0 * np.exp(np.cumsum(shocks))\n"
    "    opens = np.empty(n_days)\n"
    "    opens[0] = 100.0\n"
    "    opens[1:] = closes[:-1] * (1 + rng.normal(0, 0.001, n_days - 1))\n"
    "    highs = np.maximum(opens, closes) * (\n"
    "        1 + np.abs(rng.normal(0, 0.005, n_days))\n"
    "    )\n"
    "    lows = np.minimum(opens, closes) * (\n"
    "        1 - np.abs(rng.normal(0, 0.005, n_days))\n"
    "    )\n"
    "    volumes = (50_000_000 + rng.normal(0, 5_000_000, n_days)).astype(int)\n"
    "    volumes = np.maximum(volumes, 1_000_000)\n"
    "    bars = []\n"
    "    for i in range(n_days):\n"
    "        bars.append(Bar(\n"
    "            date=f'2023-day-{i:03d}',\n"
    "            open=float(opens[i]),\n"
    "            high=float(highs[i]),\n"
    "            low=float(lows[i]),\n"
    "            close=float(closes[i]),\n"
    "            volume=int(volumes[i]),\n"
    "        ))\n"
    "    return bars\n"
    "\n"
    "\n"
    "_BARS = {\n"
    "    'SPY': _build_bars('SPY', seed=42),\n"
    "    'AAPL': _build_bars('AAPL', seed=137),\n"
    "}\n"
    "\n"
    "\n"
    "class Market:\n"
    "    \"\"\"Historical data feed; supports SPY and AAPL.\"\"\"\n"
    "\n"
    "    def history(self, symbol: str = 'SPY'):\n"
    "        if symbol not in _BARS:\n"
    "            raise ValueError(f'Unknown symbol: {symbol}')\n"
    "        return list(_BARS[symbol])\n"
)


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
        scenario="numpy is C and BLAS under a Python skin. Reductions like `.sum()` run as one tight C loop instead of a million interpreted iterations — typically 50-100× faster. The example below runs both side-by-side so you can see the gap.",
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
        scenario="Three constructors handle nearly every input you'll build: `np.array` for known values, `np.zeros` for pre-allocated buffers, `np.linspace` for evenly-spaced sampling grids (the canonical y-axis builder for IV surfaces).",
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
        scenario="Broadcasting lets you apply a 1-D operation across a 2-D array without writing nested loops — numpy expands the smaller shape virtually, with no copy.",
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
        prompt="Predict the printed output.",
        skills=["quant", "numpy", "vectorisation"],
    ),
    Lesson(
        n=4, stage=1, mode="predict",
        title="Broadcasting gotchas",
        scenario="Shape-mismatch errors are the most common numpy bug. The fix rule is shorter than the error message: align dimensions from the right, insert size-1 axes where they don't.",
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
        prompt="Predict the printed output.",
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
        n=7, stage=1, mode="debug",
        title="Covariance via matrix algebra",
        scenario="Risk engine at a fund: `covariance_matrix(X)` is used everywhere — Sharpe, Markowitz, VaR. A reviewer notices the diagonal is slightly off from `numpy.cov(X, rowvar=False)` but only when the input has non-zero mean. The bug is in the function below: a one-line omission that quants miss because finance returns are usually zero-mean enough to hide it.",
        learner_goal="Spot the missing step in `covariance_matrix` and add it.",
        concept="The covariance formula is `(X − μ)ᵀ(X − μ) / (n − 1)` — note the `μ` subtraction. If you skip the demean, you compute the *uncentered* second moment instead. On zero-mean series the result is close enough that nobody notices; on a series with drift it's silently wrong by `μᵀμ` per entry. Sample variance divides by `n − 1`, not `n`, to be unbiased — same convention as last lesson.",
        example_code="",
        editable_template=(
            "\"\"\"Sample covariance matrix of column-stacked return series.\n"
            "\n"
            "Shape contract: input X is (n_obs, n_assets); output is\n"
            "(n_assets, n_assets) sample covariance. Compared against\n"
            "`np.cov(X, rowvar=False)` in tests.\n"
            "\"\"\"\n"
            "import numpy as np\n"
            "\n"
            "\n"
            "def covariance_matrix(X: np.ndarray) -> np.ndarray:\n"
            "    \"\"\"Return the sample covariance matrix of X.\n"
            "\n"
            "    Steps the reviewer expects:\n"
            "      1. Demean each column.\n"
            "      2. Cross-product Xdᵀ Xd.\n"
            "      3. Divide by (n - 1) for the unbiased estimator.\n"
            "    \"\"\"\n"
            "    n = X.shape[0]\n"
            "    return (X.T @ X) / (n - 1)\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "\n"
            "\n"
            "def covariance_matrix(X: np.ndarray) -> np.ndarray:\n"
            "    n = X.shape[0]\n"
            "    Xd = X - X.mean(axis=0)\n"
            "    return (Xd.T @ Xd) / (n - 1)\n"
        ),
        tests_py=(
            "\"\"\"Covariance-matrix correctness tests, including the with-drift trap.\"\"\"\n"
            "import numpy as np\n"
            "import pytest\n"
            "\n"
            "from solution import covariance_matrix\n"
            "\n"
            "\n"
            "def test_matches_numpy_cov_zero_mean():\n"
            "    rng = np.random.default_rng(0)\n"
            "    X = rng.normal(0.0, 1.0, (1000, 2))\n"
            "    assert np.allclose(covariance_matrix(X), np.cov(X, rowvar=False))\n"
            "\n"
            "\n"
            "def test_matches_numpy_cov_with_drift():\n"
            "    # The KEY test — fails when demean is missing.\n"
            "    rng = np.random.default_rng(1)\n"
            "    X = rng.normal(0.0, 1.0, (500, 3)) + np.array([10.0, -5.0, 2.5])\n"
            "    assert np.allclose(covariance_matrix(X), np.cov(X, rowvar=False))\n"
            "\n"
            "\n"
            "def test_output_shape_is_n_assets_by_n_assets():\n"
            "    X = np.random.default_rng(2).normal(size=(100, 4))\n"
            "    out = covariance_matrix(X)\n"
            "    assert out.shape == (4, 4)\n"
            "\n"
            "\n"
            "def test_diagonal_is_per_asset_variance():\n"
            "    rng = np.random.default_rng(3)\n"
            "    X = rng.normal(0.0, 1.0, (500, 2))\n"
            "    out = covariance_matrix(X)\n"
            "    # Sample variance per column matches np.var(..., ddof=1).\n"
            "    assert abs(out[0, 0] - X[:, 0].var(ddof=1)) < 1e-12\n"
            "    assert abs(out[1, 1] - X[:, 1].var(ddof=1)) < 1e-12\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_matches_numpy_cov_zero_mean",
                "Matches np.cov on a zero-mean input (passes even when the bug is present).",
            ),
            (
                "tests/test_solution.py::test_matches_numpy_cov_with_drift",
                "Matches np.cov when the input has non-zero column means — the trap test.",
            ),
            (
                "tests/test_solution.py::test_output_shape_is_n_assets_by_n_assets",
                "Output shape is (n_assets, n_assets).",
            ),
            (
                "tests/test_solution.py::test_diagonal_is_per_asset_variance",
                "Diagonal entries equal per-column sample variance (ddof=1).",
            ),
        ],
        your_turn="The function passes its smoke test on zero-mean data and silently fails when the columns have drift. Read the docstring's step list and add the missing line.",
        hint="One line, before computing the cross product. The docstring's first step gives it away.",
        skills=["quant", "numpy", "linear-algebra", "statistics"],
    ),
    Lesson(
        n=8, stage=1, mode="fillblank",
        title="Reproducible random numbers",
        scenario="Random draws need a seed if you want the same answer twice. `np.random.default_rng(seed)` makes the result deterministic — non-negotiable for any backtest you intend to reproduce.",
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
        n=9, stage=1, mode="debug",
        title="Statistical reductions",
        scenario="Junior data scientist refactors a research notebook into a `summary_stats` function the desk imports. Production runs fine for a week, then the head of risk emails: 'your 95th percentile drawdown numbers are tiny — are you in basis points?' She isn't. The bug is on one line: a units confusion between numpy and pandas that's caught half the data team at one point or another.",
        learner_goal="Find the single line where the percentile call is wrong, fix the argument, and pass the tests.",
        concept="numpy's `np.percentile(arr, q)` takes `q` in **0–100** (a percent). pandas' `Series.quantile(q)` takes `q` in **0–1** (a fraction). Same idea, different API. Calling `np.percentile(r, 0.95)` gives you the 0.95th percentile — essentially the minimum of your distribution — not the 95th. This is THE units bug in everyday quant Python; happens to everyone once.",
        example_code="",
        editable_template=(
            "\"\"\"Summary statistics used by the desk's daily research email.\"\"\"\n"
            "import numpy as np\n"
            "\n"
            "\n"
            "def summary_stats(r: np.ndarray) -> dict:\n"
            "    \"\"\"Return mean, std, and 95th percentile of a return series.\n"
            "\n"
            "    The 95th percentile (`p95`) is the value such that 95% of\n"
            "    observations are at or below it — used to size tail bands.\n"
            "    \"\"\"\n"
            "    return {\n"
            "        \"mean\": float(r.mean()),\n"
            "        \"std\": float(r.std()),\n"
            "        \"p95\": float(np.percentile(r, 0.95)),\n"
            "    }\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "\n"
            "\n"
            "def summary_stats(r: np.ndarray) -> dict:\n"
            "    return {\n"
            "        \"mean\": float(r.mean()),\n"
            "        \"std\": float(r.std()),\n"
            "        \"p95\": float(np.percentile(r, 95)),\n"
            "    }\n"
        ),
        tests_py=(
            "\"\"\"summary_stats: mean, std, and 95th percentile checks.\"\"\"\n"
            "import numpy as np\n"
            "import pytest\n"
            "\n"
            "from solution import summary_stats\n"
            "\n"
            "\n"
            "def test_mean_is_correct_on_synthetic_returns():\n"
            "    rng = np.random.default_rng(0)\n"
            "    r = rng.normal(0.001, 0.02, 10_000)\n"
            "    s = summary_stats(r)\n"
            "    assert abs(s[\"mean\"] - 0.0011) < 1e-3\n"
            "\n"
            "\n"
            "def test_std_is_correct_on_synthetic_returns():\n"
            "    rng = np.random.default_rng(0)\n"
            "    r = rng.normal(0.001, 0.02, 10_000)\n"
            "    s = summary_stats(r)\n"
            "    assert abs(s[\"std\"] - 0.02) < 5e-4\n"
            "\n"
            "\n"
            "def test_p95_is_a_high_value_not_a_low_one():\n"
            "    # The KEY test. The buggy version asks numpy for the 0.95th\n"
            "    # percentile, which is near the minimum (~ -0.06 here), not\n"
            "    # the 95th percentile (~ +0.034).\n"
            "    rng = np.random.default_rng(0)\n"
            "    r = rng.normal(0.001, 0.02, 10_000)\n"
            "    s = summary_stats(r)\n"
            "    assert s[\"p95\"] > 0.02  # 95th percentile must be on the right tail.\n"
            "\n"
            "\n"
            "def test_p95_matches_numpy_reference():\n"
            "    rng = np.random.default_rng(0)\n"
            "    r = rng.normal(0.001, 0.02, 10_000)\n"
            "    s = summary_stats(r)\n"
            "    assert abs(s[\"p95\"] - float(np.percentile(r, 95))) < 1e-12\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_mean_is_correct_on_synthetic_returns",
                "`mean` is close to the configured drift (0.001) within 1e-3.",
            ),
            (
                "tests/test_solution.py::test_std_is_correct_on_synthetic_returns",
                "`std` is close to the configured vol (0.02) within 5e-4.",
            ),
            (
                "tests/test_solution.py::test_p95_is_a_high_value_not_a_low_one",
                "`p95` must be in the right tail (> 0.02), catching the 0.95-vs-95 mistake.",
            ),
            (
                "tests/test_solution.py::test_p95_matches_numpy_reference",
                "`p95` matches `np.percentile(r, 95)` exactly.",
            ),
        ],
        your_turn="Three of the four tests pass already. The fourth one tells you the percentile call has the wrong units. One character — sometimes two — fixes it.",
        hint="numpy wants the percentile in 0–100, not 0–1.",
        skills=["quant", "numpy", "statistics"],
    ),
    Lesson(
        n=10, stage=1, mode="predict",
        title="Why numpy is fast",
        scenario="numpy stores arrays as contiguous C buffers and runs reductions as one C loop. The sum below operates over a million elements — same answer Python's `sum()` would give, in a fraction of the time.",
        learner_goal="Run a sum of one million elements and recognise the printed value.",
        concept="numpy stores arrays as contiguous C buffers — every adjacent element is one cache line away. A `.sum()` runs as one C loop with SIMD-friendly access; the L1 cache loads 64-byte runs and the CPU never stalls on memory. A Python list stores pointers to boxed `PyObject` ints scattered across the heap — every element costs a cache miss and an interpreter dispatch. Same arithmetic, completely different access pattern.",
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
        prompt="Predict the printed output.",
        skills=["quant", "numpy", "performance"],
    ),
    Lesson(
        n=11, stage=1, mode="predict",
        title="The slow Python rolling-mean",
        scenario="The naive way to compute a rolling mean is a double-loop — outer index, inner window-sum. It works, but the inner loop runs `window × len(x)` times. Read it once so you recognise the pattern before it sneaks into your code.",
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
        prompt="Predict the printed output.",
        skills=["quant", "numpy", "performance"],
    ),
    Lesson(
        n=12, stage=1, mode="skeleton",
        title="Vectorising with cumsum",
        scenario="The cumulative-sum identity turns a window sum into one subtraction of two prefix sums. Same answer as yesterday's double-loop; one numpy pass instead of `len(x) × w` Python operations. It's the canonical trick behind every rolling reduction in pandas.",
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
        n=56, stage=1, mode="skeleton",
        n_label="12a",
        order_index_override=1210,
        title="Refactor for speed",
        scenario="The naive rolling mean below is correct — its tests pass. But it's a double loop, and the senior on the desk has flagged it as too slow for the live tick feed. Same function signature, same answer, 10× faster: the cumsum identity from the previous lesson. This time the test suite includes a wall-clock budget you have to beat.",
        learner_goal="Replace the correct-but-slow double-loop rolling_mean with the cumsum-vectorised version; pass both the correctness suite and a 150 ms wall-clock budget on a 200k-element input.",
        concept="Code can be correct and still be wrong. In a real trading system, anything that touches the per-tick path has a latency budget; missing the budget is a production failure even if the output is bit-exact. Vectorisation is the highest-leverage move on the Python side — push the work into a tight C loop inside numpy, eliminate the per-element interpreter dispatch from the previous lesson. Same identity as quant-12: a prefix-sum difference computes any window-sum in one numpy pass.",
        example_code="",
        editable_template=(
            "\"\"\"Rolling mean: correctness PLUS a wall-clock budget.\n"
            "\n"
            "The implementation below is correct but slow. Replace it with the\n"
            "cumsum-based version from the previous lesson so the performance\n"
            "test passes.\n"
            "\"\"\"\n"
            "import numpy as np\n"
            "\n"
            "\n"
            "def rolling_mean(x: np.ndarray, w: int) -> np.ndarray:\n"
            "    \"\"\"Mean of every contiguous window of width w.\n"
            "\n"
            "    Returns ndarray of shape (len(x) - w + 1,). Same contract as\n"
            "    the previous lesson's reference.\n"
            "    \"\"\"\n"
            "    n = len(x)\n"
            "    out = np.empty(n - w + 1)\n"
            "    for i in range(n - w + 1):\n"
            "        s = 0.0\n"
            "        for j in range(w):\n"
            "            s += float(x[i + j])\n"
            "        out[i] = s / w\n"
            "    return out\n"
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
            "\"\"\"rolling_mean: correctness + 150ms wall-clock budget.\n"
            "\n"
            "The performance budget is sized so the naive double-loop fails\n"
            "comfortably (~600-1200ms in CPython, ~3-6s in Pyodide) and the\n"
            "cumsum version passes with margin (~5-20ms).\n"
            "\"\"\"\n"
            "import time\n"
            "import numpy as np\n"
            "import pytest\n"
            "\n"
            "from solution import rolling_mean\n"
            "\n"
            "\n"
            "def test_correctness_hand_calc():\n"
            "    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])\n"
            "    assert np.allclose(rolling_mean(x, 3), [2.0, 3.0, 4.0, 5.0])\n"
            "\n"
            "\n"
            "def test_correctness_window_one_returns_input():\n"
            "    x = np.array([10.0, 20.0, 30.0])\n"
            "    assert np.allclose(rolling_mean(x, 1), x)\n"
            "\n"
            "\n"
            "def test_correctness_on_random_input():\n"
            "    rng = np.random.default_rng(0)\n"
            "    x = rng.normal(size=500)\n"
            "    w = 12\n"
            "    naive = np.array([x[i : i + w].mean() for i in range(len(x) - w + 1)])\n"
            "    assert np.allclose(rolling_mean(x, w), naive)\n"
            "\n"
            "\n"
            "def test_performance_under_150ms():\n"
            "    # 200k elements, window 100 → 20M ops in the naive double loop.\n"
            "    # The cumsum identity is two numpy passes; budget 150ms\n"
            "    # comfortably fits the latter and excludes the former.\n"
            "    rng = np.random.default_rng(42)\n"
            "    x = rng.normal(size=200_000)\n"
            "    # Warm any first-call JIT / caching by running once before timing.\n"
            "    rolling_mean(x, 100)\n"
            "    t0 = time.perf_counter()\n"
            "    rolling_mean(x, 100)\n"
            "    elapsed_ms = (time.perf_counter() - t0) * 1000\n"
            "    assert elapsed_ms < 150, (\n"
            "        f\"Took {elapsed_ms:.1f}ms; needs to be < 150ms — vectorise.\"\n"
            "    )\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_correctness_hand_calc",
                "rolling_mean([1..6], 3) is [2, 3, 4, 5] — correctness sanity.",
            ),
            (
                "tests/test_solution.py::test_correctness_window_one_returns_input",
                "Window of 1 returns the input unchanged.",
            ),
            (
                "tests/test_solution.py::test_correctness_on_random_input",
                "Matches a Python list-comprehension reference on a 500-element series.",
            ),
            (
                "tests/test_solution.py::test_performance_under_150ms",
                "200k elements, window 100, completes in < 150 ms (the naive impl can't).",
            ),
        ],
        your_turn="The function is correct — three tests already pass. The fourth (performance) fails because the body is a double-loop. Replace it with the cumsum-identity vectorised version from the previous lesson.",
        hint="`c = np.concatenate(([0.0], np.cumsum(x)))`; then `(c[w:] - c[:-w]) / w`. Two lines, no inner loop.",
        why_this="Correct-but-slow is a production failure on a per-tick code path. Vectorising — pushing the inner loop into C inside numpy — is the highest-leverage performance move you can make in Python before reaching for Cython, Numba, or C extensions.",
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
        scenario="`.loc` indexes by label, `.iloc` indexes by integer position. They look interchangeable when the index is the default 0..n-1, but they diverge the moment the index becomes anything else — a date, a ticker, a slice.",
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
        prompt="Predict the printed output.",
        skills=["quant", "pandas"],
    ),
    Lesson(
        n=16, stage=2, mode="debug",
        title="Boolean filtering on real prices",
        scenario="Trader on the desk asks: 'how many days did SPY gap up — open above yesterday's close?' Easy enough, the junior thinks. They ship a function. The trader runs it, gets a number that looks reasonable, and now the strategy sizes positions against that count. Except the function counts the wrong thing — a subtle index shift that makes the answer almost-but-not-quite right. The kind of bug a 30-second look-at-the-tape would have caught.",
        learner_goal="Find the off-by-one in the gap-up counter and fix it.",
        concept="A gap-up day is when today's *open* is above *yesterday's* close — `df['open'] > df['close'].shift(1)`. The `.shift(1)` is the entire point: without it you're comparing today's open to today's close, which is closer to 'is this a green candle?' than 'is there a gap'. A real production bug pattern: someone wrote the comparison without the shift, the function compiles, returns a number, and the strategy quietly sizes against the wrong signal.",
        example_code="",
        editable_template=(
            "\"\"\"Count gap-up days in a price frame.\"\"\"\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "def count_gap_ups(df: pd.DataFrame) -> int:\n"
            "    \"\"\"Return the number of days where today's open is strictly\n"
            "    above YESTERDAY's close. `df` has columns open, close, ...\n"
            "    indexed in chronological order.\n"
            "    \"\"\"\n"
            "    mask = df[\"open\"] > df[\"close\"]\n"
            "    return int(mask.sum())\n"
        ),
        reference_solution=(
            "import pandas as pd\n"
            "\n"
            "\n"
            "def count_gap_ups(df: pd.DataFrame) -> int:\n"
            "    mask = df[\"open\"] > df[\"close\"].shift(1)\n"
            "    return int(mask.sum())\n"
        ),
        tests_py=(
            "\"\"\"Gap-up counter correctness.\"\"\"\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import count_gap_ups\n"
            "\n"
            "\n"
            "def _frame(open_, close):\n"
            "    return pd.DataFrame({\"open\": open_, \"close\": close})\n"
            "\n"
            "\n"
            "def test_strict_gap_up_hand_calc():\n"
            "    # Closes: 100, 101, 99, 105. Opens: 100, 102, 100, 99.\n"
            "    # Day 0: no prior close. Day 1: open 102 > close[0]=100 -> gap.\n"
            "    # Day 2: open 100 < close[1]=101 -> no gap.\n"
            "    # Day 3: open 99  < close[2]=99  -> no gap (strict >).\n"
            "    df = _frame([100, 102, 100, 99], [100, 101, 99, 105])\n"
            "    assert count_gap_ups(df) == 1\n"
            "\n"
            "\n"
            "def test_no_gap_when_open_equals_prior_close():\n"
            "    # opens 100, 100, 101; closes 100, 101, 99.\n"
            "    # Day 1: open[1]=100 == close[0]=100 -> no strict gap.\n"
            "    # Day 2: open[2]=101 == close[1]=101 -> no strict gap.\n"
            "    df = _frame([100, 100, 101], [100, 101, 99])\n"
            "    assert count_gap_ups(df) == 0\n"
            "\n"
            "\n"
            "def test_all_gaps_when_each_open_clears_prior_close():\n"
            "    # Each open strictly above the previous day's close.\n"
            "    df = _frame([100, 105, 110, 120], [100, 102, 108, 115])\n"
            "    # Days 1, 2, 3 all gap up; Day 0 has no prior so doesn't count.\n"
            "    assert count_gap_ups(df) == 3\n"
            "\n"
            "\n"
            "def test_zero_on_one_row():\n"
            "    df = _frame([100], [101])\n"
            "    assert count_gap_ups(df) == 0\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_strict_gap_up_hand_calc",
                "Hand-calculated 4-row example yields 1 gap-up day.",
            ),
            (
                "tests/test_solution.py::test_no_gap_when_open_equals_prior_close",
                "Equality is not a gap — uses strict > comparison.",
            ),
            (
                "tests/test_solution.py::test_all_gaps_when_each_open_clears_prior_close",
                "Monotone-up tape produces (n - 1) gap-up days.",
            ),
            (
                "tests/test_solution.py::test_zero_on_one_row",
                "Single-row frame has no prior close — zero gap-ups.",
            ),
        ],
        your_turn="The function looks like it counts gap-up days but doesn't. Compare your output to the test expectation on the 4-row example, then read the docstring carefully — one method call is missing.",
        hint="`yesterday's close` is `df['close'].shift(1)`.",
        skills=["quant", "pandas", "vectorisation"],
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
        n=19, stage=2, mode="skeleton",
        title="Groupby year",
        scenario="Annual board-deck time at a long-only fund. The PM wants a one-row-per-year table: 'mean daily return, daily vol, Sharpe.' You ship `by_year_metrics`. The shape — `to_datetime` → `groupby` → multi-stat aggregate — repeats across every per-period attribution the firm does (monthly, by-quarter, by-regime). Internalise it once and 30% of pandas is the same pattern.",
        learner_goal="Implement `by_year_metrics(df)` so it returns a DataFrame indexed by year with mean_daily, vol_daily, and sharpe columns.",
        concept="`pd.to_datetime(df['date']).dt.year` extracts the calendar year. `df.groupby(year)['adj_close'].apply(...)` splits the frame into one slice per year and runs your function on each. To get three statistics into a single output, return a `pd.Series` per group and pandas will pivot them into columns. Sharpe (rf=0) is `mean_daily / vol_daily` — same formula a project tested earlier.",
        example_code="",
        editable_template=(
            "\"\"\"By-year performance attribution.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "def by_year_metrics(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    \"\"\"Per-calendar-year mean, vol, and Sharpe of daily returns.\n"
            "\n"
            "    Parameters\n"
            "    ----------\n"
            "    df : has 'date' (parsable string or datetime) and 'adj_close' columns.\n"
            "\n"
            "    Returns\n"
            "    -------\n"
            "    DataFrame indexed by `year` (int) with columns:\n"
            "        - 'mean_daily': mean of pct_change inside the year\n"
            "        - 'vol_daily' : std  of pct_change inside the year (default ddof=1)\n"
            "        - 'sharpe'    : mean_daily / vol_daily  (rf = 0; not annualised)\n"
            "\n"
            "    Implementation tips:\n"
            "      - Drop the first NaN that pct_change introduces.\n"
            "      - Group by `pd.to_datetime(df['date']).dt.year`.\n"
            "      - Use `.apply(...)` returning a Series so pandas pivots\n"
            "        the three stats into three columns of the output.\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement by_year_metrics\")\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "def by_year_metrics(df: pd.DataFrame) -> pd.DataFrame:\n"
            "    out = df.copy()\n"
            "    out['year'] = pd.to_datetime(out['date']).dt.year\n"
            "    out['ret'] = out['adj_close'].pct_change()\n"
            "    out = out.dropna(subset=['ret'])\n"
            "\n"
            "    def _stats(s: pd.Series) -> pd.Series:\n"
            "        mu = float(s.mean())\n"
            "        sd = float(s.std())\n"
            "        return pd.Series({\n"
            "            'mean_daily': mu,\n"
            "            'vol_daily': sd,\n"
            "            'sharpe': mu / sd if sd > 0 else float('nan'),\n"
            "        })\n"
            "\n"
            "    return out.groupby('year')['ret'].apply(_stats).unstack()\n"
        ),
        tests_py=(
            "\"\"\"by_year_metrics: per-year mean / vol / Sharpe.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import by_year_metrics\n"
            "\n"
            "\n"
            "def _df(start: str, n: int, drift: float, vol: float, seed: int) -> pd.DataFrame:\n"
            "    rng = np.random.default_rng(seed)\n"
            "    rets = rng.normal(drift, vol, n)\n"
            "    prices = 100 * np.exp(np.cumsum(rets))\n"
            "    dates = pd.date_range(start, periods=n, freq='B')\n"
            "    return pd.DataFrame({'date': dates.strftime('%Y-%m-%d'), 'adj_close': prices})\n"
            "\n"
            "\n"
            "def test_columns_and_index_name():\n"
            "    df = _df('2020-01-01', 252, 0.0005, 0.01, seed=0)\n"
            "    out = by_year_metrics(df)\n"
            "    assert list(out.columns) == ['mean_daily', 'vol_daily', 'sharpe']\n"
            "    assert out.index.name == 'year'\n"
            "\n"
            "\n"
            "def test_two_year_split():\n"
            "    # 500 business days starting Jan 2020 spans 2020 + 2021.\n"
            "    df = _df('2020-01-01', 500, 0.0005, 0.01, seed=1)\n"
            "    out = by_year_metrics(df)\n"
            "    assert set(out.index) == {2020, 2021}\n"
            "\n"
            "\n"
            "def test_sharpe_equals_mean_over_vol():\n"
            "    df = _df('2018-01-01', 252, 0.001, 0.012, seed=2)\n"
            "    out = by_year_metrics(df)\n"
            "    for year in out.index:\n"
            "        row = out.loc[year]\n"
            "        assert abs(row['sharpe'] - row['mean_daily'] / row['vol_daily']) < 1e-9\n"
            "\n"
            "\n"
            "def test_mean_in_right_ballpark():\n"
            "    # Generator drift 0.0005 → mean_daily should land in (0.0001, 0.001).\n"
            "    df = _df('2019-01-01', 252, 0.0005, 0.01, seed=3)\n"
            "    out = by_year_metrics(df)\n"
            "    mean_2019 = out.loc[2019, 'mean_daily']\n"
            "    assert 0.0001 < abs(mean_2019) < 0.002 or mean_2019 > 0  # noise band\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_columns_and_index_name",
                "Output has columns [mean_daily, vol_daily, sharpe] and index named 'year'.",
            ),
            (
                "tests/test_solution.py::test_two_year_split",
                "500 business days starting 2020 splits into two year rows (2020, 2021).",
            ),
            (
                "tests/test_solution.py::test_sharpe_equals_mean_over_vol",
                "Sharpe column equals mean_daily / vol_daily per row.",
            ),
            (
                "tests/test_solution.py::test_mean_in_right_ballpark",
                "Per-year mean is in the right ballpark of the configured generator drift.",
            ),
        ],
        your_turn="Implement `by_year_metrics`. The docstring spells out the steps; you can return a Series-per-group from `.apply` to get the three-column output.",
        hint="Inside the `.apply` callback, return `pd.Series({'mean_daily': ..., 'vol_daily': ..., 'sharpe': ...})` — pandas pivots it into columns automatically.",
        skills=["quant", "pandas", "time-series"],
    ),
    Lesson(
        n=20, stage=2, mode="debug",
        title="Aligning two series",
        scenario="Crypto-vs-equities cross-asset research at a macro shop. The PM wants BTC paired against SPY for the days both traded. A junior writes the merge, runs a quick sanity check on length, looks fine. Two weeks later a backtest result no-one can reproduce gets traced back to this function: it returns more rows than it should because the join type silently fills weekends with NaNs instead of dropping them. Spot the wrong keyword.",
        learner_goal="Find the wrong `how=` argument that lets weekends sneak into the joined frame; fix it so only shared dates survive.",
        concept="`pd.merge(a, b, on='date', how='inner')` is the safest default — keep only dates present in BOTH frames. `how='left'` carries every row of `a` through, filling missing `b` columns with NaN; `how='outer'` does both. With BTC on one side (trades weekends) and SPY on the other (doesn't), `left`/`right`/`outer` quietly leave NaN-padded rows that downstream code may not check for. The bug shows up as a silently-too-large result — exactly the shape this lesson's tests catch.",
        example_code="",
        editable_template=(
            "\"\"\"Align two return frames on shared trading dates.\"\"\"\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "def aligned_returns(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:\n"
            "    \"\"\"Merge two daily-bar frames on 'date', keeping only dates that\n"
            "    appear in BOTH inputs. The output has both frames' columns,\n"
            "    suffixed _a / _b on the collisions.\n"
            "\n"
            "    Used to pair crypto vs equity tapes, US vs Europe, paper vs\n"
            "    benchmark.\n"
            "    \"\"\"\n"
            "    return pd.merge(a, b, on='date', how='outer', suffixes=('_a', '_b'))\n"
        ),
        reference_solution=(
            "import pandas as pd\n"
            "\n"
            "\n"
            "def aligned_returns(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:\n"
            "    return pd.merge(a, b, on='date', how='inner', suffixes=('_a', '_b'))\n"
        ),
        tests_py=(
            "\"\"\"aligned_returns: shared-date inner join with no NaN leakage.\"\"\"\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import aligned_returns\n"
            "\n"
            "\n"
            "SPY_DATES = ['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']\n"
            "BTC_DATES = [\n"
            "    '2024-01-02', '2024-01-03', '2024-01-04',\n"
            "    '2024-01-05', '2024-01-06', '2024-01-07',  # weekend prints\n"
            "]\n"
            "\n"
            "\n"
            "def _spy():\n"
            "    return pd.DataFrame({'date': SPY_DATES, 'close': [470.0, 472.0, 471.5, 473.0]})\n"
            "\n"
            "\n"
            "def _btc():\n"
            "    return pd.DataFrame({'date': BTC_DATES, 'close': [44000.0, 45000.0, 45500.0, 46000.0, 46500.0, 47000.0]})\n"
            "\n"
            "\n"
            "def test_only_shared_dates_survive():\n"
            "    out = aligned_returns(_spy(), _btc())\n"
            "    assert list(out['date']) == SPY_DATES  # 4 weekday rows; weekends dropped\n"
            "\n"
            "\n"
            "def test_no_nan_in_close_columns():\n"
            "    out = aligned_returns(_spy(), _btc())\n"
            "    # Both close columns must be fully populated.\n"
            "    assert out['close_a'].isna().sum() == 0\n"
            "    assert out['close_b'].isna().sum() == 0\n"
            "\n"
            "\n"
            "def test_row_count_equals_min_of_two_inputs():\n"
            "    out = aligned_returns(_spy(), _btc())\n"
            "    assert len(out) == min(len(_spy()), len(_btc()))\n"
            "\n"
            "\n"
            "def test_no_extra_rows_appear_when_inputs_identical():\n"
            "    df = _spy()\n"
            "    out = aligned_returns(df, df)\n"
            "    assert len(out) == len(df)\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_only_shared_dates_survive",
                "Result's date column equals the intersection of the two inputs (no weekend rows).",
            ),
            (
                "tests/test_solution.py::test_no_nan_in_close_columns",
                "Neither suffixed close column has any NaN — the join didn't leave gaps.",
            ),
            (
                "tests/test_solution.py::test_row_count_equals_min_of_two_inputs",
                "Output has exactly min(len(a), len(b)) rows when one frame's dates are a subset.",
            ),
            (
                "tests/test_solution.py::test_no_extra_rows_appear_when_inputs_identical",
                "Joining a frame to itself returns the same number of rows.",
            ),
        ],
        your_turn="Read what the docstring promises ('only dates that appear in BOTH'), then check the `how=` argument — pandas has a one-word swap that fixes it.",
        hint="Same name as the SQL join that keeps only the intersection.",
        skills=["quant", "pandas", "time-series"],
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
        n=57, stage=2, mode="skeleton",
        n_label="21a",
        order_index_override=2110,
        title="Refactor returns for speed",
        scenario="The returns calculator below is correct but uses `df.apply(lambda)` — pandas's slowest per-row idiom. On a 10k-row tape it's fine; on a billion-row tick tape it's a 30-minute job that should take 30 seconds. Same answer, vectorised pandas: drop the apply, use `pct_change` (or its log-return cousin) directly.",
        learner_goal="Replace the apply-lambda returns calculator with vectorised pandas; pass the correctness suite AND a wall-clock budget on a 50k-row frame.",
        concept="`Series.apply(lambda)` invokes the Python function once per element — the same per-element interpreter cost that the previous numpy lessons tried to avoid. The vectorised pandas idiom for simple returns is `s.pct_change()`; for log returns it's `np.log(s / s.shift(1))`. Both run as compiled numpy under the hood. The speedup over apply is typically 50-200×.",
        example_code="",
        editable_template=(
            "\"\"\"Daily returns from a price series — correct, but slow.\n"
            "\n"
            "The contract: take a DataFrame with column 'adj_close' (chronological\n"
            "order) and return a Series of simple daily returns of length\n"
            "len(df) - 1. Replace the body with a vectorised pandas call so the\n"
            "perf test passes.\n"
            "\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "def daily_returns(df: pd.DataFrame) -> pd.Series:\n"
            "    \"\"\"Simple daily returns of df['adj_close'].\"\"\"\n"
            "    closes = df['adj_close']\n"
            "    rets = []\n"
            "    # Slow: per-row Python dispatch through .iloc on each step.\n"
            "    for i in range(1, len(closes)):\n"
            "        prev = float(closes.iloc[i - 1])\n"
            "        cur = float(closes.iloc[i])\n"
            "        rets.append((cur - prev) / prev)\n"
            "    return pd.Series(rets, index=closes.index[1:])\n"
        ),
        reference_solution=(
            "import pandas as pd\n"
            "\n"
            "\n"
            "def daily_returns(df: pd.DataFrame) -> pd.Series:\n"
            "    return df['adj_close'].pct_change().dropna()\n"
        ),
        tests_py=(
            "\"\"\"daily_returns: correctness + 100ms wall-clock budget on 50k rows.\n"
            "\n"
            "The naive per-row Python loop typically takes ~500ms-1s in CPython\n"
            "on 50k rows; the vectorised pct_change is ~5-15ms. Budget 100ms\n"
            "comfortably separates them.\n"
            "\"\"\"\n"
            "import time\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import daily_returns\n"
            "\n"
            "\n"
            "def _gbm_frame(n: int, seed: int = 0) -> pd.DataFrame:\n"
            "    rng = np.random.default_rng(seed)\n"
            "    shocks = rng.normal(0.0, 0.01, n)\n"
            "    closes = 100.0 * np.exp(np.cumsum(shocks))\n"
            "    return pd.DataFrame({'adj_close': closes})\n"
            "\n"
            "\n"
            "def test_correctness_small_input():\n"
            "    df = pd.DataFrame({'adj_close': [100.0, 110.0, 99.0]})\n"
            "    r = daily_returns(df)\n"
            "    assert len(r) == 2\n"
            "    assert abs(float(r.iloc[0]) - 0.10) < 1e-9\n"
            "    assert abs(float(r.iloc[1]) - (-0.10)) < 1e-9\n"
            "\n"
            "\n"
            "def test_correctness_matches_pct_change():\n"
            "    df = _gbm_frame(1_000, seed=7)\n"
            "    expected = df['adj_close'].pct_change().dropna()\n"
            "    got = daily_returns(df)\n"
            "    assert np.allclose(got.values, expected.values)\n"
            "\n"
            "\n"
            "def test_correctness_no_nan_no_leading_row():\n"
            "    df = _gbm_frame(100)\n"
            "    r = daily_returns(df)\n"
            "    assert r.isna().sum() == 0\n"
            "    assert len(r) == len(df) - 1\n"
            "\n"
            "\n"
            "def test_performance_under_80ms_on_100k_rows():\n"
            "    df = _gbm_frame(100_000, seed=42)\n"
            "    # Warm-up call to take any first-time setup off the clock.\n"
            "    daily_returns(df)\n"
            "    t0 = time.perf_counter()\n"
            "    daily_returns(df)\n"
            "    elapsed_ms = (time.perf_counter() - t0) * 1000\n"
            "    assert elapsed_ms < 80, (\n"
            "        f\"Took {elapsed_ms:.1f}ms; needs to be < 80ms — drop the loop.\"\n"
            "    )\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_correctness_small_input",
                "Hand-calculated 3-row frame: returns are +0.10 then -0.10.",
            ),
            (
                "tests/test_solution.py::test_correctness_matches_pct_change",
                "Matches df['adj_close'].pct_change().dropna() on a 1k-row GBM frame.",
            ),
            (
                "tests/test_solution.py::test_correctness_no_nan_no_leading_row",
                "No NaN in output; length is len(df) - 1.",
            ),
            (
                "tests/test_solution.py::test_performance_under_80ms_on_100k_rows",
                "100k-row frame completes in < 80 ms (the per-row Python loop can't).",
            ),
        ],
        your_turn="Three correctness tests already pass. The fourth (performance) fails because the body uses `apply(lambda)` plus a Python loop. Replace both with a single vectorised pandas call.",
        hint="`df['adj_close'].pct_change().dropna()` is one line. That's the whole function body.",
        why_this="`apply(lambda)` is the pandas equivalent of a Python for-loop — same per-row interpreter dispatch. Vectorised pandas (`pct_change`, `rolling`, `groupby`-aggregations) pushes the work into compiled C and typically buys 50-200× speedup.",
        skills=["quant", "pandas", "vectorisation", "performance"],
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
        prompt="Predict the printed output.",
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
        why_this="Every pricing model in finance — bond YTM, DCF, option pricing — is a sum of present values. Get the one-cashflow case automatic and the rest is just iteration.",
        skills=["quant", "options"],
    ),
    Lesson(
        n=25, stage=3, mode="skeleton",
        title="Bond yield to maturity",
        scenario="The treasury desk at a primary dealer quotes prices on a hundred-strong universe of bonds; the buy-side queries the system in YTM space. The function below sits between those two views — given face, coupon, term, and current price, return the YTM. No closed form exists; you root-find. Same code shape ships at every fund running a fixed-income book.",
        learner_goal="Implement `ytm(face, coupon, n_years, price)` using scipy's brentq root-finder.",
        concept="An annual-coupon bond's fair price is `sum(c / (1+r)**t for t in 1..N) + face / (1+r)**N`. The YTM is the rate `r` that makes this equation balance against the market price. `scipy.optimize.brentq(f, lo, hi)` does a robust bisection — needs `f(lo)` and `f(hi)` to straddle zero. A 0.0001..0.50 bracket covers any realistic bond. At par (price == face), YTM exactly equals the coupon rate — your cheapest sanity check.",
        example_code="",
        editable_template=(
            "\"\"\"Bond yield-to-maturity via numerical root-finding.\"\"\"\n"
            "from scipy.optimize import brentq\n"
            "\n"
            "\n"
            "def ytm(face: float, coupon: float, n_years: int, price: float) -> float:\n"
            "    \"\"\"Return the annual-compounding YTM of a vanilla coupon bond.\n"
            "\n"
            "    Parameters\n"
            "    ----------\n"
            "    face     : redemption value at maturity (e.g. 100)\n"
            "    coupon   : annual coupon payment in face units (e.g. 5 means 5%)\n"
            "    n_years  : whole years to maturity\n"
            "    price    : current market price\n"
            "\n"
            "    Returns\n"
            "    -------\n"
            "    float — the YTM as a decimal (0.05 for 5%).\n"
            "\n"
            "    Implementation:\n"
            "      - Define an `npv(r)` closure that returns\n"
            "        PV_of_all_cashflows(r) - price.\n"
            "      - Call brentq with bracket (0.0001, 0.5).\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement ytm\")\n"
        ),
        reference_solution=(
            "from scipy.optimize import brentq\n"
            "\n"
            "\n"
            "def ytm(face: float, coupon: float, n_years: int, price: float) -> float:\n"
            "    def npv(r: float) -> float:\n"
            "        return (\n"
            "            sum(coupon / (1 + r) ** t for t in range(1, n_years + 1))\n"
            "            + face / (1 + r) ** n_years\n"
            "            - price\n"
            "        )\n"
            "    return float(brentq(npv, 0.0001, 0.5))\n"
        ),
        tests_py=(
            "\"\"\"YTM correctness across par / discount / premium pricings.\"\"\"\n"
            "import pytest\n"
            "\n"
            "from solution import ytm\n"
            "\n"
            "\n"
            "def test_par_bond_yields_coupon_rate():\n"
            "    # 5-year, 5% coupon, price == face → YTM == coupon rate.\n"
            "    assert abs(ytm(100, 5, 5, 100) - 0.05) < 1e-6\n"
            "\n"
            "\n"
            "def test_discount_bond_yields_above_coupon():\n"
            "    # 10-year, 3% coupon, priced below par → YTM > 3%.\n"
            "    y = ytm(100, 3, 10, 90)\n"
            "    assert y > 0.03\n"
            "    # Hand-check approximation; tight tolerance against a known answer.\n"
            "    assert abs(y - 0.0428) < 0.001\n"
            "\n"
            "\n"
            "def test_premium_bond_yields_below_coupon():\n"
            "    # 7-year, 6% coupon, priced above par → YTM < 6%.\n"
            "    y = ytm(100, 6, 7, 110)\n"
            "    assert y < 0.06\n"
            "    assert abs(y - 0.0432) < 0.001\n"
            "\n"
            "\n"
            "def test_zero_coupon_bond():\n"
            "    # Zero-coupon, 5-year, face 100, price 78 → YTM ≈ (100/78)^(1/5)-1 ≈ 5.09%.\n"
            "    y = ytm(100, 0, 5, 78)\n"
            "    assert abs(y - 0.0509) < 1e-3\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_par_bond_yields_coupon_rate",
                "Par bond's YTM equals the coupon rate.",
            ),
            (
                "tests/test_solution.py::test_discount_bond_yields_above_coupon",
                "Discount bond (price < par) has YTM above the coupon rate.",
            ),
            (
                "tests/test_solution.py::test_premium_bond_yields_below_coupon",
                "Premium bond (price > par) has YTM below the coupon rate.",
            ),
            (
                "tests/test_solution.py::test_zero_coupon_bond",
                "Zero-coupon bond's YTM matches the closed-form (price/face)^(1/n) - 1.",
            ),
        ],
        your_turn="Implement `ytm`. Define the NPV closure that returns PV minus price; root-find with brentq on (0.0001, 0.5). The docstring spells out both steps.",
        hint="`brentq(npv, 0.0001, 0.5)` — your NPV closure returns 0 at the YTM.",
        why_this="Bond markets quote in price; risk and portfolio analytics live in yield space. This function is the translation layer every fixed-income system runs millions of times a day.",
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
        why_this="Sketching payoff at expiry is the first thing a vol trader does when sized a new structure. Pattern-match the shape and you can spot a structurer's misprice in seconds.",
        skills=["quant", "options", "matplotlib"],
    ),
    Lesson(
        n=27, stage=3, mode="debug",
        title="Put-call parity",
        scenario="Vol-desk arb-checking script: every option quote streams in, gets compared against put-call parity, and any violation greater than the bid-ask spread fires an alert. The junior who wrote `parity_put_from_call` got the sign convention wrong on the discount factor — so the script's flagging *all* the quotes as arbitrages. Find the one-character bug before the trading floor mutes the alarm.",
        learner_goal="Find the sign error in the discount factor that makes the parity-implied put inflate instead of deflate the strike.",
        concept="Put-call parity: `C − P = S − K · exp(−rT)`. Solve for P: `P = C − S + K · exp(−rT)`. The discount factor `exp(−rT)` is always < 1 for positive `r` (today's worth of a future strike is less than face). Flipping the sign — `exp(+rT)` — inflates the future strike, gives you a put price hundreds of dollars too high, and turns every quote into a false-positive arb signal.",
        example_code="",
        editable_template=(
            "\"\"\"Put price implied by put-call parity from a call price.\"\"\"\n"
            "import math\n"
            "\n"
            "\n"
            "def parity_put_from_call(\n"
            "    call: float, S: float, K: float, r: float, T: float\n"
            ") -> float:\n"
            "    \"\"\"Return the no-arb put price implied by C - P = S - K*exp(-r*T).\n"
            "\n"
            "    Parameters\n"
            "    ----------\n"
            "    call : current call price\n"
            "    S    : spot\n"
            "    K    : strike\n"
            "    r    : risk-free rate (annualised)\n"
            "    T    : years to expiry\n"
            "    \"\"\"\n"
            "    return call - S + K * math.exp(r * T)\n"
        ),
        reference_solution=(
            "import math\n"
            "\n"
            "\n"
            "def parity_put_from_call(\n"
            "    call: float, S: float, K: float, r: float, T: float\n"
            ") -> float:\n"
            "    return call - S + K * math.exp(-r * T)\n"
        ),
        tests_py=(
            "\"\"\"parity_put_from_call: sign-of-exponent check on the discount.\"\"\"\n"
            "import math\n"
            "import pytest\n"
            "\n"
            "from solution import parity_put_from_call\n"
            "\n"
            "\n"
            "def test_at_money_textbook_example():\n"
            "    # S=K=100, r=4%, T=1y, call=9.6 → put ≈ 5.68.\n"
            "    put = parity_put_from_call(9.6, 100, 100, 0.04, 1.0)\n"
            "    assert abs(put - 5.68) < 0.02\n"
            "\n"
            "\n"
            "def test_zero_rate_collapses_to_call_minus_S_plus_K():\n"
            "    # With r=0, exp(-r*T)=1, so put = call - S + K.\n"
            "    put = parity_put_from_call(7.0, 100, 100, 0.0, 1.0)\n"
            "    assert abs(put - 7.0) < 1e-12  # call - S + K = 7 - 100 + 100\n"
            "\n"
            "\n"
            "def test_high_rate_pulls_put_below_call():\n"
            "    # At higher rate, the PV(K) shrinks, so put should be SMALLER.\n"
            "    put_low = parity_put_from_call(9.6, 100, 100, 0.02, 1.0)\n"
            "    put_high = parity_put_from_call(9.6, 100, 100, 0.10, 1.0)\n"
            "    assert put_high < put_low\n"
            "\n"
            "\n"
            "def test_at_par_at_zero_rate_equals_call_when_S_equals_K():\n"
            "    # Edge: zero rate, S=K. Then exp(-rT)=1 → put = call.\n"
            "    put = parity_put_from_call(7.5, 100, 100, 0.0, 1.0)\n"
            "    assert abs(put - 7.5) < 1e-12\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_at_money_textbook_example",
                "ATM example with r=4%, T=1y, call=9.60 → put ≈ 5.68.",
            ),
            (
                "tests/test_solution.py::test_zero_rate_collapses_to_call_minus_S_plus_K",
                "At r=0, exp(-rT)=1 — checks the discount factor doesn't blow up.",
            ),
            (
                "tests/test_solution.py::test_high_rate_pulls_put_below_call",
                "Higher rate → smaller PV(K) → smaller put price (catches sign flip).",
            ),
            (
                "tests/test_solution.py::test_at_par_at_zero_rate_equals_call_when_S_equals_K",
                "Zero-rate ATM case has put == call exactly.",
            ),
        ],
        your_turn="The function uses `exp(r*T)` where the no-arb formula needs `exp(-r*T)`. One character flip.",
        hint="Negative rate times time goes inside the exponent.",
        why_this="Parity is the dealer's no-arb sanity check on every quote. If your puts and calls don't satisfy it within bid-ask, one of them is mispriced — guaranteed.",
        skills=["quant", "options"],
    ),
    Lesson(
        n=28, stage=3, mode="skeleton",
        title="Black-Scholes from scratch",
        scenario="Options interview at any market-maker — Citadel Securities, IMC, Optiver, Jane Street — opens with: 'implement Black-Scholes from first principles, no libraries beyond a normal CDF.' It's FizzBuzz for derivatives engineers. The function you write here is the same one that's been hand-rolled in every options-trading codebase since 1973. After today it's muscle memory.",
        learner_goal="Implement `bs_call(S, K, r, sigma, T)` from the closed-form Black-Scholes formula.",
        concept="Call price `C = S·N(d1) − K·exp(−rT)·N(d2)` where `d1 = (ln(S/K) + (r + σ²/2)·T) / (σ·√T)` and `d2 = d1 − σ·√T`. `N(·)` is the standard normal CDF (`scipy.stats.norm.cdf`). The canonical Hull example (S=K=100, r=5%, σ=20%, T=1y) gives C ≈ 10.4506 — every BS implementation in the world matches that number, and tests usually verify it first.",
        example_code="",
        editable_template=(
            "\"\"\"Black-Scholes European call from first principles.\"\"\"\n"
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def bs_call(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"Return the Black-Scholes call price.\n"
            "\n"
            "    Parameters\n"
            "    ----------\n"
            "    S     : spot price\n"
            "    K     : strike\n"
            "    r     : risk-free rate (annualised, continuous compounding)\n"
            "    sigma : volatility (annualised, > 0)\n"
            "    T     : time to expiry in years (> 0)\n"
            "\n"
            "    Steps:\n"
            "      d1 = (ln(S/K) + (r + sigma**2 / 2) * T) / (sigma * sqrt(T))\n"
            "      d2 = d1 - sigma * sqrt(T)\n"
            "      C  = S * N(d1) - K * exp(-r * T) * N(d2)\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement bs_call\")\n"
        ),
        reference_solution=(
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def bs_call(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))\n"
            "    d2 = d1 - sigma * math.sqrt(T)\n"
            "    return float(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2))\n"
        ),
        tests_py=(
            "\"\"\"Black-Scholes call pricer correctness.\"\"\"\n"
            "import math\n"
            "import pytest\n"
            "\n"
            "from solution import bs_call\n"
            "\n"
            "\n"
            "def test_hull_canonical_example():\n"
            "    # S=K=100, r=5%, σ=20%, T=1y. Hull p.299: C ≈ 10.4506.\n"
            "    c = bs_call(100, 100, 0.05, 0.20, 1.0)\n"
            "    assert abs(c - 10.4506) < 1e-3\n"
            "\n"
            "\n"
            "def test_deep_itm_call_approaches_S_minus_PV_K():\n"
            "    # S=200, K=100, very ITM. C → S - K*exp(-rT) = 200 - 100*exp(-0.05) ≈ 104.88.\n"
            "    c = bs_call(200, 100, 0.05, 0.20, 1.0)\n"
            "    expected = 200 - 100 * math.exp(-0.05)\n"
            "    assert abs(c - expected) < 0.05\n"
            "\n"
            "\n"
            "def test_deep_otm_call_is_near_zero():\n"
            "    c = bs_call(50, 150, 0.05, 0.20, 1.0)\n"
            "    assert 0 <= c < 0.05\n"
            "\n"
            "\n"
            "def test_monotone_increasing_in_spot():\n"
            "    # Higher spot → higher call price, all else equal.\n"
            "    a = bs_call(95, 100, 0.05, 0.20, 1.0)\n"
            "    b = bs_call(100, 100, 0.05, 0.20, 1.0)\n"
            "    c = bs_call(110, 100, 0.05, 0.20, 1.0)\n"
            "    assert a < b < c\n"
            "\n"
            "\n"
            "def test_monotone_increasing_in_sigma():\n"
            "    # Higher vol → higher call price, all else equal.\n"
            "    low_vol = bs_call(100, 100, 0.05, 0.10, 1.0)\n"
            "    high_vol = bs_call(100, 100, 0.05, 0.40, 1.0)\n"
            "    assert low_vol < high_vol\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_hull_canonical_example",
                "Hull's textbook example (S=K=100, r=5%, σ=20%, T=1y) → C ≈ 10.4506.",
            ),
            (
                "tests/test_solution.py::test_deep_itm_call_approaches_S_minus_PV_K",
                "Deep-ITM call price approaches the intrinsic minus the strike's PV.",
            ),
            (
                "tests/test_solution.py::test_deep_otm_call_is_near_zero",
                "Deep-OTM call (S=50, K=150) is essentially zero.",
            ),
            (
                "tests/test_solution.py::test_monotone_increasing_in_spot",
                "Call price is monotonically increasing in spot.",
            ),
            (
                "tests/test_solution.py::test_monotone_increasing_in_sigma",
                "Call price is monotonically increasing in volatility (positive vega).",
            ),
        ],
        your_turn="Implement `bs_call`. The docstring has the three lines you need. The Hull example (S=K=100, r=5%, σ=20%, T=1y) → 10.4506 is your first sanity check.",
        hint="`math.log`, `math.sqrt`, `math.exp`, `norm.cdf`. Five lines total.",
        why_this="Closed-form is the calibration anchor; every other pricer (binomial, MC, PDE) has to agree with it on the European-vanilla case before you trust it on anything harder.",
        skills=["quant", "options", "black-scholes"],
    ),
    # ---- BS deep-dive sub-arc (Phase BB.1) ----
    # quant-28a: build intuition via driven inputs (read the code, predict
    # which way the price moves under a parameter bump). Format A.
    # quant-28b: compute Greeks numerically and compare to closed-form.
    # quant-28c: simulate a daily delta-hedge and inspect residual P&L.
    Lesson(
        n=52, stage=3, mode="predict",
        n_label="28a",
        order_index_override=2810,
        title="Black-Scholes intuition",
        scenario="The closed-form is in your hands from the previous lesson. Before solving for prices on a new structure, the desk's intuition check is to bump one input at a time and see which way the price moves. This is how vol traders calibrate their gut.",
        learner_goal="Read a working bs_call, then predict the direction the call price moves when volatility doubles.",
        concept="A European call is *long* volatility: vega `∂C/∂σ` is strictly positive everywhere. Doubling σ from 0.20 to 0.40 widens the terminal log-normal distribution; the upside tail gets fatter, the downside loss is bounded at -premium, so the expected payoff under the risk-neutral measure goes up. Concretely for an ATM 1-year call with r=5%: the price lifts from ≈ 10.45 to ≈ 17.69 — about 70% more.",
        example_code=(
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "def bs_call(S, K, r, sigma, T):\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    d2 = d1 - sigma*math.sqrt(T)\n"
            "    return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)\n"
            "\n"
            "# Same ATM 1y call (r=5%) priced at two volatility regimes.\n"
            "low_vol  = bs_call(100, 100, 0.05, 0.20, 1.0)\n"
            "high_vol = bs_call(100, 100, 0.05, 0.40, 1.0)\n"
            "# Direction of the move when sigma doubles.\n"
            "print('up' if high_vol > low_vol else 'down' if high_vol < low_vol else 'same')"
        ),
        code=(
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "def bs_call(S, K, r, sigma, T):\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    d2 = d1 - sigma*math.sqrt(T)\n"
            "    return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)\n"
            "\n"
            "low_vol  = bs_call(100, 100, 0.05, 0.20, 1.0)\n"
            "high_vol = bs_call(100, 100, 0.05, 0.40, 1.0)\n"
            "print('up' if high_vol > low_vol else 'down' if high_vol < low_vol else 'same')"
        ),
        your_turn="Predict the direction of the call price as σ doubles.",
        expected_stdout="up",
        prompt="Predict the printed output.",
        why_this="Bump-one-input-at-a-time is how vol traders sanity-check a quote in seconds. If your model says doubling vol decreases a call's price, you know the sign of vega is wrong before you check a single test.",
        skills=["quant", "options", "black-scholes", "greeks"],
    ),
    Lesson(
        n=53, stage=3, mode="skeleton",
        n_label="28b",
        order_index_override=2820,
        title="Greeks by bumping",
        scenario="Most options books compute Greeks both ways: closed-form when one exists, numerical bumping as the universal fallback (and the cross-check that catches the sign errors closed-form sometimes hides). The bumping function below is the same one you'd run against a Monte Carlo pricer or a binomial tree.",
        learner_goal="Implement delta, gamma, and vega by central differences against the Black-Scholes pricer; match the closed-form Greeks at the Hull canonical numbers.",
        concept="Central differences turn any pricer into a Greek calculator. Delta is `(C(S+h) - C(S-h)) / (2h)`, gamma is the second difference `(C(S+h) - 2C(S) + C(S-h)) / h²`, vega is the σ-bump `(C(σ+h) - C(σ-h)) / (2h)`. Pick `h` small enough that the truncation error is below your tolerance, big enough that floating-point noise doesn't dominate: `h=0.01` for spot and `h=0.001` for σ are conservative defaults for double precision.",
        example_code="",
        editable_template=(
            "\"\"\"Greeks computed by central-difference bumping of bs_call.\"\"\"\n"
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def bs_call(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"Closed-form Black-Scholes European call (provided).\"\"\"\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    d2 = d1 - sigma*math.sqrt(T)\n"
            "    return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)\n"
            "\n"
            "\n"
            "def delta(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"∂C/∂S by central difference. Default bump h=0.01 on spot.\"\"\"\n"
            "    raise NotImplementedError(\"Implement delta\")\n"
            "\n"
            "\n"
            "def gamma(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"∂²C/∂S² by second-difference. Default bump h=0.01.\"\"\"\n"
            "    raise NotImplementedError(\"Implement gamma\")\n"
            "\n"
            "\n"
            "def vega(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"∂C/∂σ by central difference. Default bump h=0.001 on sigma.\n"
            "\n"
            "    Returned in price-per-unit-σ (i.e. dC for a +1.00 jump in σ);\n"
            "    divide by 100 if you want per-vol-point.\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement vega\")\n"
        ),
        reference_solution=(
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def bs_call(S, K, r, sigma, T):\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    d2 = d1 - sigma*math.sqrt(T)\n"
            "    return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)\n"
            "\n"
            "\n"
            "def delta(S, K, r, sigma, T, h=0.01):\n"
            "    return (bs_call(S+h, K, r, sigma, T) - bs_call(S-h, K, r, sigma, T)) / (2*h)\n"
            "\n"
            "\n"
            "def gamma(S, K, r, sigma, T, h=0.01):\n"
            "    return (\n"
            "        bs_call(S+h, K, r, sigma, T)\n"
            "        - 2*bs_call(S, K, r, sigma, T)\n"
            "        + bs_call(S-h, K, r, sigma, T)\n"
            "    ) / (h*h)\n"
            "\n"
            "\n"
            "def vega(S, K, r, sigma, T, h=0.001):\n"
            "    return (bs_call(S, K, r, sigma+h, T) - bs_call(S, K, r, sigma-h, T)) / (2*h)\n"
        ),
        tests_py=(
            "\"\"\"Numerical Greeks vs the Hull canonical (S=K=100, r=5%, σ=20%, T=1y).\n"
            "\n"
            "Closed-form references:\n"
            "  delta ≈ 0.63683\n"
            "  gamma ≈ 0.01876\n"
            "  vega  ≈ 37.524  (per 1.00 jump in σ)\n"
            "\"\"\"\n"
            "import pytest\n"
            "\n"
            "from solution import delta, gamma, vega\n"
            "\n"
            "\n"
            "def test_delta_matches_closed_form_at_hull_atm():\n"
            "    assert abs(delta(100, 100, 0.05, 0.20, 1.0) - 0.63683) < 1e-3\n"
            "\n"
            "\n"
            "def test_gamma_matches_closed_form_at_hull_atm():\n"
            "    assert abs(gamma(100, 100, 0.05, 0.20, 1.0) - 0.01876) < 1e-3\n"
            "\n"
            "\n"
            "def test_vega_matches_closed_form_at_hull_atm():\n"
            "    assert abs(vega(100, 100, 0.05, 0.20, 1.0) - 37.524) < 1e-1\n"
            "\n"
            "\n"
            "def test_delta_deep_itm_approaches_one():\n"
            "    assert delta(200, 100, 0.05, 0.20, 1.0) > 0.99\n"
            "\n"
            "\n"
            "def test_delta_deep_otm_approaches_zero():\n"
            "    assert delta(50, 150, 0.05, 0.20, 1.0) < 0.05\n"
            "\n"
            "\n"
            "def test_gamma_is_positive_for_a_long_call():\n"
            "    # Gamma is the convexity — always non-negative for a long option.\n"
            "    assert gamma(100, 100, 0.05, 0.20, 1.0) > 0\n"
            "\n"
            "\n"
            "def test_vega_is_positive_for_a_long_call():\n"
            "    # Calls are long vol — vega strictly positive on the interior.\n"
            "    assert vega(100, 100, 0.05, 0.20, 1.0) > 0\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_delta_matches_closed_form_at_hull_atm",
                "delta at Hull ATM matches closed-form (0.63683) within 1e-3.",
            ),
            (
                "tests/test_solution.py::test_gamma_matches_closed_form_at_hull_atm",
                "gamma at Hull ATM matches closed-form (0.01876) within 1e-3.",
            ),
            (
                "tests/test_solution.py::test_vega_matches_closed_form_at_hull_atm",
                "vega at Hull ATM matches closed-form (37.524) within 0.1.",
            ),
            (
                "tests/test_solution.py::test_delta_deep_itm_approaches_one",
                "delta of a deep-ITM call (S=200, K=100) is > 0.99.",
            ),
            (
                "tests/test_solution.py::test_delta_deep_otm_approaches_zero",
                "delta of a deep-OTM call (S=50, K=150) is < 0.05.",
            ),
            (
                "tests/test_solution.py::test_gamma_is_positive_for_a_long_call",
                "gamma is positive — convexity of a long option.",
            ),
            (
                "tests/test_solution.py::test_vega_is_positive_for_a_long_call",
                "vega is positive — calls and puts are long vol.",
            ),
        ],
        your_turn="Implement the three Greeks via central differences against the provided bs_call. The default bump sizes in the signatures are tuned to give 3-decimal accuracy at Hull's canonical example.",
        hint="Central diff: `(f(x+h) - f(x-h)) / (2h)`. Gamma is the second difference around S; vega is the first difference around σ.",
        why_this="Numerical bumping is the universal Greek calculator — it works against any pricer, even MC and trees that have no closed form. Most production options books compute both and alert when they diverge by more than rounding.",
        skills=["quant", "options", "black-scholes", "greeks"],
    ),
    Lesson(
        n=54, stage=3, mode="skeleton",
        n_label="28c",
        order_index_override=2830,
        title="Delta-hedge simulation",
        scenario="Selling an option without hedging is a punt on spot direction. Selling it and dynamically rebalancing delta shares against it isolates the *volatility* P&L — the actual exposure an options desk wants. The hedge loop you write here is the same one a market-maker runs after every fill.",
        learner_goal="Implement a daily-rebalance delta hedge of a short European call over a price path; final P&L should be small in magnitude (discretisation error only).",
        concept="At each rebalance step: (a) carry the cash book at the risk-free rate over `dt`, (b) mark the existing share position to the new spot, (c) recompute the target hedge `Δ` at the new (S, T-t), (d) buy/sell the difference at the new spot, paying/receiving in cash. The replicating portfolio is `(-1 call, +Δ shares)`. If the BS model is correct, the P&L on a continuous hedge is identically zero; discrete rebalance leaves a small residual proportional to `Γ · (ΔS)² · dt` — the gamma slippage every options book budgets for.",
        example_code="",
        editable_template=(
            "\"\"\"Daily delta-hedge of a short European call over a price path.\"\"\"\n"
            "import math\n"
            "from typing import Sequence\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def bs_call(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"Closed-form Black-Scholes European call price (provided).\"\"\"\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    d2 = d1 - sigma*math.sqrt(T)\n"
            "    return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)\n"
            "\n"
            "\n"
            "def bs_delta(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"Closed-form BS delta of a European call (provided).\"\"\"\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    return float(norm.cdf(d1))\n"
            "\n"
            "\n"
            "def hedge_pnl(\n"
            "    path: Sequence[float],\n"
            "    K: float,\n"
            "    r: float,\n"
            "    sigma: float,\n"
            "    T: float,\n"
            ") -> float:\n"
            "    \"\"\"Simulate selling one call at t=0 and dynamically delta-hedging\n"
            "    over the price path. Return the final cash P&L.\n"
            "\n"
            "    Parameters\n"
            "    ----------\n"
            "    path : daily prices, length n+1, with path[0] = S0 and path[-1] = S_T.\n"
            "    K, r, sigma, T : option parameters at t=0.\n"
            "\n"
            "    Steps:\n"
            "      1. At t=0: receive premium = bs_call(S0, K, r, sigma, T) into cash;\n"
            "         buy delta = bs_delta(S0, K, r, sigma, T) shares, paying delta*S0.\n"
            "      2. For each step i = 1..n:\n"
            "         - dt = T / n (constant step size).\n"
            "         - Carry cash forward: cash *= exp(r * dt).\n"
            "         - Compute remaining time to expiry: tau = T - i*dt.\n"
            "         - If tau > 0: recompute new_delta at (path[i], tau). Buy/sell\n"
            "           (new_delta - delta) shares at path[i]; pay diff*path[i] cash.\n"
            "      3. At expiry: short-call payout = max(path[-1] - K, 0); the shares\n"
            "         are worth delta * path[-1]. Final P&L = cash + delta*path[-1]\n"
            "         - max(path[-1] - K, 0).\n"
            "\n"
            "    Returns\n"
            "    -------\n"
            "    float — residual P&L. With a correct hedge, |P&L| << premium.\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement hedge_pnl\")\n"
        ),
        reference_solution=(
            "import math\n"
            "from typing import Sequence\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def bs_call(S, K, r, sigma, T):\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    d2 = d1 - sigma*math.sqrt(T)\n"
            "    return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)\n"
            "\n"
            "\n"
            "def bs_delta(S, K, r, sigma, T):\n"
            "    d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "    return float(norm.cdf(d1))\n"
            "\n"
            "\n"
            "def hedge_pnl(path, K, r, sigma, T):\n"
            "    n = len(path) - 1\n"
            "    dt = T / n\n"
            "    S = path[0]\n"
            "    cash = bs_call(S, K, r, sigma, T)\n"
            "    delta_shares = bs_delta(S, K, r, sigma, T)\n"
            "    cash -= delta_shares * S\n"
            "    for i in range(1, n + 1):\n"
            "        cash *= math.exp(r * dt)\n"
            "        S_new = path[i]\n"
            "        tau = T - i * dt\n"
            "        if tau > 1e-9:\n"
            "            new_delta = bs_delta(S_new, K, r, sigma, tau)\n"
            "            cash -= (new_delta - delta_shares) * S_new\n"
            "            delta_shares = new_delta\n"
            "        S = S_new\n"
            "    payout = max(path[-1] - K, 0)\n"
            "    return float(cash + delta_shares * path[-1] - payout)\n"
        ),
        tests_py=(
            "\"\"\"hedge_pnl: daily-rebalance delta hedge of a short European call.\n"
            "\n"
            "Tests check the residual P&L is small on deterministic GBM paths\n"
            "(seed-controlled). A correct hedge leaves ~1% of premium as gamma\n"
            "slippage; the threshold here is loose to account for the fixed seed.\n"
            "\"\"\"\n"
            "import math\n"
            "import numpy as np\n"
            "import pytest\n"
            "\n"
            "from solution import bs_call, hedge_pnl\n"
            "\n"
            "\n"
            "def _gbm_path(seed: int, S0=100.0, mu=0.05, sigma=0.20, T=0.25, n=63):\n"
            "    \"\"\"Daily GBM path under the real-world measure (mu drift).\n"
            "    n = 63 steps ~ one quarter at daily granularity.\"\"\"\n"
            "    rng = np.random.default_rng(seed)\n"
            "    dt = T / n\n"
            "    Z = rng.standard_normal(n)\n"
            "    log_steps = (mu - sigma**2/2)*dt + sigma*math.sqrt(dt)*Z\n"
            "    path = np.empty(n + 1)\n"
            "    path[0] = S0\n"
            "    path[1:] = S0 * np.exp(np.cumsum(log_steps))\n"
            "    return path\n"
            "\n"
            "\n"
            "def test_pnl_is_finite():\n"
            "    path = _gbm_path(seed=0)\n"
            "    pnl = hedge_pnl(list(path), K=100.0, r=0.05, sigma=0.20, T=0.25)\n"
            "    assert math.isfinite(pnl)\n"
            "\n"
            "\n"
            "def test_pnl_magnitude_under_one_percent_premium():\n"
            "    # Premium of a 3-month ATM call with σ=20%, r=5% is ≈ 4.6.\n"
            "    # Daily rebalance should leave residual << premium.\n"
            "    premium = bs_call(100.0, 100.0, 0.05, 0.20, 0.25)\n"
            "    pnls = [\n"
            "        hedge_pnl(list(_gbm_path(seed)), 100.0, 0.05, 0.20, 0.25)\n"
            "        for seed in range(20)\n"
            "    ]\n"
            "    # Loose 30% threshold: gamma slippage on individual paths is bounded\n"
            "    # but not zero. Tightens with more steps.\n"
            "    assert max(abs(p) for p in pnls) < 0.30 * premium\n"
            "\n"
            "\n"
            "def test_unhedged_short_call_loses_when_itm():\n"
            "    # Sanity: if the function ignored hedging and just shorted the call,\n"
            "    # the P&L on a path where S_T >> K would be very negative.\n"
            "    # Conversely, a working hedge keeps the loss bounded.\n"
            "    path = list(_gbm_path(seed=42))\n"
            "    pnl = hedge_pnl(path, K=100.0, r=0.05, sigma=0.20, T=0.25)\n"
            "    # On any path, a properly hedged short call's loss is bounded by\n"
            "    # a few times the premium even if S_T finishes deep ITM.\n"
            "    assert pnl > -5.0\n"
            "\n"
            "\n"
            "def test_zero_volatility_path_makes_theta():\n"
            "    # On a constant-spot path the realised vol is zero but the\n"
            "    # option was priced at σ=20%. The short-call seller pockets\n"
            "    # theta (time-decay) and pays nothing back to gamma. P&L is\n"
            "    # positive, bounded by a couple of premiums.\n"
            "    n = 63\n"
            "    path = [100.0] * (n + 1)\n"
            "    pnl = hedge_pnl(path, K=100.0, r=0.05, sigma=0.20, T=0.25)\n"
            "    premium = bs_call(100.0, 100.0, 0.05, 0.20, 0.25)\n"
            "    assert 0 < pnl < 2 * premium\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_pnl_is_finite",
                "P&L is a finite real number on a basic GBM path.",
            ),
            (
                "tests/test_solution.py::test_pnl_magnitude_under_one_percent_premium",
                "Across 20 random GBM paths, |P&L| stays below 30% of the premium.",
            ),
            (
                "tests/test_solution.py::test_unhedged_short_call_loses_when_itm",
                "On a deep-ITM path, the hedged P&L is bounded above -5 (not unbounded).",
            ),
            (
                "tests/test_solution.py::test_zero_volatility_path_makes_theta",
                "On a constant-spot path, the trader pockets theta — P&L is positive (0 < pnl < 2×premium).",
            ),
        ],
        your_turn="Implement `hedge_pnl`. The docstring spells out the three steps: receive premium + buy delta shares; per step, carry cash + rebalance to new delta at tau remaining; at expiry, deliver and unwind. The clean version is ~15 lines.",
        hint="The cash account moves three ways per step: (1) interest carry `cash *= exp(r*dt)`, (2) rebalance cost `cash -= (new_delta - old_delta) * S_new`, (3) at expiry, pay `max(S_T - K, 0)` to the call buyer.",
        why_this="This loop is the heartbeat of an options market-maker's hedge book. Get it right and you isolate realised vs implied vol P&L — the actual edge an options trader is trying to capture.",
        skills=["quant", "options", "black-scholes", "greeks"],
    ),
    Lesson(
        n=58, stage=3, mode="skeleton",
        n_label="28d",
        order_index_override=2840,
        title="Design a pricer API",
        scenario="So far each pricer (BS call, BS put, binomial American put) has been its own function. In a real options system you want one *interface* the strategy code talks to — call it with three arguments, get a price back, no matter what's behind it (closed-form, tree, MC). This lesson asks you to design that interface and implement it. The signatures are yours to pick.",
        learner_goal="Design and implement an `OptionPricer` class exposing european_call, european_put, and american_put with the same calling convention; pass tests that check Hull-canonical prices and the American >= European put inequality.",
        concept="Designing an API is half the engineering work — once you've picked argument order, return shape, and method names, the *implementation* is largely mechanical. The tests below specify the *behaviour* (canonical price within tolerance; American put >= European put) but not the internal structure: you can split helpers however you want, use closed-form vs trees, even take parameters via dataclass vs scalars. Multiple correct designs will pass.",
        example_code="",
        editable_template=(
            "\"\"\"Option pricer interface — you design the implementation.\n"
            "\n"
            "Specification:\n"
            "    Create a class `OptionPricer` that prices three options with the\n"
            "    same calling convention. The methods, helpers, and internal\n"
            "    structure are yours to design — the tests check behaviour, not\n"
            "    signatures. The required calls are:\n"
            "\n"
            "        OptionPricer().european_call(S, K, r, sigma, T) -> float\n"
            "        OptionPricer().european_put(S, K, r, sigma, T) -> float\n"
            "        OptionPricer().american_put(S, K, r, sigma, T, N=200) -> float\n"
            "\n"
            "    European call/put: closed-form Black-Scholes within 1e-3 of the\n"
            "    Hull canonical (S=K=100, r=0.05, σ=0.20, T=1y) → call ≈ 10.4506,\n"
            "    put ≈ 5.5735.\n"
            "    American put: N-step CRR binomial with early-exercise check.\n"
            "    Must be ≥ the European put on every input.\n"
            "\"\"\"\n"
            "\n"
            "\n"
            "class OptionPricer:\n"
            "    def european_call(self, S, K, r, sigma, T):\n"
            "        raise NotImplementedError(\"Implement european_call\")\n"
            "\n"
            "    def european_put(self, S, K, r, sigma, T):\n"
            "        raise NotImplementedError(\"Implement european_put\")\n"
            "\n"
            "    def american_put(self, S, K, r, sigma, T, N=200):\n"
            "        raise NotImplementedError(\"Implement american_put\")\n"
        ),
        reference_solution=(
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "class OptionPricer:\n"
            "    def european_call(self, S, K, r, sigma, T):\n"
            "        d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "        d2 = d1 - sigma*math.sqrt(T)\n"
            "        return S*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)\n"
            "\n"
            "    def european_put(self, S, K, r, sigma, T):\n"
            "        d1 = (math.log(S/K) + (r + sigma**2/2)*T) / (sigma*math.sqrt(T))\n"
            "        d2 = d1 - sigma*math.sqrt(T)\n"
            "        return K*math.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)\n"
            "\n"
            "    def american_put(self, S, K, r, sigma, T, N=200):\n"
            "        dt = T / N\n"
            "        u = math.exp(sigma * math.sqrt(dt))\n"
            "        d = 1 / u\n"
            "        q = (math.exp(r * dt) - d) / (u - d)\n"
            "        values = [\n"
            "            max(K - S * (u ** (N - i)) * (d ** i), 0)\n"
            "            for i in range(N + 1)\n"
            "        ]\n"
            "        for step in range(N - 1, -1, -1):\n"
            "            new_vals = []\n"
            "            for i in range(step + 1):\n"
            "                hold = math.exp(-r * dt) * (q * values[i] + (1 - q) * values[i + 1])\n"
            "                spot = S * (u ** (step - i)) * (d ** i)\n"
            "                exercise = max(K - spot, 0)\n"
            "                new_vals.append(max(hold, exercise))\n"
            "            values = new_vals\n"
            "        return float(values[0])\n"
        ),
        tests_py=(
            "\"\"\"OptionPricer: behavioural checks; multiple internal designs may pass.\"\"\"\n"
            "import inspect\n"
            "import pytest\n"
            "\n"
            "from solution import OptionPricer\n"
            "\n"
            "\n"
            "def test_class_exists():\n"
            "    assert inspect.isclass(OptionPricer)\n"
            "\n"
            "\n"
            "def test_european_call_matches_hull_canonical():\n"
            "    p = OptionPricer()\n"
            "    assert abs(p.european_call(100, 100, 0.05, 0.20, 1.0) - 10.4506) < 1e-3\n"
            "\n"
            "\n"
            "def test_european_put_matches_hull_canonical():\n"
            "    p = OptionPricer()\n"
            "    # Hull example: put ≈ 5.5735 via parity from call ≈ 10.4506.\n"
            "    assert abs(p.european_put(100, 100, 0.05, 0.20, 1.0) - 5.5735) < 1e-3\n"
            "\n"
            "\n"
            "def test_american_put_close_to_european_at_money():\n"
            "    p = OptionPricer()\n"
            "    eu = p.european_put(100, 100, 0.05, 0.20, 1.0)\n"
            "    am = p.american_put(100, 100, 0.05, 0.20, 1.0, N=400)\n"
            "    # Hull ATM early-exercise premium is ~0.5; allow up to 1.0\n"
            "    # for small N or alternative discretisations.\n"
            "    assert 0 <= (am - eu) < 1.0\n"
            "\n"
            "\n"
            "def test_american_put_dominates_european_on_ditm():\n"
            "    p = OptionPricer()\n"
            "    # Deep ITM put: early exercise is valuable, American premium is real.\n"
            "    eu = p.european_put(60, 100, 0.05, 0.20, 1.0)\n"
            "    am = p.american_put(60, 100, 0.05, 0.20, 1.0, N=400)\n"
            "    assert am >= eu\n"
            "    # Hull canonical: at S=60 K=100 the American put exceeds the European\n"
            "    # by a clear margin (early exercise valuable).\n"
            "    assert am - eu > 0.5\n"
            "\n"
            "\n"
            "def test_european_call_monotone_in_spot():\n"
            "    p = OptionPricer()\n"
            "    a = p.european_call(95, 100, 0.05, 0.20, 1.0)\n"
            "    b = p.european_call(100, 100, 0.05, 0.20, 1.0)\n"
            "    c = p.european_call(110, 100, 0.05, 0.20, 1.0)\n"
            "    assert a < b < c\n"
            "\n"
            "\n"
            "def test_european_put_monotone_in_strike():\n"
            "    p = OptionPricer()\n"
            "    a = p.european_put(100, 90, 0.05, 0.20, 1.0)\n"
            "    b = p.european_put(100, 100, 0.05, 0.20, 1.0)\n"
            "    c = p.european_put(100, 110, 0.05, 0.20, 1.0)\n"
            "    assert a < b < c\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_class_exists",
                "OptionPricer is a class (any internal design is fine).",
            ),
            (
                "tests/test_solution.py::test_european_call_matches_hull_canonical",
                "ATM european_call matches Hull canonical 10.4506 within 1e-3.",
            ),
            (
                "tests/test_solution.py::test_european_put_matches_hull_canonical",
                "ATM european_put matches Hull canonical 5.5735 within 1e-3.",
            ),
            (
                "tests/test_solution.py::test_american_put_close_to_european_at_money",
                "ATM american_put exceeds european_put by < 0.5 (small early-exercise premium).",
            ),
            (
                "tests/test_solution.py::test_american_put_dominates_european_on_ditm",
                "Deep-ITM american_put exceeds european_put by > 0.5 (early-exercise valuable).",
            ),
            (
                "tests/test_solution.py::test_european_call_monotone_in_spot",
                "european_call is monotonically increasing in spot.",
            ),
            (
                "tests/test_solution.py::test_european_put_monotone_in_strike",
                "european_put is monotonically increasing in strike.",
            ),
        ],
        your_turn="Design and implement OptionPricer. The tests check behaviour at canonical points and a few monotonicity invariants — multiple valid designs pass. Reuse the bs_call body from lesson 28 and the binomial backward-induction from lesson 30 if you want.",
        hint="Three method bodies. European call/put → closed-form Black-Scholes. American put → N-step CRR with `max(hold, exercise)` at each step. ~25 lines total.",
        why_this="Designing an interface (then implementing it) is the engineering muscle that lets you swap closed-form for tree for MC without touching strategy code. Real options libraries (QuantLib, py_vollib) do exactly this with a `Pricer` abstraction.",
        skills=["quant", "options", "black-scholes"],
    ),
    Lesson(
        n=29, stage=3, mode="debug",
        title="Greeks: delta of a call",
        scenario="The vol-trading desk runs `compute_delta` against every open option position thousands of times a second to keep the book delta-neutral. The junior ships an implementation, the smoke test passes (ATM call delta in the right ballpark), but the senior risk auditor reviewing the PR notices the d1 formula uses `(r − σ²/2)` instead of `(r + σ²/2)`. Subtle, but it gives systematically wrong deltas — and the desk's hedges drift. Find and fix the sign.",
        learner_goal="Spot the sign error in the d1 numerator and correct it.",
        concept="d1 in the Black-Scholes formula is `(ln(S/K) + (r + σ²/2)·T) / (σ·√T)`. The `+ σ²/2` is sometimes called the *convexity correction* on the log-normal drift — confusing it with `− σ²/2` is THE common slip when you're writing BS from memory. The two terms appear in the same paper but on different lines: the `r + σ²/2` in d1, the `r − σ²/2` in the GBM exponent. Mix them up and call deltas are silently a few percent off — exactly the kind of bug a delta-hedging book is sensitive to.",
        example_code="",
        editable_template=(
            "\"\"\"Black-Scholes delta for a European call.\"\"\"\n"
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def compute_delta(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    \"\"\"Return the Black-Scholes delta of a European call: Δ = N(d1).\n"
            "\n"
            "    d1 = (ln(S/K) + (r + σ²/2)·T) / (σ·√T)\n"
            "    \"\"\"\n"
            "    d1 = (math.log(S / K) + (r - sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))\n"
            "    return float(norm.cdf(d1))\n"
        ),
        reference_solution=(
            "import math\n"
            "from scipy.stats import norm\n"
            "\n"
            "\n"
            "def compute_delta(S: float, K: float, r: float, sigma: float, T: float) -> float:\n"
            "    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))\n"
            "    return float(norm.cdf(d1))\n"
        ),
        tests_py=(
            "\"\"\"Call-delta correctness against the Hull canonical numbers.\"\"\"\n"
            "import pytest\n"
            "\n"
            "from solution import compute_delta\n"
            "\n"
            "\n"
            "def test_atm_call_delta_is_above_half_from_drift():\n"
            "    # ATM call with r=5%, σ=20%, T=1y → delta ≈ 0.6368.\n"
            "    # With the bug (- σ²/2), the answer is ≈ 0.5793 — clearly below.\n"
            "    d = compute_delta(100, 100, 0.05, 0.20, 1.0)\n"
            "    assert abs(d - 0.6368) < 1e-3\n"
            "\n"
            "\n"
            "def test_deep_itm_call_delta_approaches_one():\n"
            "    # Deep ITM call (S=200, K=100) → delta very close to 1.\n"
            "    d = compute_delta(200, 100, 0.05, 0.20, 1.0)\n"
            "    assert d > 0.99\n"
            "\n"
            "\n"
            "def test_deep_otm_call_delta_approaches_zero():\n"
            "    d = compute_delta(50, 150, 0.05, 0.20, 1.0)\n"
            "    assert d < 0.05\n"
            "\n"
            "\n"
            "def test_monotone_increasing_in_spot():\n"
            "    a = compute_delta(95, 100, 0.05, 0.20, 1.0)\n"
            "    b = compute_delta(100, 100, 0.05, 0.20, 1.0)\n"
            "    c = compute_delta(110, 100, 0.05, 0.20, 1.0)\n"
            "    assert a < b < c\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_atm_call_delta_is_above_half_from_drift",
                "ATM call with r=5%/σ=20%/T=1y → delta ≈ 0.6368 (the bug gives ~0.58).",
            ),
            (
                "tests/test_solution.py::test_deep_itm_call_delta_approaches_one",
                "Deep-ITM call (S=200, K=100) → delta > 0.99.",
            ),
            (
                "tests/test_solution.py::test_deep_otm_call_delta_approaches_zero",
                "Deep-OTM call (S=50, K=150) → delta < 0.05.",
            ),
            (
                "tests/test_solution.py::test_monotone_increasing_in_spot",
                "Call delta is monotonically increasing in spot.",
            ),
        ],
        your_turn="The first test is the giveaway: ATM call delta should be ≈ 0.6368 with the given parameters, but the function returns ~0.58. The d1 numerator has the wrong sign on the σ²/2 term.",
        hint="d1's numerator carries `(r + σ²/2)·T`, not `(r − σ²/2)·T`. One character.",
        why_this="Delta is how much spot exposure an option gives you. Hedge it daily and you isolate the vol P&L — the thing an options book is actually trying to harvest.",
        skills=["quant", "options", "greeks"],
    ),
    Lesson(
        n=30, stage=3, mode="skeleton",
        title="Binomial tree pricer",
        scenario="Before Black-Scholes' PDE became the standard solver in vol-desk software, the CRR (Cox-Ross-Rubinstein) tree was *the* pricing algorithm. It still is for American options — early exercise needs a backward induction that the closed-form BS can't do. Every options engineer can sketch the recurrence on a whiteboard; today you write it as code.",
        learner_goal="Implement `crr_call(S, K, r, sigma, T, N)` — an N-step CRR binomial tree pricer for a European call.",
        concept="Set `dt = T / N`, `u = exp(σ·√dt)`, `d = 1/u` (multiplicatively symmetric). Risk-neutral up-probability `p = (exp(r·dt) − d) / (u − d)`. Terminal prices at expiry: `S · u^i · d^(N−i)` for `i = 0..N`. Terminal call payoffs: `max(S_T − K, 0)`. Backward-induct: at each step, `vals_new = exp(−r·dt) · (p·vals[1:] + (1−p)·vals[:-1])`. After N iterations, `vals[0]` is the price at t=0. As N → ∞ the price converges monotonically to BS.",
        example_code="",
        editable_template=(
            "\"\"\"CRR (Cox-Ross-Rubinstein) binomial-tree European call pricer.\"\"\"\n"
            "import numpy as np\n"
            "\n"
            "\n"
            "def crr_call(S: float, K: float, r: float, sigma: float, T: float, N: int) -> float:\n"
            "    \"\"\"N-step CRR binomial price of a European call.\n"
            "\n"
            "    Steps:\n"
            "      dt = T / N\n"
            "      u  = exp(sigma * sqrt(dt));  d = 1 / u\n"
            "      p  = (exp(r * dt) - d) / (u - d)\n"
            "      Terminal prices: S * u**i * d**(N - i) for i in 0..N\n"
            "      Terminal payoffs: max(S_T - K, 0)\n"
            "      Backward induction N times:\n"
            "        vals = exp(-r * dt) * (p * vals[1:] + (1 - p) * vals[:-1])\n"
            "      Return vals[0].\n"
            "\n"
            "    Vectorised numpy is fine. A loop over N is fine — at N=50 it's microseconds.\n"
            "    \"\"\"\n"
            "    raise NotImplementedError(\"Implement crr_call\")\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "\n"
            "\n"
            "def crr_call(S: float, K: float, r: float, sigma: float, T: float, N: int) -> float:\n"
            "    dt = T / N\n"
            "    u = np.exp(sigma * np.sqrt(dt))\n"
            "    d = 1 / u\n"
            "    p = (np.exp(r * dt) - d) / (u - d)\n"
            "    ST = S * u ** np.arange(N + 1) * d ** (N - np.arange(N + 1))\n"
            "    vals = np.maximum(ST - K, 0)\n"
            "    for _ in range(N):\n"
            "        vals = np.exp(-r * dt) * (p * vals[1:] + (1 - p) * vals[:-1])\n"
            "    return float(vals[0])\n"
        ),
        tests_py=(
            "\"\"\"CRR binomial pricer correctness + convergence-to-BS.\"\"\"\n"
            "import math\n"
            "import pytest\n"
            "\n"
            "from solution import crr_call\n"
            "\n"
            "\n"
            "HULL = dict(S=100, K=100, r=0.05, sigma=0.20, T=1.0)\n"
            "BS_CALL = 10.4506  # closed-form BS on Hull's example\n"
            "\n"
            "\n"
            "def test_n50_within_0_05_of_BS():\n"
            "    c = crr_call(**HULL, N=50)\n"
            "    assert abs(c - BS_CALL) < 0.05\n"
            "\n"
            "\n"
            "def test_n500_within_0_01_of_BS():\n"
            "    c = crr_call(**HULL, N=500)\n"
            "    assert abs(c - BS_CALL) < 0.01\n"
            "\n"
            "\n"
            "def test_500_step_is_closer_than_50_step():\n"
            "    # CRR converges as N grows — not always monotone, but 500 should\n"
            "    # always be at least as close as 50.\n"
            "    c50 = crr_call(**HULL, N=50)\n"
            "    c500 = crr_call(**HULL, N=500)\n"
            "    assert abs(c500 - BS_CALL) <= abs(c50 - BS_CALL) + 1e-6\n"
            "\n"
            "\n"
            "def test_deep_otm_call_is_near_zero():\n"
            "    c = crr_call(S=50, K=150, r=0.05, sigma=0.20, T=1.0, N=200)\n"
            "    assert 0 <= c < 0.05\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_n50_within_0_05_of_BS",
                "50-step tree within 0.05 of BS on Hull's example.",
            ),
            (
                "tests/test_solution.py::test_n500_within_0_01_of_BS",
                "500-step tree within 0.01 of BS — convergence with N.",
            ),
            (
                "tests/test_solution.py::test_500_step_is_closer_than_50_step",
                "More steps → closer to BS (convergence direction sanity).",
            ),
            (
                "tests/test_solution.py::test_deep_otm_call_is_near_zero",
                "Deep-OTM call (S=50, K=150) → tree price ≈ 0.",
            ),
        ],
        your_turn="Implement `crr_call`. The docstring spells out the six steps; the cleanest code is ~10 lines.",
        hint="`S * u ** np.arange(N + 1) * d ** (N - np.arange(N + 1))` gives the terminal price vector in one line.",
        why_this="American options need backward induction — Black-Scholes can't price early exercise. The same tree machinery prices warrants, convertibles, and most early-exercise structured products.",
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
        why_this="MC handles path-dependent payoffs (Asian, barrier, autocallable) that no closed-form touches. The cost is the convergence rate — you watch the running mean stabilise as N grows.",
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
        why_this="Every allocator quotes 'efficient frontier' even when they don't actually trade on it. Knowing the closed-form is how you tell when the pitch is hand-waving vs grounded.",
        skills=["quant", "portfolio", "linear-algebra"],
        datasets=["spy", "aapl", "tlt"],
    ),
    Lesson(
        n=33, stage=3, mode="debug",
        title="Sharpe, max drawdown",
        scenario="The strategy deck goes to the IC tomorrow. The junior writes `risk_metrics(returns)` and the numbers look fine to her — until the senior risk officer pastes a known-good return series through it and the Sharpe comes out √252 too large. Same bug ships every quarter across the industry: someone scales the mean by 252 but forgets to scale the std the right way. Find it.",
        learner_goal="Spot the annualisation slip on the Sharpe ratio and fix the std scaling.",
        concept="Annualised Sharpe for daily returns is `(mean × 252) / (std × √252)`. Equivalently: `(mean / std) × √252`. The intuition: returns sum *linearly* over time (so mean scales by 252 over a year), but std scales by `√n` (so daily std becomes annual std at `× √252`). Forgetting the √ on the denominator inflates Sharpe by `√252 ≈ 15.87` — turns a respectable 0.8 into a comically wrong 12.7. Max drawdown's `cummax / cummin` direction is also a common slip: peak-to-trough is `equity / equity.cummax() - 1`, then take the *min* (most negative). Mirror it (`.min()`/`.cummin()`) and you measure trough-to-peak which is always positive.",
        example_code="",
        editable_template=(
            "\"\"\"Annualised Sharpe ratio and max drawdown for daily returns.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "def risk_metrics(r: pd.Series) -> dict:\n"
            "    \"\"\"Return {sharpe, max_drawdown} for a daily-return series.\n"
            "\n"
            "    - sharpe       : annualised Sharpe = (mean*252) / (std*sqrt(252))\n"
            "    - max_drawdown : worst peak-to-trough loss as a negative fraction\n"
            "    \"\"\"\n"
            "    sharpe = (r.mean() * 252) / r.std()\n"
            "    eq = (1 + r).cumprod()\n"
            "    dd = (eq / eq.cummax() - 1).min()\n"
            "    return {\"sharpe\": float(sharpe), \"max_drawdown\": float(dd)}\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "def risk_metrics(r: pd.Series) -> dict:\n"
            "    sharpe = (r.mean() * 252) / (r.std() * np.sqrt(252))\n"
            "    eq = (1 + r).cumprod()\n"
            "    dd = (eq / eq.cummax() - 1).min()\n"
            "    return {\"sharpe\": float(sharpe), \"max_drawdown\": float(dd)}\n"
        ),
        tests_py=(
            "\"\"\"risk_metrics: Sharpe annualisation + drawdown direction.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import risk_metrics\n"
            "\n"
            "\n"
            "def test_sharpe_on_known_series():\n"
            "    # Constructed: mean = 0.001 daily, std = 0.012 daily.\n"
            "    # Expected annualised Sharpe = 0.001*252 / (0.012*sqrt(252))\n"
            "    #                            = 0.252 / 0.1904... ≈ 1.323.\n"
            "    rng = np.random.default_rng(0)\n"
            "    raw = rng.normal(0.001, 0.012, 10_000)\n"
            "    raw -= raw.mean() - 0.001\n"
            "    raw *= 0.012 / raw.std()\n"
            "    s = pd.Series(raw)\n"
            "    m = risk_metrics(s)\n"
            "    expected = (s.mean() * 252) / (s.std() * np.sqrt(252))\n"
            "    assert abs(m[\"sharpe\"] - expected) < 1e-9\n"
            "\n"
            "\n"
            "def test_sharpe_doesnt_blow_up_by_factor_of_sqrt_252():\n"
            "    # With the bug present, Sharpe is √252 (~15.87) too large.\n"
            "    # Reasonable strategies have Sharpe well under 5.\n"
            "    rng = np.random.default_rng(1)\n"
            "    s = pd.Series(rng.normal(0.0005, 0.012, 5000))\n"
            "    m = risk_metrics(s)\n"
            "    assert abs(m[\"sharpe\"]) < 5\n"
            "\n"
            "\n"
            "def test_max_drawdown_is_negative_on_lossy_series():\n"
            "    # 30%-drop pattern → drawdown ≈ -0.3.\n"
            "    s = pd.Series([0.0, -0.10, -0.10, -0.15])\n"
            "    m = risk_metrics(s)\n"
            "    assert m[\"max_drawdown\"] < -0.25\n"
            "\n"
            "\n"
            "def test_max_drawdown_zero_on_monotone_up():\n"
            "    s = pd.Series([0.01] * 100)\n"
            "    m = risk_metrics(s)\n"
            "    assert abs(m[\"max_drawdown\"]) < 1e-9\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_sharpe_on_known_series",
                "Sharpe matches the analytical formula (mean*252)/(std*√252) on a controlled series.",
            ),
            (
                "tests/test_solution.py::test_sharpe_doesnt_blow_up_by_factor_of_sqrt_252",
                "Sharpe on a 10k-sample noise series stays under 5 — catches the missing √252.",
            ),
            (
                "tests/test_solution.py::test_max_drawdown_is_negative_on_lossy_series",
                "Drawdown on a loss-heavy series is below -0.25 (sign + magnitude).",
            ),
            (
                "tests/test_solution.py::test_max_drawdown_zero_on_monotone_up",
                "Monotone-up returns have zero drawdown.",
            ),
        ],
        your_turn="The Sharpe value is √252 too large. The annualisation needs to scale BOTH the numerator (by 252) and the denominator (by √252).",
        hint="`r.std() * np.sqrt(252)`.",
        why_this="These are the two numbers fund-of-funds ask about before they read the IC ticket. Get the annualisation wrong and your IR-2 looks like an IR-30 — which gets you laughed out of the meeting, not funded.",
        skills=["quant", "pandas", "risk-metrics"],
    ),
    Lesson(
        n=59, stage=3, mode="skeleton",
        n_label="33a",
        order_index_override=3310,
        title="Design a Portfolio class",
        scenario="You've implemented sharpe(), max_drawdown(), and value-at-date as separate functions across a few lessons. Real strategy code packages them into one object — a `Portfolio` you construct once with weights + returns, then query for any metric. This lesson asks you to design that object. The interior is yours; the contract is below.",
        learner_goal="Design and implement a `Portfolio` class that takes weights and a returns DataFrame, and exposes sharpe(), max_drawdown(), and value_at_date(date).",
        concept="Same engineering muscle as the pricer lesson: pick names, return types, and method bodies that meet a behavioural spec. The implementation can pre-compute the portfolio return series once and cache it, or recompute on each call — either passes. The lesson is: 'API first, then implementation'. Real desk libraries (zipline, vectorbt, qstrader) all expose some flavour of this object.",
        example_code="",
        editable_template=(
            "\"\"\"Portfolio analytics class — you design the implementation.\n"
            "\n"
            "Specification:\n"
            "    Create a class `Portfolio` with this behaviour:\n"
            "\n"
            "    Constructor: Portfolio(weights, returns)\n"
            "      - weights: dict mapping asset name (str) → weight (float).\n"
            "                 Weights sum to 1.0 (no leverage; long-only or short).\n"
            "      - returns: pd.DataFrame indexed by date, columns are asset\n"
            "                 names matching the weights keys.\n"
            "\n"
            "    Methods:\n"
            "      - sharpe() -> float\n"
            "          Annualised Sharpe of the portfolio return series.\n"
            "          252 trading days/year. (mean*252) / (std*sqrt(252)).\n"
            "      - max_drawdown() -> float\n"
            "          Worst peak-to-trough loss as a NEGATIVE fraction.\n"
            "      - value_at_date(date) -> float\n"
            "          Portfolio NAV (starting at 1.0) compounded through `date`.\n"
            "\n"
            "Multiple valid designs pass — the tests check behaviour, not internals.\n"
            "\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "class Portfolio:\n"
            "    def __init__(self, weights: dict, returns: pd.DataFrame):\n"
            "        raise NotImplementedError(\"Design and implement Portfolio\")\n"
            "\n"
            "    def sharpe(self) -> float:\n"
            "        raise NotImplementedError(\"Implement sharpe\")\n"
            "\n"
            "    def max_drawdown(self) -> float:\n"
            "        raise NotImplementedError(\"Implement max_drawdown\")\n"
            "\n"
            "    def value_at_date(self, date) -> float:\n"
            "        raise NotImplementedError(\"Implement value_at_date\")\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "import pandas as pd\n"
            "\n"
            "\n"
            "class Portfolio:\n"
            "    def __init__(self, weights: dict, returns: pd.DataFrame):\n"
            "        self.weights = pd.Series(weights)\n"
            "        self.returns = returns\n"
            "        self._port_rets = (returns * self.weights).sum(axis=1)\n"
            "\n"
            "    def sharpe(self) -> float:\n"
            "        r = self._port_rets\n"
            "        if r.std() == 0:\n"
            "            return 0.0\n"
            "        return float((r.mean() * 252) / (r.std() * np.sqrt(252)))\n"
            "\n"
            "    def max_drawdown(self) -> float:\n"
            "        eq = (1 + self._port_rets).cumprod()\n"
            "        return float((eq / eq.cummax() - 1).min())\n"
            "\n"
            "    def value_at_date(self, date) -> float:\n"
            "        eq = (1 + self._port_rets).cumprod()\n"
            "        return float(eq.loc[date])\n"
        ),
        tests_py=(
            "\"\"\"Portfolio: behavioural checks; many valid internal designs.\"\"\"\n"
            "import inspect\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import Portfolio\n"
            "\n"
            "\n"
            "def _toy_returns():\n"
            "    rng = np.random.default_rng(0)\n"
            "    dates = pd.date_range('2024-01-01', periods=200, freq='D')\n"
            "    spy = rng.normal(0.0005, 0.012, 200)\n"
            "    aapl = rng.normal(0.0008, 0.015, 200)\n"
            "    return pd.DataFrame({'SPY': spy, 'AAPL': aapl}, index=dates)\n"
            "\n"
            "\n"
            "def test_class_exists():\n"
            "    assert inspect.isclass(Portfolio)\n"
            "\n"
            "\n"
            "def test_sharpe_returns_finite_float():\n"
            "    p = Portfolio({'SPY': 0.6, 'AAPL': 0.4}, _toy_returns())\n"
            "    s = p.sharpe()\n"
            "    assert isinstance(s, float) and np.isfinite(s)\n"
            "\n"
            "\n"
            "def test_sharpe_matches_hand_calc():\n"
            "    df = _toy_returns()\n"
            "    weights = {'SPY': 0.6, 'AAPL': 0.4}\n"
            "    p = Portfolio(weights, df)\n"
            "    port_rets = 0.6 * df['SPY'] + 0.4 * df['AAPL']\n"
            "    expected = (port_rets.mean() * 252) / (port_rets.std() * np.sqrt(252))\n"
            "    assert abs(p.sharpe() - expected) < 1e-6\n"
            "\n"
            "\n"
            "def test_max_drawdown_is_nonpositive_float():\n"
            "    p = Portfolio({'SPY': 1.0, 'AAPL': 0.0}, _toy_returns())\n"
            "    dd = p.max_drawdown()\n"
            "    assert isinstance(dd, float)\n"
            "    assert dd <= 0.0\n"
            "\n"
            "\n"
            "def test_max_drawdown_zero_on_monotone_up_series():\n"
            "    dates = pd.date_range('2024-01-01', periods=50, freq='D')\n"
            "    df = pd.DataFrame(\n"
            "        {'SPY': [0.01]*50, 'AAPL': [0.02]*50},\n"
            "        index=dates,\n"
            "    )\n"
            "    p = Portfolio({'SPY': 0.5, 'AAPL': 0.5}, df)\n"
            "    assert abs(p.max_drawdown()) < 1e-9\n"
            "\n"
            "\n"
            "def test_value_at_first_date():\n"
            "    df = _toy_returns()\n"
            "    p = Portfolio({'SPY': 0.5, 'AAPL': 0.5}, df)\n"
            "    v0 = p.value_at_date(df.index[0])\n"
            "    expected = 1.0 + 0.5 * df.iloc[0]['SPY'] + 0.5 * df.iloc[0]['AAPL']\n"
            "    assert abs(v0 - expected) < 1e-9\n"
            "\n"
            "\n"
            "def test_value_at_last_date_compounds():\n"
            "    df = _toy_returns()\n"
            "    p = Portfolio({'SPY': 0.5, 'AAPL': 0.5}, df)\n"
            "    v = p.value_at_date(df.index[-1])\n"
            "    port_rets = 0.5 * df['SPY'] + 0.5 * df['AAPL']\n"
            "    expected = float((1 + port_rets).prod())\n"
            "    assert abs(v - expected) < 1e-9\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_class_exists",
                "Portfolio is a class (internal design is your choice).",
            ),
            (
                "tests/test_solution.py::test_sharpe_returns_finite_float",
                "sharpe() returns a finite float on a typical 200-day series.",
            ),
            (
                "tests/test_solution.py::test_sharpe_matches_hand_calc",
                "sharpe() matches the analytical formula on a controlled portfolio.",
            ),
            (
                "tests/test_solution.py::test_max_drawdown_is_nonpositive_float",
                "max_drawdown() returns a float <= 0 (loss as a negative fraction).",
            ),
            (
                "tests/test_solution.py::test_max_drawdown_zero_on_monotone_up_series",
                "Monotone-up returns produce zero drawdown.",
            ),
            (
                "tests/test_solution.py::test_value_at_first_date",
                "value_at_date on day 0 equals 1 + first day's portfolio return.",
            ),
            (
                "tests/test_solution.py::test_value_at_last_date_compounds",
                "value_at_date on the last day equals the compounded NAV from day 0.",
            ),
        ],
        your_turn="Design and implement Portfolio. The constructor receives weights + returns; the three methods are sharpe, max_drawdown, value_at_date. Tests check behaviour at canonical points — many valid internal designs pass. Reuse the formulas from lesson 33.",
        hint="Compute the portfolio return series in the constructor (`(returns * weights).sum(axis=1)`); all three methods reduce to one-liners on that series.",
        why_this="The first thing real strategy code does after a backtest is package the result into one object the rest of the pipeline can query. Designing it well saves rewriting the same five method calls across every notebook.",
        skills=["quant", "pandas", "risk-metrics", "portfolio"],
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
        prompt="Predict the printed output.",
        skills=["quant", "machine-learning", "backtesting"],
    ),
    Lesson(
        n=36, stage=4, mode="debug",
        title="Momentum signal regression",
        scenario="Junior at a quant fund builds a momentum-feature linear model and reports a *suspiciously high* R² in the morning standup. The senior raises an eyebrow — daily-horizon momentum on a single index has R² close to zero in honest cross-validation. A code review turns up the bug in the feature construction: the supposed 'lagged 5-day momentum' is rolling over the same-day return, so the model can see the future. Find the missing `.shift(1)`.",
        learner_goal="Spot the look-ahead in the feature pipeline and add the missing lag.",
        concept="A predictive feature at time `t` must be computable from data up to and including `t-1`. The standard idiom in pandas: `r.shift(1).rolling(W).sum()` shifts first (drops today's return) then aggregates over the prior window. Skipping the shift means today's return is in the feature, the model trivially learns 'today's return predicts today's return', and R² inflates from ~0 to >0.1. This is the most-shipped bug in junior quant-ML code; explicit tests on a synthetic random-walk catch it instantly.",
        example_code="",
        editable_template=(
            "\"\"\"5-day momentum feature → next-day return regression.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import train_test_split\n"
            "\n"
            "\n"
            "def momentum_r2(returns: pd.Series) -> float:\n"
            "    \"\"\"Return the test-set R² of a single-feature model.\n"
            "\n"
            "    Feature: 5-day rolling sum of PRIOR returns (must lag by 1).\n"
            "    Target : next-day return.\n"
            "    Split  : chronological 80/20, no shuffle.\n"
            "    \"\"\"\n"
            "    # Bug: missing .shift(1) — the feature includes today's return.\n"
            "    df = pd.DataFrame({\n"
            "        'mom': returns.rolling(5).sum(),\n"
            "        'next': returns,\n"
            "    }).dropna()\n"
            "    X = df[['mom']].values\n"
            "    y = df['next'].values\n"
            "    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, shuffle=False)\n"
            "    return float(LinearRegression().fit(Xtr, ytr).score(Xte, yte))\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import train_test_split\n"
            "\n"
            "\n"
            "def momentum_r2(returns: pd.Series) -> float:\n"
            "    df = pd.DataFrame({\n"
            "        'mom': returns.shift(1).rolling(5).sum(),\n"
            "        'next': returns,\n"
            "    }).dropna()\n"
            "    X = df[['mom']].values\n"
            "    y = df['next'].values\n"
            "    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, shuffle=False)\n"
            "    return float(LinearRegression().fit(Xtr, ytr).score(Xte, yte))\n"
        ),
        tests_py=(
            "\"\"\"Momentum-R² leak detection on a random-walk null.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import momentum_r2\n"
            "\n"
            "\n"
            "def _white_noise(n: int = 2000, seed: int = 0) -> pd.Series:\n"
            "    rng = np.random.default_rng(seed)\n"
            "    return pd.Series(rng.normal(0, 0.01, n))\n"
            "\n"
            "\n"
            "def test_r2_near_zero_on_random_walk():\n"
            "    # If features are properly lagged, R² on pure noise is ~0.\n"
            "    # The leaky version returns R² > 0.1 — clearly distinguishable.\n"
            "    score = momentum_r2(_white_noise(seed=1))\n"
            "    assert abs(score) < 0.05\n"
            "\n"
            "\n"
            "def test_r2_not_inflated_by_same_day_leak():\n"
            "    # Run on three independent noise series; mean R² must stay near 0.\n"
            "    mean_score = np.mean([\n"
            "        momentum_r2(_white_noise(seed=k)) for k in range(3)\n"
            "    ])\n"
            "    assert abs(mean_score) < 0.05\n"
            "\n"
            "\n"
            "def test_returns_a_float():\n"
            "    out = momentum_r2(_white_noise())\n"
            "    assert isinstance(out, float)\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_r2_near_zero_on_random_walk",
                "On pure noise (no real signal), test R² stays near zero — catches the leak.",
            ),
            (
                "tests/test_solution.py::test_r2_not_inflated_by_same_day_leak",
                "Mean R² across 3 random-walk seeds is below 0.05.",
            ),
            (
                "tests/test_solution.py::test_returns_a_float",
                "Function returns a plain float (not a numpy scalar).",
            ),
        ],
        your_turn="The feature includes the current day's return — that's the leak. Add the single `.shift(1)` that lags the feature by one day before the rolling sum.",
        hint="`returns.shift(1).rolling(5).sum()` — shift first, then aggregate.",
        skills=["quant", "machine-learning", "regression", "backtesting"],
    ),
    Lesson(
        n=37, stage=4, mode="debug",
        title="Random forest direction classifier",
        scenario="A junior at a multi-strat shop trains a random forest on a two-feature direction classifier and reports 70% out-of-sample accuracy. The PM is sceptical — a real edge that strong would put the desk out of work. A code review finds the bug: `train_test_split` defaults to `shuffle=True`, so the test set is randomly drawn from across the full timeline. Future rows leak into the training fold. With chronological splitting the score collapses back to noise. Find the missing keyword.",
        learner_goal="Find the `train_test_split` call that's secretly shuffling the time series and pin it back to chronological order.",
        concept="`sklearn.model_selection.train_test_split(..., shuffle=True)` — the SILENT DEFAULT — randomly samples test rows from anywhere in the array. For tabular i.i.d. data that's correct. For time series it's lookahead leakage by definition: the model sees rows after the test points during training. Fix: pass `shuffle=False` to keep the last `test_size` fraction as the chronological holdout. Same trap whether you're using linear regression, gradient-boosted trees, or a neural net.",
        example_code="",
        editable_template=(
            "\"\"\"Two-feature random-forest direction classifier with chronological split.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.ensemble import RandomForestClassifier\n"
            "from sklearn.model_selection import train_test_split\n"
            "\n"
            "\n"
            "def rf_accuracy(returns: pd.Series) -> float:\n"
            "    \"\"\"Train a 100-tree RandomForest on (mom_5, vol_20) → sign(next).\n"
            "    Returns the test-set accuracy.\n"
            "\n"
            "    On a random-walk null, honest accuracy is ~0.5. A buggy split\n"
            "    can push it well above 0.6 — that's not skill, that's leakage.\n"
            "    \"\"\"\n"
            "    df = pd.DataFrame({\n"
            "        'mom': returns.shift(1).rolling(5).sum(),\n"
            "        'vol': returns.shift(1).rolling(20).std(),\n"
            "        'next': np.sign(returns),\n"
            "    }).dropna()\n"
            "    X = df[['mom', 'vol']].values\n"
            "    y = df['next'].values\n"
            "    # Bug: train_test_split shuffles by DEFAULT — future rows mix into train.\n"
            "    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=0)\n"
            "    model = RandomForestClassifier(n_estimators=100, random_state=0).fit(Xtr, ytr)\n"
            "    return float(model.score(Xte, yte))\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.ensemble import RandomForestClassifier\n"
            "from sklearn.model_selection import train_test_split\n"
            "\n"
            "\n"
            "def rf_accuracy(returns: pd.Series) -> float:\n"
            "    df = pd.DataFrame({\n"
            "        'mom': returns.shift(1).rolling(5).sum(),\n"
            "        'vol': returns.shift(1).rolling(20).std(),\n"
            "        'next': np.sign(returns),\n"
            "    }).dropna()\n"
            "    X = df[['mom', 'vol']].values\n"
            "    y = df['next'].values\n"
            "    Xtr, Xte, ytr, yte = train_test_split(\n"
            "        X, y, test_size=0.2, shuffle=False\n"
            "    )\n"
            "    model = RandomForestClassifier(n_estimators=100, random_state=0).fit(Xtr, ytr)\n"
            "    return float(model.score(Xte, yte))\n"
        ),
        tests_py=(
            "\"\"\"RF accuracy: deterministic fingerprints distinguish shuffle vs no-shuffle.\n"
            "\n"
            "Both `train_test_split(..., shuffle=True)` (the silent default) and\n"
            "`shuffle=False` produce DETERMINISTIC outputs when random_state is\n"
            "set — but different ones, because they pick different test rows.\n"
            "We fingerprint the no-shuffle values on two seeds and assert the\n"
            "function returns those exact values. The buggy editable shuffles,\n"
            "so it lands on different (lower-on-these-seeds) numbers and fails.\n"
            "\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import rf_accuracy\n"
            "\n"
            "\n"
            "def _noise(n: int = 2000, seed: int = 0) -> pd.Series:\n"
            "    rng = np.random.default_rng(seed)\n"
            "    return pd.Series(rng.normal(0, 0.01, n))\n"
            "\n"
            "\n"
            "# Both values computed with shuffle=False on the given seed.\n"
            "EXPECTED_SEED_1 = 0.5076\n"
            "EXPECTED_SEED_11 = 0.5278\n"
            "\n"
            "\n"
            "def test_seed_1_matches_chronological_fingerprint():\n"
            "    acc = rf_accuracy(_noise(seed=1))\n"
            "    assert abs(acc - EXPECTED_SEED_1) < 5e-3\n"
            "\n"
            "\n"
            "def test_seed_11_matches_chronological_fingerprint():\n"
            "    acc = rf_accuracy(_noise(seed=11))\n"
            "    assert abs(acc - EXPECTED_SEED_11) < 5e-3\n"
            "\n"
            "\n"
            "def test_deterministic_across_calls():\n"
            "    a = rf_accuracy(_noise(seed=3))\n"
            "    b = rf_accuracy(_noise(seed=3))\n"
            "    assert abs(a - b) < 1e-12\n"
            "\n"
            "\n"
            "def test_returns_a_float():\n"
            "    assert isinstance(rf_accuracy(_noise()), float)\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_seed_1_matches_chronological_fingerprint",
                "Seed-1 result matches the shuffle=False fingerprint (≈0.5076).",
            ),
            (
                "tests/test_solution.py::test_seed_11_matches_chronological_fingerprint",
                "Seed-11 result matches the shuffle=False fingerprint (≈0.5278).",
            ),
            (
                "tests/test_solution.py::test_deterministic_across_calls",
                "Function returns the same value on repeated calls with the same input.",
            ),
            (
                "tests/test_solution.py::test_returns_a_float",
                "Function returns a plain Python float.",
            ),
        ],
        your_turn="`train_test_split` is silently shuffling. Add `shuffle=False` so the test set is the last 20% chronologically.",
        hint="`train_test_split(X, y, test_size=0.2, shuffle=False)` — the default is True.",
        skills=["quant", "machine-learning", "backtesting"],
    ),
    Lesson(
        n=38, stage=4, mode="debug",
        title="Time-series cross-validation",
        scenario="Same junior, third sprint. The notebook's CV scores look great. But the CV splitter is *KFold* — which shuffles by default. Future folds get used to predict past folds. The PR review catches it: change `KFold` → `TimeSeriesSplit`, scores collapse to noise, the strategy that was 'ready for live capital' isn't. This is the single biggest mistake quant ML reviewers look for, and the most-googled gotcha after Asness/Pedersen/Moskowitz.",
        learner_goal="Find the wrong cross-validator and swap it for the expanding-window splitter.",
        concept="`KFold(n_splits=5)` randomly partitions rows into 5 folds — for i.i.d. data, fine. For time series, each fold is contaminated: training folds contain rows AFTER some test rows, so the model peeks. `TimeSeriesSplit(n_splits=5)` instead yields *expanding-window* splits: test fold k always starts after train fold k ends. Same import path, same `cross_val_score(model, X, y, cv=...)` call shape — just the splitter class changes. Lopez de Prado's `purgedKFold` extends this with embargo gaps for serially-correlated labels.",
        example_code="",
        editable_template=(
            "\"\"\"Cross-validate a momentum regression with the right CV splitter.\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import KFold, TimeSeriesSplit, cross_val_score\n"
            "\n"
            "\n"
            "def mean_cv_score(returns: pd.Series) -> float:\n"
            "    \"\"\"Return the mean of 5-fold CV R² on a momentum → next-return model.\n"
            "\n"
            "    Must use an EXPANDING-WINDOW (time-aware) splitter so test folds\n"
            "    never see future training data.\n"
            "    \"\"\"\n"
            "    df = pd.DataFrame({\n"
            "        'mom': returns.shift(1).rolling(5).sum(),\n"
            "        'next': returns,\n"
            "    }).dropna()\n"
            "    X = df[['mom']].values\n"
            "    y = df['next'].values\n"
            "    # Bug: KFold shuffles folds — leaks future into the training data.\n"
            "    cv = KFold(n_splits=5, shuffle=True, random_state=0)\n"
            "    scores = cross_val_score(LinearRegression(), X, y, cv=cv)\n"
            "    return float(scores.mean())\n"
        ),
        reference_solution=(
            "import numpy as np\n"
            "import pandas as pd\n"
            "from sklearn.linear_model import LinearRegression\n"
            "from sklearn.model_selection import TimeSeriesSplit, cross_val_score\n"
            "\n"
            "\n"
            "def mean_cv_score(returns: pd.Series) -> float:\n"
            "    df = pd.DataFrame({\n"
            "        'mom': returns.shift(1).rolling(5).sum(),\n"
            "        'next': returns,\n"
            "    }).dropna()\n"
            "    X = df[['mom']].values\n"
            "    y = df['next'].values\n"
            "    cv = TimeSeriesSplit(n_splits=5)\n"
            "    scores = cross_val_score(LinearRegression(), X, y, cv=cv)\n"
            "    return float(scores.mean())\n"
        ),
        tests_py=(
            "\"\"\"CV-splitter selection check via deterministic fingerprint.\n"
            "\n"
            "Both KFold(shuffle=True, random_state=0) and TimeSeriesSplit give\n"
            "DETERMINISTIC outputs for a fixed input — but different ones. We\n"
            "fingerprint the TimeSeriesSplit answer and assert the function\n"
            "matches; the leaky KFold answer is meaningfully off, so the\n"
            "buggy editable fails.\n"
            "\"\"\"\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import pytest\n"
            "\n"
            "from solution import mean_cv_score\n"
            "\n"
            "\n"
            "def _noise(n: int = 3000, seed: int = 0) -> pd.Series:\n"
            "    rng = np.random.default_rng(seed)\n"
            "    return pd.Series(rng.normal(0, 0.01, n))\n"
            "\n"
            "\n"
            "EXPECTED_SEED_1 = -0.005549\n"
            "EXPECTED_SEED_7 = -0.006750\n"
            "\n"
            "\n"
            "def test_seed_1_matches_timeseries_split_fingerprint():\n"
            "    score = mean_cv_score(_noise(seed=1))\n"
            "    assert abs(score - EXPECTED_SEED_1) < 5e-5\n"
            "\n"
            "\n"
            "def test_seed_7_matches_timeseries_split_fingerprint():\n"
            "    score = mean_cv_score(_noise(seed=7))\n"
            "    assert abs(score - EXPECTED_SEED_7) < 5e-5\n"
            "\n"
            "\n"
            "def test_function_is_deterministic_across_calls():\n"
            "    a = mean_cv_score(_noise(seed=2))\n"
            "    b = mean_cv_score(_noise(seed=2))\n"
            "    assert abs(a - b) < 1e-12\n"
            "\n"
            "\n"
            "def test_returns_a_float():\n"
            "    assert isinstance(mean_cv_score(_noise()), float)\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_seed_1_matches_timeseries_split_fingerprint",
                "Seed-1 result matches the TimeSeriesSplit fingerprint (-0.005549).",
            ),
            (
                "tests/test_solution.py::test_seed_7_matches_timeseries_split_fingerprint",
                "Seed-7 result matches the TimeSeriesSplit fingerprint (-0.006750).",
            ),
            (
                "tests/test_solution.py::test_function_is_deterministic_across_calls",
                "Function returns the same value on repeated calls with the same input.",
            ),
            (
                "tests/test_solution.py::test_returns_a_float",
                "Function returns a plain Python float.",
            ),
        ],
        your_turn="Swap `KFold` for `TimeSeriesSplit` (already imported). Same `cross_val_score` call works — the only thing that changes is the splitter you pass in.",
        hint="`TimeSeriesSplit(n_splits=5)` — no shuffle argument, no random_state, it's expanding-window by design.",
        skills=["quant", "machine-learning", "backtesting"],
    ),
    Lesson(
        n=60, stage=4, mode="skeleton",
        n_label="38a",
        order_index_override=3810,
        title="Build a momentum strategy",
        scenario="The previous three lessons built signal, model, and validation. None of them produced a P&L. This is where they connect: read bars from a mock data feed, decide a position from a momentum signal, hold for one day, repeat. The tests include the same lookahead-bias check the senior risk officer runs on every new strategy.",
        learner_goal="Implement a momentum signal + a one-day-hold backtest that passes correctness, no-lookahead, and basic monotonicity tests.",
        concept="A trading algorithm is a function from (history of bars) → (sequence of positions). This lesson factors it into two pieces: `signal_at(closes, t)` returns the desired position at time t (using only past data), and `backtest(symbol)` runs the signal across history and aggregates the P&L. The lookahead-bias test is the structural check that catches most junior bugs: if you can replace future bars with garbage and the signal at t doesn't change, your function is honest.",
        example_code="",
        editable_template=(
            "\"\"\"Momentum strategy — read bars, emit positions, accumulate P&L.\n"
            "\n"
            "Use the Market class from mock_market to fetch history:\n"
            "\n"
            "    from mock_market import Market\n"
            "    bars = Market().history('SPY')\n"
            "\n"
            "Each Bar has .date, .open, .high, .low, .close, .volume.\n"
            "\n"
            "Implement two functions:\n"
            "\n"
            "    signal_at(closes, t, lookback=20) -> int\n"
            "        Returns -1, 0, or +1 based on the lookback-period return:\n"
            "            (closes[t] - closes[t-lookback]) / closes[t-lookback]\n"
            "        > 0 → +1, < 0 → -1, t < lookback or 0 → 0.\n"
            "        ⚠ Must use ONLY closes[:t+1]. Lookahead is forbidden.\n"
            "\n"
            "    backtest(symbol='SPY', lookback=20) -> dict\n"
            "        Apply signal_at across the full history; hold each signal\n"
            "        for ONE day (signal at t controls return at t+1).\n"
            "        Return: {'sharpe': float, 'max_drawdown': float, 'trades': int}\n"
            "        - sharpe: annualised, 252 days/year ((mean*252) / (std*sqrt(252))).\n"
            "        - max_drawdown: worst peak-to-trough as a NEGATIVE fraction.\n"
            "        - trades: count of position CHANGES (signal[t] != signal[t-1]).\n"
            "\"\"\"\n"
            "from mock_market import Market\n"
            "\n"
            "\n"
            "def signal_at(closes, t, lookback=20):\n"
            "    raise NotImplementedError(\"Implement signal_at\")\n"
            "\n"
            "\n"
            "def backtest(symbol='SPY', lookback=20):\n"
            "    raise NotImplementedError(\"Implement backtest\")\n"
        ),
        reference_solution=(
            "import math\n"
            "from mock_market import Market\n"
            "\n"
            "\n"
            "def signal_at(closes, t, lookback=20):\n"
            "    if t < lookback:\n"
            "        return 0\n"
            "    base = closes[t - lookback]\n"
            "    if base == 0:\n"
            "        return 0\n"
            "    ret = (closes[t] - base) / base\n"
            "    if ret > 0:\n"
            "        return 1\n"
            "    elif ret < 0:\n"
            "        return -1\n"
            "    return 0\n"
            "\n"
            "\n"
            "def backtest(symbol='SPY', lookback=20):\n"
            "    bars = Market().history(symbol)\n"
            "    closes = [b.close for b in bars]\n"
            "    n = len(closes)\n"
            "    signals = [signal_at(closes, t, lookback) for t in range(n)]\n"
            "    rets = []\n"
            "    trades = 0\n"
            "    prev = 0\n"
            "    for t in range(n - 1):\n"
            "        next_ret = (closes[t + 1] - closes[t]) / closes[t]\n"
            "        rets.append(signals[t] * next_ret)\n"
            "        if signals[t] != prev:\n"
            "            trades += 1\n"
            "        prev = signals[t]\n"
            "    if not rets:\n"
            "        return {'sharpe': 0.0, 'max_drawdown': 0.0, 'trades': 0}\n"
            "    m = sum(rets) / len(rets)\n"
            "    var = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)\n"
            "    s = math.sqrt(var)\n"
            "    sharpe = 0.0 if s == 0 else (m * 252) / (s * math.sqrt(252))\n"
            "    # Max drawdown from running equity curve.\n"
            "    eq = 1.0\n"
            "    peak = 1.0\n"
            "    max_dd = 0.0\n"
            "    for r in rets:\n"
            "        eq *= 1 + r\n"
            "        peak = max(peak, eq)\n"
            "        dd = eq / peak - 1\n"
            "        if dd < max_dd:\n"
            "            max_dd = dd\n"
            "    return {\n"
            "        'sharpe': float(sharpe),\n"
            "        'max_drawdown': float(max_dd),\n"
            "        'trades': int(trades),\n"
            "    }\n"
        ),
        tests_py=(
            "\"\"\"Momentum strategy: correctness, no-lookahead, P&L structure.\"\"\"\n"
            "import math\n"
            "import pytest\n"
            "\n"
            "from solution import signal_at, backtest\n"
            "from mock_market import Market\n"
            "\n"
            "\n"
            "def _closes():\n"
            "    return [b.close for b in Market().history('SPY')]\n"
            "\n"
            "\n"
            "def test_signal_returns_one_of_three_values():\n"
            "    closes = _closes()\n"
            "    for t in [30, 100, 500]:\n"
            "        s = signal_at(closes, t, lookback=20)\n"
            "        assert s in (-1, 0, 1), f\"unexpected signal {s} at t={t}\"\n"
            "\n"
            "\n"
            "def test_signal_is_zero_when_t_under_lookback():\n"
            "    closes = _closes()\n"
            "    for t in [0, 5, 19]:\n"
            "        assert signal_at(closes, t, lookback=20) == 0\n"
            "\n"
            "\n"
            "def test_signal_is_long_on_monotone_up():\n"
            "    closes = [float(i) for i in range(1, 100)]\n"
            "    assert signal_at(closes, 50, lookback=20) == 1\n"
            "\n"
            "\n"
            "def test_signal_is_short_on_monotone_down():\n"
            "    closes = [float(i) for i in range(100, 1, -1)]\n"
            "    assert signal_at(closes, 50, lookback=20) == -1\n"
            "\n"
            "\n"
            "def test_signal_no_lookahead_bias():\n"
            "    # Replace closes[t+1:] with nonsense — signal at t must not change.\n"
            "    closes = _closes()\n"
            "    t = 200\n"
            "    truth = signal_at(closes, t, lookback=20)\n"
            "    poisoned = closes[: t + 1] + [-1e9] * (len(closes) - t - 1)\n"
            "    assert signal_at(poisoned, t, lookback=20) == truth\n"
            "\n"
            "\n"
            "def test_backtest_returns_dict_with_required_keys():\n"
            "    result = backtest('SPY', lookback=20)\n"
            "    assert isinstance(result, dict)\n"
            "    for k in ('sharpe', 'max_drawdown', 'trades'):\n"
            "        assert k in result, f\"missing key: {k}\"\n"
            "\n"
            "\n"
            "def test_backtest_sharpe_is_finite_float():\n"
            "    result = backtest('SPY', lookback=20)\n"
            "    assert isinstance(result['sharpe'], float)\n"
            "    assert math.isfinite(result['sharpe'])\n"
            "\n"
            "\n"
            "def test_backtest_max_drawdown_in_valid_range():\n"
            "    result = backtest('SPY', lookback=20)\n"
            "    assert isinstance(result['max_drawdown'], float)\n"
            "    assert -1.0 <= result['max_drawdown'] <= 0.0\n"
            "\n"
            "\n"
            "def test_backtest_trades_is_nonnegative_int():\n"
            "    result = backtest('SPY', lookback=20)\n"
            "    assert isinstance(result['trades'], int)\n"
            "    assert result['trades'] >= 0\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_signal_returns_one_of_three_values",
                "signal_at returns only -1, 0, or +1.",
            ),
            (
                "tests/test_solution.py::test_signal_is_zero_when_t_under_lookback",
                "signal_at returns 0 before enough lookback history is available.",
            ),
            (
                "tests/test_solution.py::test_signal_is_long_on_monotone_up",
                "Monotonically rising prices give +1 (long).",
            ),
            (
                "tests/test_solution.py::test_signal_is_short_on_monotone_down",
                "Monotonically falling prices give -1 (short).",
            ),
            (
                "tests/test_solution.py::test_signal_no_lookahead_bias",
                "Poisoning closes[t+1:] does not change the signal at t — the lookahead-bias check.",
            ),
            (
                "tests/test_solution.py::test_backtest_returns_dict_with_required_keys",
                "backtest returns a dict with 'sharpe', 'max_drawdown', 'trades'.",
            ),
            (
                "tests/test_solution.py::test_backtest_sharpe_is_finite_float",
                "Sharpe is a finite float (no NaN, no inf).",
            ),
            (
                "tests/test_solution.py::test_backtest_max_drawdown_in_valid_range",
                "Max drawdown is a float in [-1, 0].",
            ),
            (
                "tests/test_solution.py::test_backtest_trades_is_nonnegative_int",
                "Trade count is a non-negative integer.",
            ),
        ],
        extra_readonly={"mock_market.py": MOCK_MARKET_PY},
        your_turn="Implement `signal_at` (4-5 lines of branching) and `backtest` (a loop over closes, accumulate signal × next-day return, compute Sharpe + max drawdown). The lookahead-bias test is the structural check most junior bugs trip.",
        hint="signal_at: guard t < lookback, then compute the lookback-period return and return its sign. backtest: loop t in range(n-1), append signals[t] * (closes[t+1]/closes[t] - 1) to the return series, count position changes.",
        why_this="This loop is the smallest end-to-end backtest you can build — signal → position → return → metrics. The same shape underlies vectorbt, zipline, and every fund's in-house backtester. Get this honest (no lookahead) and the rest is just feature engineering.",
        skills=["quant", "machine-learning", "backtesting"],
    ),
    Lesson(
        n=61, stage=4, mode="skeleton",
        n_label="38b",
        order_index_override=3820,
        title="Build a pairs trade",
        scenario="The momentum strategy traded directional moves in one symbol. A pairs trade is the opposite bet: when two correlated symbols drift apart, expect them to converge — short the rich one, long the cheap one, profit on the mean-reversion. The mock market gives you SPY and AAPL (AAPL has β ≈ 1.3 to SPY plus idiosyncratic noise) — the exact shape pairs traders look for.",
        learner_goal="Implement a rolling z-score on the SPY-AAPL log spread, then a mean-reversion strategy that enters on |z| > entry threshold and exits inside the band.",
        concept="The spread `s_t = log(P_SPY) - log(P_AAPL)` is approximately mean-reverting when the two symbols share a common factor (here: market beta). A rolling z-score `(s_t - μ) / σ` measured over a backward window flags extremes. Mean-reversion rules: when z exceeds the entry threshold the spread is *rich* — short it (short SPY, long AAPL); when z falls below the exit threshold the bet's been collected — flatten. Lookahead bias is the same trap as the momentum strategy: rolling_zscore at t must depend on s[:t+1] only.",
        example_code="",
        editable_template=(
            "\"\"\"Pairs trade — z-score of the SPY-AAPL log spread.\n"
            "\n"
            "Use the Market class to fetch both symbols' bars:\n"
            "\n"
            "    from mock_market import Market\n"
            "    spy = Market().history('SPY')\n"
            "    aapl = Market().history('AAPL')\n"
            "\n"
            "Implement:\n"
            "\n"
            "    rolling_zscore(spread, t, window=60) -> float\n"
            "        Z-score of spread[t] against the mean and std of\n"
            "        the previous `window` observations: spread[t-window+1 : t+1].\n"
            "        Return float('nan') for t < window - 1.\n"
            "        ⚠ Must use ONLY spread[:t+1].\n"
            "\n"
            "    backtest(window=60, entry=2.0, exit=0.5) -> dict\n"
            "        Compute the spread as math.log(spy_close) - math.log(aapl_close).\n"
            "        Compute rolling_zscore[t] for every t.\n"
            "        Position rules (start flat at t=0):\n"
            "          - If flat and z[t] >  entry: position = -1 (short spread).\n"
            "          - If flat and z[t] < -entry: position = +1 (long spread).\n"
            "          - If in position and |z[t]| < exit: flatten.\n"
            "          - Else hold previous position.\n"
            "          - When z[t] is NaN: hold previous position.\n"
            "        Strategy P&L at t = position[t] * (spread[t+1] - spread[t]).\n"
            "        Return: {'sharpe': float, 'max_drawdown': float, 'trades': int}.\n"
            "          - sharpe: annualised, 252-day convention.\n"
            "          - max_drawdown: negative fraction of running equity.\n"
            "          - trades: count of position CHANGES.\n"
            "\"\"\"\n"
            "import math\n"
            "from mock_market import Market\n"
            "\n"
            "\n"
            "def rolling_zscore(spread, t, window=60):\n"
            "    raise NotImplementedError(\"Implement rolling_zscore\")\n"
            "\n"
            "\n"
            "def backtest(window=60, entry=2.0, exit=0.5):\n"
            "    raise NotImplementedError(\"Implement backtest\")\n"
        ),
        reference_solution=(
            "import math\n"
            "from mock_market import Market\n"
            "\n"
            "\n"
            "def rolling_zscore(spread, t, window=60):\n"
            "    if t < window - 1:\n"
            "        return float('nan')\n"
            "    chunk = spread[t - window + 1 : t + 1]\n"
            "    m = sum(chunk) / window\n"
            "    var = sum((c - m) ** 2 for c in chunk) / (window - 1)\n"
            "    s = math.sqrt(var)\n"
            "    if s == 0:\n"
            "        return 0.0\n"
            "    return (spread[t] - m) / s\n"
            "\n"
            "\n"
            "def backtest(window=60, entry=2.0, exit=0.5):\n"
            "    spy_bars = Market().history('SPY')\n"
            "    aapl_bars = Market().history('AAPL')\n"
            "    n = min(len(spy_bars), len(aapl_bars))\n"
            "    spread = [\n"
            "        math.log(spy_bars[i].close) - math.log(aapl_bars[i].close)\n"
            "        for i in range(n)\n"
            "    ]\n"
            "    positions = [0] * n\n"
            "    current = 0\n"
            "    trades = 0\n"
            "    for t in range(n):\n"
            "        z = rolling_zscore(spread, t, window)\n"
            "        if math.isnan(z):\n"
            "            positions[t] = current\n"
            "            continue\n"
            "        if current == 0:\n"
            "            if z > entry:\n"
            "                current = -1\n"
            "            elif z < -entry:\n"
            "                current = 1\n"
            "        else:\n"
            "            if abs(z) < exit:\n"
            "                current = 0\n"
            "        positions[t] = current\n"
            "        if t > 0 and positions[t] != positions[t - 1]:\n"
            "            trades += 1\n"
            "    rets = [\n"
            "        positions[t] * (spread[t + 1] - spread[t])\n"
            "        for t in range(n - 1)\n"
            "    ]\n"
            "    if not rets:\n"
            "        return {'sharpe': 0.0, 'max_drawdown': 0.0, 'trades': 0}\n"
            "    m = sum(rets) / len(rets)\n"
            "    var = sum((r - m) ** 2 for r in rets) / max(1, len(rets) - 1)\n"
            "    s = math.sqrt(var)\n"
            "    sharpe = 0.0 if s == 0 else (m * 252) / (s * math.sqrt(252))\n"
            "    eq = 1.0\n"
            "    peak = 1.0\n"
            "    max_dd = 0.0\n"
            "    for r in rets:\n"
            "        eq *= 1 + r\n"
            "        peak = max(peak, eq)\n"
            "        dd = eq / peak - 1\n"
            "        if dd < max_dd:\n"
            "            max_dd = dd\n"
            "    return {\n"
            "        'sharpe': float(sharpe),\n"
            "        'max_drawdown': float(max_dd),\n"
            "        'trades': int(trades),\n"
            "    }\n"
        ),
        tests_py=(
            "\"\"\"Pairs trade: z-score correctness, no-lookahead, structural P&L.\"\"\"\n"
            "import math\n"
            "import pytest\n"
            "\n"
            "from solution import rolling_zscore, backtest\n"
            "from mock_market import Market\n"
            "\n"
            "\n"
            "def _spread():\n"
            "    spy = Market().history('SPY')\n"
            "    aapl = Market().history('AAPL')\n"
            "    return [math.log(spy[i].close) - math.log(aapl[i].close)\n"
            "            for i in range(min(len(spy), len(aapl)))]\n"
            "\n"
            "\n"
            "def test_zscore_is_nan_before_window():\n"
            "    s = _spread()\n"
            "    for t in [0, 10, 58]:\n"
            "        assert math.isnan(rolling_zscore(s, t, window=60))\n"
            "\n"
            "\n"
            "def test_zscore_is_finite_after_window():\n"
            "    s = _spread()\n"
            "    for t in [60, 200, 500]:\n"
            "        z = rolling_zscore(s, t, window=60)\n"
            "        assert isinstance(z, float)\n"
            "        assert math.isfinite(z)\n"
            "\n"
            "\n"
            "def test_zscore_matches_hand_calc_constant_window():\n"
            "    # Constant window → variance 0 → guard returns 0.\n"
            "    s = [5.0] * 100\n"
            "    assert rolling_zscore(s, 90, window=60) == 0.0\n"
            "\n"
            "\n"
            "def test_zscore_matches_hand_calc_known_series():\n"
            "    # Window of 4 with [1,2,3,4] → mean=2.5, sample std=sqrt(5/3).\n"
            "    # Z at t=3 of 4 against window [1,2,3,4]: (4 - 2.5)/sqrt(5/3) ≈ 1.1619.\n"
            "    s = [1.0, 2.0, 3.0, 4.0]\n"
            "    z = rolling_zscore(s, 3, window=4)\n"
            "    assert abs(z - 1.1619) < 1e-3\n"
            "\n"
            "\n"
            "def test_zscore_no_lookahead_bias():\n"
            "    # Poison spread[t+1:]; z at t must not change.\n"
            "    s = _spread()\n"
            "    t = 300\n"
            "    truth = rolling_zscore(s, t, window=60)\n"
            "    poisoned = s[: t + 1] + [-1e9] * (len(s) - t - 1)\n"
            "    assert abs(rolling_zscore(poisoned, t, window=60) - truth) < 1e-9\n"
            "\n"
            "\n"
            "def test_backtest_returns_dict_with_required_keys():\n"
            "    r = backtest()\n"
            "    assert isinstance(r, dict)\n"
            "    for k in ('sharpe', 'max_drawdown', 'trades'):\n"
            "        assert k in r\n"
            "\n"
            "\n"
            "def test_backtest_sharpe_is_finite_float():\n"
            "    r = backtest()\n"
            "    assert isinstance(r['sharpe'], float)\n"
            "    assert math.isfinite(r['sharpe'])\n"
            "\n"
            "\n"
            "def test_backtest_max_drawdown_in_valid_range():\n"
            "    r = backtest()\n"
            "    assert -1.0 <= r['max_drawdown'] <= 0.0\n"
            "\n"
            "\n"
            "def test_backtest_trades_is_nonnegative_int():\n"
            "    r = backtest()\n"
            "    assert isinstance(r['trades'], int)\n"
            "    assert r['trades'] >= 0\n"
        ),
        pytest_targets=[
            (
                "tests/test_solution.py::test_zscore_is_nan_before_window",
                "rolling_zscore returns NaN for t < window - 1.",
            ),
            (
                "tests/test_solution.py::test_zscore_is_finite_after_window",
                "rolling_zscore returns a finite float once the backward window is full.",
            ),
            (
                "tests/test_solution.py::test_zscore_matches_hand_calc_constant_window",
                "Constant series produces z = 0 (the zero-variance guard).",
            ),
            (
                "tests/test_solution.py::test_zscore_matches_hand_calc_known_series",
                "On [1,2,3,4], z at t=3 matches the analytical value ≈ 1.162.",
            ),
            (
                "tests/test_solution.py::test_zscore_no_lookahead_bias",
                "Poisoning spread[t+1:] does not change rolling_zscore at t.",
            ),
            (
                "tests/test_solution.py::test_backtest_returns_dict_with_required_keys",
                "backtest returns a dict with sharpe / max_drawdown / trades.",
            ),
            (
                "tests/test_solution.py::test_backtest_sharpe_is_finite_float",
                "Sharpe is a finite float.",
            ),
            (
                "tests/test_solution.py::test_backtest_max_drawdown_in_valid_range",
                "Max drawdown is in [-1, 0].",
            ),
            (
                "tests/test_solution.py::test_backtest_trades_is_nonnegative_int",
                "Trade count is a non-negative integer.",
            ),
        ],
        extra_readonly={"mock_market.py": MOCK_MARKET_PY},
        your_turn="Implement `rolling_zscore` (mean + sample std over the trailing window) and `backtest` (compute spread, walk forward, apply entry/exit rules, accumulate P&L). The lookahead-bias test and the constant-window guard are the structural checks; the sharpe/dd tests just verify the output shape.",
        hint="rolling_zscore: slice `spread[t-window+1 : t+1]`, compute mean + std (sample, ddof=1), guard std==0. backtest: walk forward with a single `current` position int; flip on |z| > entry from flat, flatten on |z| < exit while in position.",
        why_this="Pairs trades are the canonical statistical-arbitrage shape — the same z-score-of-spread structure underlies every cointegration-based strategy. The lesson's no-lookahead test is the screen every cointegration ticket is gated on at a real fund.",
        skills=["quant", "machine-learning", "backtesting"],
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

    # ============ Stage 5 — Performance & C (13 lessons incl. 40b) ============
    Lesson(
        n=55, stage=5, mode="predict",
        n_label="40b",
        order_index_override=3950,
        title="Python hits a wall",
        scenario="You've built three strategies in Python. They work. Now imagine the same loop running at the exchange — every tick, every order book update, 24 hours a day. The bookkeeping that took milliseconds in your backtest needs microseconds in production. This is the lesson where Python's interpreter overhead matters.",
        learner_goal="Read a simple Python backtest loop and identify what's dominating the per-tick cost.",
        concept="The CPython interpreter dispatches each bytecode instruction via a giant `switch` statement; each step typically costs 50-100ns of pure overhead beyond the actual work. For the loop below, that's ~8 dispatched ops per tick. At a million ticks per second (a busy quote feed), the interpreter alone consumes ~500ns/tick — already half the entire 10µs end-to-end budget on a US equity option quote. The actual *arithmetic* is single-digit nanoseconds. The dispatch is the wall — and it's why the inner loops of every low-latency system are written in C.",
        example_code=(
            "# A momentum-signal backtester: read tick, update rolling mean, emit signal.\n"
            "# Annotated with the dominant bottleneck per line.\n"
            "import time\n"
            "\n"
            "def backtest(prices, window):\n"
            "    rolling_sum = 0.0\n"
            "    rolling_window = []\n"
            "    signals = []\n"
            "    for px in prices:                       # bytecode dispatch + box\n"
            "        rolling_window.append(px)            # list grow + ref-bump\n"
            "        rolling_sum += px                    # float add + box-rewrap\n"
            "        if len(rolling_window) > window:     # builtin call dispatch\n"
            "            rolling_sum -= rolling_window.pop(0)  # memcpy + ref-bump\n"
            "        if len(rolling_window) == window:    # builtin call dispatch\n"
            "            mean = rolling_sum / window      # float divide + box\n"
            "            signals.append(1 if px > mean else 0)  # compare + dispatch\n"
            "    return signals\n"
            "\n"
            "# 100k ticks of 'data'.\n"
            "prices = [100.0 + i*0.001 for i in range(100_000)]\n"
            "signals = backtest(prices, 20)\n"
            "# Which axis of cost dominates?\n"
            "#   interpreter — bytecode dispatch + boxing (∼500ns/tick total).\n"
            "#   memory      — heap-alloc / cache-miss costs (~100ns each, occasional).\n"
            "#   io          — print, network, syscall (not in this loop).\n"
            "print('interpreter')"
        ),
        code=(
            "import time\n"
            "\n"
            "def backtest(prices, window):\n"
            "    rolling_sum = 0.0\n"
            "    rolling_window = []\n"
            "    signals = []\n"
            "    for px in prices:\n"
            "        rolling_window.append(px)\n"
            "        rolling_sum += px\n"
            "        if len(rolling_window) > window:\n"
            "            rolling_sum -= rolling_window.pop(0)\n"
            "        if len(rolling_window) == window:\n"
            "            mean = rolling_sum / window\n"
            "            signals.append(1 if px > mean else 0)\n"
            "    return signals\n"
            "\n"
            "prices = [100.0 + i*0.001 for i in range(100_000)]\n"
            "signals = backtest(prices, 20)\n"
            "print('interpreter')"
        ),
        your_turn="Read the loop's per-line cost annotation (in the Example), then predict which cost class dominates: `interpreter`, `memory`, or `io`.",
        expected_stdout="interpreter",
        prompt="Predict the printed output.",
        why_this="This is the answer to 'why do quants use C': not because the arithmetic is faster, but because the interpreter dispatch in the hot path doesn't exist. Lessons 41-49 build the muscle to write that hot path.",
        skills=["quant", "performance", "c-language"],
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
        why_this="The literal program that runs in every kernel and most exchange matching engines. Building muscle memory for the boilerplate frees you to think about the algorithm.",
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
        why_this="Fixed-width integers and IEEE doubles are how wire-format protocols encode prices and quantities. Get the type right and your parsing matches the exchange byte-for-byte.",
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
        why_this="Tight `for` loops the compiler can unroll and vectorise are how numpy, BLAS, and every hot path in a low-latency system actually run their arithmetic.",
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
        why_this="Pointer arithmetic plus cache-line-aware layouts are how you write a market-data ring buffer that doesn't allocate per tick. lesson 48 is the canonical example.",
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
        why_this="Byte-exact struct layouts are what wire-format protocols (FIX, ITCH, MDP3) compile down to. The struct declaration is the contract.",
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
        why_this="Strategy dispatch tables in C use function pointers — what a Python `dict[str, Callable]` becomes when you cross the JIT boundary into the hot path.",
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
        why_this="Production low-latency code pre-allocates everything at boot precisely to never call malloc on the hot path — the kernel might decide to give you a slow allocation right before a market open.",
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
        prompt="Predict the printed output.",
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
        prompt="Predict the printed output.",
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
        lines.append(f"  {lesson.display_index}")
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
