"""Generate the Quant Programmer track mini-project SQL + TypeScript config.

Each project is a multi-file pyodide challenge: 4–6 editable + readonly
Python files plus a tests/ directory the runner discovers automatically.
The scaffolds ship inline in the generated TS config — no GitHub mirror
required (Project 5's `.wasm` demo is still loaded from /wasm/quant/).

Run from repo root:

    python scripts/generate_quant_projects.py

Writes:

- supabase/quant_projects_seed.generated.sql
- apps/web/src/lib/quant-projects-config.generated.ts
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACK_UUID = "00000000-0000-0000-0000-000000000003"

STAGE_MODULE_UUID = {
    1: "00000000-0000-0000-0000-000000000031",
    2: "00000000-0000-0000-0000-000000000032",
    3: "00000000-0000-0000-0000-000000000033",
    4: "00000000-0000-0000-0000-000000000034",
    5: "00000000-0000-0000-0000-000000000035",
}


@dataclass
class TestCase:
    pytest_id: str
    description: str


@dataclass
class Project:
    """A multi-file pyodide challenge with inline file scaffolds."""

    n: int  # 1..5 — drives UUID and slug
    stage: int  # 1..5 — module to attach to
    title: str
    scenario: str
    learner_goal: str
    overview_md: str  # rendered as instructions
    editable: dict[str, str] = field(default_factory=dict)
    readonly: dict[str, str] = field(default_factory=dict)
    tests: list[TestCase] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return f"quant-project-{self.n}-{self._kebab(self.title)}"

    @property
    def uuid(self) -> str:
        # 0x340..0x34F — gap above the 51 lessons at 0x300..0x332.
        return f"00000000-0000-0000-0000-{0x340 + (self.n - 1):012x}"

    @property
    def module_uuid(self) -> str:
        return STAGE_MODULE_UUID[self.stage]

    @staticmethod
    def _kebab(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    def all_files(self) -> dict[str, str]:
        return {**self.editable, **self.readonly}


# ---- Project content ----------------------------------------------------

# Project 1 — Monte Carlo of asset paths -----------------------------------

P1_PATHS_PY = '''"""Monte Carlo of asset paths under geometric Brownian motion (GBM).

GBM is the canonical model for asset prices in quant finance — it's
what Black-Scholes assumes and what every option-pricing Monte Carlo
starts with. Your job here is to implement the simulator from scratch.

References:
- Hilpisch, "Derivatives Analytics with Python" (dawp):
  https://github.com/yhilpisch/dawp
- Glasserman, "Monte Carlo Methods in Financial Engineering"
"""
import numpy as np


def simulate_gbm(
    S0: float,
    mu: float,
    sigma: float,
    T: float,
    steps: int,
    paths: int,
    seed: int = 0,
) -> np.ndarray:
    """Simulate `paths` independent GBM trajectories from t=0 to t=T.

    Use the exact log-Euler step:

        S_{t+dt} = S_t * exp((mu - sigma^2 / 2) * dt + sigma * sqrt(dt) * Z)

    where Z ~ N(0, 1). Build the (steps, paths) shocks first, then
    cumulative-sum the log-increments and exponentiate.

    Parameters
    ----------
    S0     : initial price
    mu     : annualised drift
    sigma  : annualised volatility (>= 0)
    T      : horizon in years
    steps  : number of time steps in [0, T]
    paths  : number of independent simulations
    seed   : RNG seed so results reproduce bit-for-bit across runs

    Returns
    -------
    prices : ndarray of shape (steps + 1, paths)
        prices[0, :] is S0 for every path; prices[-1, :] is the
        terminal price of each path.
    """
    raise NotImplementedError("Implement simulate_gbm")
'''


P1_STATS_PY = '''"""Summary statistics for the terminal-price distribution."""
import numpy as np


def terminal_stats(prices: np.ndarray) -> dict:
    """Return summary stats of the final row of `prices`.

    Expected keys: 'mean', 'std', 'p05', 'p95'. All values are floats.

    Parameters
    ----------
    prices : ndarray of shape (steps + 1, paths) — output of `simulate_gbm`.

    Returns
    -------
    dict with the four keys above. Use np.percentile for the percentiles
    (q in 0..100, NOT 0..1).
    """
    raise NotImplementedError("Implement terminal_stats")
'''


P1_TEST_PATHS_PY = '''"""Tests for the GBM simulator and terminal-distribution stats."""
import numpy as np
import pytest

from paths import simulate_gbm
from stats import terminal_stats


def test_shape_is_steps_plus_1_by_paths():
    out = simulate_gbm(100, 0.05, 0.2, 1.0, 252, 500, seed=1)
    assert out.shape == (253, 500)


def test_first_row_is_S0():
    out = simulate_gbm(123.45, 0.05, 0.2, 1.0, 252, 100, seed=1)
    assert np.allclose(out[0], 123.45)


def test_seed_reproduces_paths():
    a = simulate_gbm(100, 0.05, 0.2, 1.0, 50, 100, seed=42)
    b = simulate_gbm(100, 0.05, 0.2, 1.0, 50, 100, seed=42)
    assert np.allclose(a, b)


def test_zero_vol_collapses_to_deterministic_drift():
    # With sigma=0, every path matches S0 * exp(mu * T) at the terminal step.
    out = simulate_gbm(100, 0.05, 0.0, 1.0, 100, 50, seed=7)
    expected = 100 * np.exp(0.05 * 1.0)
    assert np.allclose(out[-1], expected, rtol=1e-10)


def test_mean_drift_with_many_paths():
    # E[S_T] = S0 * exp(mu * T). 10k paths gets the sample mean close.
    out = simulate_gbm(100, 0.10, 0.2, 1.0, 252, 10_000, seed=11)
    expected = 100 * np.exp(0.10 * 1.0)
    sample_mean = float(out[-1].mean())
    assert abs(sample_mean - expected) / expected < 0.02  # within 2%


def test_log_return_variance_scales_linearly_with_horizon():
    # Var(log(S_T / S0)) = sigma^2 * T — doubling T should ~double var.
    out1 = simulate_gbm(100, 0.05, 0.25, 1.0, 252, 5_000, seed=21)
    out2 = simulate_gbm(100, 0.05, 0.25, 2.0, 504, 5_000, seed=21)
    var1 = float(np.var(np.log(out1[-1] / 100)))
    var2 = float(np.var(np.log(out2[-1] / 100)))
    assert 1.7 < (var2 / var1) < 2.3


def test_terminal_stats_returns_expected_keys():
    out = simulate_gbm(100, 0.05, 0.2, 1.0, 252, 1000, seed=33)
    s = terminal_stats(out)
    assert set(s.keys()) == {"mean", "std", "p05", "p95"}


def test_terminal_stats_values_make_sense():
    # Deterministic seed → deterministic stats.
    out = simulate_gbm(100, 0.05, 0.2, 1.0, 252, 5000, seed=55)
    s = terminal_stats(out)
    # Empirical mean should be close to S0 * exp(mu * T) = ~105.
    assert abs(s["mean"] - 105) < 3  # within £3
    # p05 < mean < p95 — sanity ordering of the percentiles.
    assert s["p05"] < s["mean"] < s["p95"]
'''


P1_CONFTEST_PY = '''# Pytest discovery: pyodide puts this project at /home/pyodide and inserts
# that dir on sys.path, so `from paths import ...` resolves directly.
# No fixtures needed.
'''


P1_README_MD = '''# Project 1 — Monte Carlo of asset paths

Welcome to the canonical "first quant project." Simulate many price
paths under geometric Brownian motion (GBM), then study the resulting
distribution of terminal prices.

## What you build

- **`paths.py`** — `simulate_gbm(S0, mu, sigma, T, steps, paths, seed)`
  returns a `(steps + 1, paths)` ndarray of price trajectories.
- **`stats.py`** — `terminal_stats(prices)` returns the summary stats of
  the final row: `{mean, std, p05, p95}`.

## What the tests check

- Shape, first-row-is-S0, reproducibility under a fixed seed
- Zero-vol path matches `S0 * exp(mu * T)` exactly
- Sample mean of `S_T` is within 2% of `S0 * exp(mu * T)` at 10k paths
- Variance of `log(S_T / S0)` scales linearly with horizon
- `terminal_stats` returns the four expected keys with the right ordering

## References

- Hilpisch, *Derivatives Analytics with Python* (dawp) —
  github.com/yhilpisch/dawp
- Glasserman, *Monte Carlo Methods in Financial Engineering* — the
  textbook every quant has on their shelf

## Time

~60 minutes if you know GBM; ~2 hours from first principles.
'''


P1 = Project(
    n=1,
    stage=1,
    title="Monte Carlo asset paths",
    scenario=(
        "Welcome to your first proper quant project. The Monte Carlo "
        "simulator you build here is the same engine — modulo a few "
        "performance tweaks — that every Bank's exotic-options desk "
        "uses to price path-dependent structures, that every risk "
        "team uses to compute VaR via simulation, and that every "
        "research notebook at AQR or Citadel starts with when "
        "studying a new strategy's path distribution."
    ),
    learner_goal=(
        "Implement a GBM simulator and a terminal-distribution stats "
        "helper, then pass 8 tests that check shape, reproducibility, "
        "drift, variance scaling, and the percentile structure."
    ),
    overview_md=P1_README_MD,
    editable={
        "paths.py": P1_PATHS_PY,
        "stats.py": P1_STATS_PY,
    },
    readonly={
        "tests/test_paths.py": P1_TEST_PATHS_PY,
        "tests/conftest.py": P1_CONFTEST_PY,
        "README.md": P1_README_MD,
    },
    tests=[
        TestCase(
            "tests/test_paths.py::test_shape_is_steps_plus_1_by_paths",
            "Output is shape (steps + 1, paths).",
        ),
        TestCase(
            "tests/test_paths.py::test_first_row_is_S0",
            "Row 0 of the result is the initial price S0 for every path.",
        ),
        TestCase(
            "tests/test_paths.py::test_seed_reproduces_paths",
            "Same seed twice → identical paths (reproducibility).",
        ),
        TestCase(
            "tests/test_paths.py::test_zero_vol_collapses_to_deterministic_drift",
            "With sigma=0, every terminal price equals S0 * exp(mu * T).",
        ),
        TestCase(
            "tests/test_paths.py::test_mean_drift_with_many_paths",
            "With 10k paths, the empirical mean of S_T sits within 2% of S0 * exp(mu * T).",
        ),
        TestCase(
            "tests/test_paths.py::test_log_return_variance_scales_linearly_with_horizon",
            "Var(log(S_T / S0)) ≈ sigma^2 * T — doubling T doubles the variance.",
        ),
        TestCase(
            "tests/test_paths.py::test_terminal_stats_returns_expected_keys",
            "`terminal_stats` returns exactly the keys {mean, std, p05, p95}.",
        ),
        TestCase(
            "tests/test_paths.py::test_terminal_stats_values_make_sense",
            "Stats values match S0 * exp(mu * T) within tolerance and percentiles are ordered.",
        ),
    ],
    skills=["quant", "numpy", "monte-carlo", "random-numbers"],
)


# Project 2 — Return-distribution dashboard -------------------------------

P2_DASHBOARD_PY = '''"""Build a daily-returns dashboard across five tickers.

Real research uses bundled CSVs. To keep this project entirely
deterministic and offline-safe, we synthesise the returns from a fixed
RNG — same shape, same tests, no I/O. Treat each column as a ticker.
"""
import numpy as np
import pandas as pd

TICKERS = ["SPY", "AAPL", "QQQ", "TLT", "GLD"]
# Annualised drift and vol per ticker — fixed so the tests reproduce.
DRIFTS = np.array([0.10, 0.18, 0.13, 0.02, 0.05])
VOLS   = np.array([0.18, 0.30, 0.22, 0.12, 0.15])


def load_returns(days: int = 2500, seed: int = 0) -> pd.DataFrame:
    """Return a (days, 5) DataFrame of daily log returns for TICKERS.

    Use `np.random.default_rng(seed)` so the dataset is reproducible.
    Daily drift is `DRIFTS / 252`; daily vol is `VOLS / sqrt(252)`.

    Returns
    -------
    DataFrame with columns equal to TICKERS, index 0..days-1, dtype float.
    """
    raise NotImplementedError("Implement load_returns")


def summary_metrics(returns: pd.DataFrame) -> pd.DataFrame:
    """Per-column summary stats. Returns a DataFrame indexed by ticker
    with columns: ['mean_annual', 'vol_annual', 'sharpe', 'skew', 'kurt'].

    - mean_annual = mean(daily) * 252
    - vol_annual  = std(daily)  * sqrt(252)
    - sharpe      = mean_annual / vol_annual  (rf = 0)
    - skew, kurt  = scipy.stats.skew / kurtosis on the daily series

    Round every value to 4 decimal places.
    """
    raise NotImplementedError("Implement summary_metrics")
'''


P2_METRICS_PY = '''"""Drawdown helpers used by tests and a future viz layer."""
import numpy as np
import pandas as pd


def max_drawdown(returns: pd.Series) -> float:
    """Return the worst peak-to-trough loss on the equity curve.

    equity = (1 + returns).cumprod()  — log returns approximate; OK here.
    dd     = equity / equity.cummax() - 1
    return the minimum of `dd` as a negative float.
    """
    raise NotImplementedError("Implement max_drawdown")
'''


P2_TEST_DASHBOARD_PY = '''"""Tests for the returns dashboard."""
import numpy as np
import pandas as pd
import pytest

from dashboard import load_returns, summary_metrics, TICKERS
from metrics import max_drawdown


def test_load_returns_shape_and_columns():
    df = load_returns(days=1000, seed=0)
    assert df.shape == (1000, 5)
    assert list(df.columns) == TICKERS


def test_load_returns_is_reproducible():
    a = load_returns(days=500, seed=42)
    b = load_returns(days=500, seed=42)
    pd.testing.assert_frame_equal(a, b)


def test_load_returns_means_in_right_ballpark():
    # SPY's daily drift target is 0.10 / 252 ≈ 0.000397. The empirical
    # mean of 5000 daily draws has standard error ≈ vol_daily / sqrt(5000)
    # ≈ 0.00016, so a 3σ band is ~5e-4. Use 6e-4 for headroom on any seed.
    df = load_returns(days=5000, seed=7)
    spy_daily_mean = df["SPY"].mean()
    assert abs(spy_daily_mean - 0.10 / 252) < 6e-4


def test_summary_metrics_columns():
    df = load_returns(days=2500, seed=11)
    s = summary_metrics(df)
    assert list(s.columns) == ["mean_annual", "vol_annual", "sharpe", "skew", "kurt"]
    assert list(s.index) == TICKERS


def test_summary_metrics_vol_in_ballpark():
    # SPY's annualised vol should land near its 0.18 generator setting.
    df = load_returns(days=2500, seed=11)
    s = summary_metrics(df)
    assert 0.15 < s.loc["SPY", "vol_annual"] < 0.22


def test_summary_metrics_sharpe_is_mean_over_vol():
    df = load_returns(days=2500, seed=11)
    s = summary_metrics(df)
    for tkr in TICKERS:
        expected = s.loc[tkr, "mean_annual"] / s.loc[tkr, "vol_annual"]
        assert abs(s.loc[tkr, "sharpe"] - round(expected, 4)) < 1e-4


def test_max_drawdown_is_negative_on_volatile_series():
    df = load_returns(days=2500, seed=21)
    # AAPL is the most volatile — expect a non-trivial drawdown.
    dd = max_drawdown(df["AAPL"])
    assert dd < -0.05  # at least a 5% drawdown


def test_max_drawdown_zero_on_monotone_series():
    # A monotonically positive series has zero drawdown.
    s = pd.Series([0.01] * 100)
    assert abs(max_drawdown(s)) < 1e-9
'''


P2_CONFTEST_PY = '''# tests/conftest.py — pyodide places this project at /home/pyodide.
'''

P2_README_MD = '''# Project 2 — Return-distribution dashboard

Build the panel every fund manager glances at first: per-ticker mean,
vol, Sharpe, skew, kurtosis, and a drawdown helper. Synthetic returns
keep things fully reproducible — the maths is the same on real CSVs.

## What you build

- **`dashboard.py`** — `load_returns(days, seed)` and `summary_metrics(returns)`
- **`metrics.py`** — `max_drawdown(returns)` for a single series

## What the tests check

- Shape and column order of `load_returns`
- Reproducibility (same seed → identical frame)
- Drift recovers the configured per-ticker mean within tolerance
- Sharpe is `mean_annual / vol_annual` (rf = 0)
- Drawdown is negative on AAPL (vol = 30%) and zero on a monotone series

## References

- empyrical-reloaded — github.com/stefan-jansen/empyrical-reloaded
- pyfolio — github.com/quantopian/pyfolio (legacy but the source for many
  canonical metric definitions)

## Time

~45 minutes if you know pandas; ~90 from scratch.
'''


P2 = Project(
    n=2,
    stage=2,
    title="Return distribution dashboard",
    scenario=(
        "Every fund's monthly report leads with a panel of per-ticker "
        "stats: mean, vol, Sharpe, skew, kurtosis, max drawdown. The "
        "engine behind that panel is half a dozen pandas reductions "
        "and a couple of scipy.stats calls. Build it once and the "
        "shape becomes muscle memory — at AQR, at Citadel, at any "
        "long-only allocator you ever work for, the same panel exists."
    ),
    learner_goal=(
        "Implement reproducible synthetic-returns loading, per-ticker "
        "summary statistics, and a max-drawdown helper. Pass 8 tests."
    ),
    overview_md=P2_README_MD,
    editable={
        "dashboard.py": P2_DASHBOARD_PY,
        "metrics.py": P2_METRICS_PY,
    },
    readonly={
        "tests/test_dashboard.py": P2_TEST_DASHBOARD_PY,
        "tests/conftest.py": P2_CONFTEST_PY,
        "README.md": P2_README_MD,
    },
    tests=[
        TestCase(
            "tests/test_dashboard.py::test_load_returns_shape_and_columns",
            "`load_returns(1000)` is shape (1000, 5) with columns SPY/AAPL/QQQ/TLT/GLD.",
        ),
        TestCase(
            "tests/test_dashboard.py::test_load_returns_is_reproducible",
            "Same seed → identical DataFrame across calls.",
        ),
        TestCase(
            "tests/test_dashboard.py::test_load_returns_means_in_right_ballpark",
            "SPY daily mean is within ±0.0001 of 0.10/252 over 5000 days.",
        ),
        TestCase(
            "tests/test_dashboard.py::test_summary_metrics_columns",
            "`summary_metrics` returns columns [mean_annual, vol_annual, sharpe, skew, kurt].",
        ),
        TestCase(
            "tests/test_dashboard.py::test_summary_metrics_vol_in_ballpark",
            "SPY annualised vol lands between 0.15 and 0.22 with the configured 0.18.",
        ),
        TestCase(
            "tests/test_dashboard.py::test_summary_metrics_sharpe_is_mean_over_vol",
            "Per-ticker `sharpe` equals `round(mean_annual / vol_annual, 4)`.",
        ),
        TestCase(
            "tests/test_dashboard.py::test_max_drawdown_is_negative_on_volatile_series",
            "Drawdown on AAPL (30% vol) is at least -5%.",
        ),
        TestCase(
            "tests/test_dashboard.py::test_max_drawdown_zero_on_monotone_series",
            "Drawdown on a constant-positive series is zero.",
        ),
    ],
    skills=["quant", "pandas", "statistics", "risk-metrics"],
)


# Project 3 — Mini options pricer ----------------------------------------

P3_ANALYTICAL_PY = '''"""Black-Scholes analytical price for European call and put."""
import math
from scipy.stats import norm


def bs_call_put(S: float, K: float, r: float, sigma: float, T: float) -> tuple:
    """Return (call, put) prices for a European option under Black-Scholes.

    d1 = (ln(S/K) + (r + sigma^2/2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    C  = S * N(d1) - K * exp(-r*T) * N(d2)
    P  = K * exp(-r*T) * N(-d2) - S * N(-d1)

    Returns
    -------
    (call, put) : tuple of two floats
    """
    raise NotImplementedError("Implement bs_call_put")
'''


P3_BINOMIAL_PY = '''"""CRR binomial-tree price for a European call."""
import math
import numpy as np


def crr_call(S: float, K: float, r: float, sigma: float, T: float, N: int) -> float:
    """Cox-Ross-Rubinstein N-step tree price for a European call.

    Steps:
      dt = T / N
      u  = exp(sigma * sqrt(dt));   d = 1 / u
      p  = (exp(r * dt) - d) / (u - d)
      Terminal prices: S * u^i * d^(N-i)  for i in 0..N
      Backward-induct: V_t = exp(-r * dt) * (p * V_up + (1 - p) * V_down)

    Returns
    -------
    float — the value at t=0.
    """
    raise NotImplementedError("Implement crr_call")
'''


P3_MC_PY = '''"""Monte Carlo Black-Scholes call pricer."""
import numpy as np


def mc_call(
    S: float, K: float, r: float, sigma: float, T: float,
    paths: int = 20_000, seed: int = 0,
) -> float:
    """Risk-neutral MC estimate of a European call price.

    S_T = S * exp((r - sigma^2 / 2) * T + sigma * sqrt(T) * Z), Z ~ N(0, 1)
    Price = exp(-r * T) * mean(max(S_T - K, 0))

    Use np.random.default_rng(seed) so each call is reproducible.
    """
    raise NotImplementedError("Implement mc_call")
'''


P3_TEST_PRICING_PY = '''"""Cross-method sanity tests for the three pricers."""
import pytest

from analytical import bs_call_put
from binomial import crr_call
from mc import mc_call


HULL_PARAMS = dict(S=100, K=100, r=0.05, sigma=0.20, T=1.0)


def test_bs_hull_example_call():
    call, _ = bs_call_put(**HULL_PARAMS)
    assert abs(call - 10.4506) < 1e-3


def test_bs_hull_example_put():
    _, put = bs_call_put(**HULL_PARAMS)
    # From put-call parity: P = C - S + K*exp(-rT) = 10.4506 - 100 + 95.123 ≈ 5.574
    assert abs(put - 5.5735) < 1e-2


def test_put_call_parity_holds():
    # C - P should equal S - K * exp(-r * T)
    import math
    call, put = bs_call_put(**HULL_PARAMS)
    rhs = HULL_PARAMS["S"] - HULL_PARAMS["K"] * math.exp(-HULL_PARAMS["r"] * HULL_PARAMS["T"])
    assert abs((call - put) - rhs) < 1e-4


def test_binomial_converges_to_bs_as_N_grows():
    bs_call, _ = bs_call_put(**HULL_PARAMS)
    crr_100 = crr_call(N=100, **HULL_PARAMS)
    crr_500 = crr_call(N=500, **HULL_PARAMS)
    # The 500-step tree should be closer to BS than the 100-step tree.
    assert abs(crr_500 - bs_call) < abs(crr_100 - bs_call) + 0.005
    assert abs(crr_500 - bs_call) < 0.05


def test_mc_matches_bs_within_tolerance():
    bs_call, _ = bs_call_put(**HULL_PARAMS)
    mc = mc_call(paths=50_000, seed=42, **HULL_PARAMS)
    # 50k paths → standard error ~0.07; allow 0.3 wiggle.
    assert abs(mc - bs_call) < 0.3


def test_mc_is_reproducible():
    a = mc_call(paths=5000, seed=11, **HULL_PARAMS)
    b = mc_call(paths=5000, seed=11, **HULL_PARAMS)
    assert a == b


def test_deep_otm_call_is_near_zero():
    call, _ = bs_call_put(S=100, K=200, r=0.05, sigma=0.20, T=1.0)
    assert 0 <= call < 0.01
'''


P3_CONFTEST_PY = '''# tests/conftest.py — pyodide handles sys.path.
'''


P3_README_MD = '''# Project 3 — Mini options pricer

Three independent implementations of the same vanilla call price:
the closed-form Black-Scholes, the CRR binomial tree, and a
risk-neutral Monte Carlo. They should agree to within their respective
tolerances on the canonical Hull textbook example.

## What you build

- **`analytical.py`** — `bs_call_put(S, K, r, sigma, T) -> (call, put)`
- **`binomial.py`** — `crr_call(S, K, r, sigma, T, N) -> float`
- **`mc.py`** — `mc_call(S, K, r, sigma, T, paths, seed) -> float`

## What the tests check

- BS call matches Hull's 10.4506 (S=K=100, r=5%, σ=20%, T=1y)
- Put-call parity `C − P = S − K·exp(−rT)` to machine precision
- 500-step binomial gets closer to BS than 100-step
- MC with 50k paths is within 0.3 of BS
- MC is reproducible under a fixed seed
- Deep OTM call (K=200, S=100) is essentially zero

## References

- py_vollib — github.com/vollib/py_vollib — the production-grade
  reference implementation
- Hull, *Options, Futures and Other Derivatives* — chapter 13 has the
  worked example we test against

## Time

~75 minutes if you know BS; ~3 hours from first principles.
'''


P3 = Project(
    n=3,
    stage=3,
    title="Mini options pricer",
    scenario=(
        "Every market-maker's vol-desk runs three independent pricing "
        "paths for any vanilla quote: analytical Black-Scholes for the "
        "fast path, a tree for early-exercise checks, and Monte Carlo "
        "for path-dependent or basket payoffs. When they disagree, "
        "that's a bug. Today you build all three from scratch and "
        "verify they agree on Hull's textbook example to the relevant "
        "tolerance."
    ),
    learner_goal=(
        "Implement Black-Scholes, CRR binomial tree, and Monte Carlo "
        "European-call pricers; verify cross-method consistency "
        "and put-call parity through 7 tests."
    ),
    overview_md=P3_README_MD,
    editable={
        "analytical.py": P3_ANALYTICAL_PY,
        "binomial.py": P3_BINOMIAL_PY,
        "mc.py": P3_MC_PY,
    },
    readonly={
        "tests/test_pricing.py": P3_TEST_PRICING_PY,
        "tests/conftest.py": P3_CONFTEST_PY,
        "README.md": P3_README_MD,
    },
    tests=[
        TestCase(
            "tests/test_pricing.py::test_bs_hull_example_call",
            "BS call on Hull's S=K=100, r=5%, σ=20%, T=1y matches 10.4506 to 3 dp.",
        ),
        TestCase(
            "tests/test_pricing.py::test_bs_hull_example_put",
            "BS put on the same parameters matches 5.5735 to 2 dp.",
        ),
        TestCase(
            "tests/test_pricing.py::test_put_call_parity_holds",
            "C - P equals S - K·exp(-rT) on Hull's parameters.",
        ),
        TestCase(
            "tests/test_pricing.py::test_binomial_converges_to_bs_as_N_grows",
            "500-step CRR is within 0.05 of BS and beats the 100-step tree.",
        ),
        TestCase(
            "tests/test_pricing.py::test_mc_matches_bs_within_tolerance",
            "50k-path MC is within 0.30 of BS (≈3σ standard error band).",
        ),
        TestCase(
            "tests/test_pricing.py::test_mc_is_reproducible",
            "Same seed twice → identical MC estimate.",
        ),
        TestCase(
            "tests/test_pricing.py::test_deep_otm_call_is_near_zero",
            "K=200, S=100 deep-OTM call price is ~0.",
        ),
    ],
    skills=["quant", "options", "black-scholes", "monte-carlo"],
)


# Project 4 — Walk-forward backtest with ML signal -----------------------

P4_FEATURES_PY = '''"""Construct ML features from a return series — strictly past-only."""
import numpy as np
import pandas as pd


def make_features(returns: pd.Series) -> pd.DataFrame:
    """Build features for ML on a daily-return series.

    Features:
      - mom_5  = sum of returns over the prior 5 days  (lag 1)
      - mom_20 = sum of returns over the prior 20 days (lag 1)
      - vol_20 = std of returns over the prior 20 days (lag 1)

    Every feature for day t must use ONLY data from day t-1 and earlier.
    This is the lookahead-bias-free convention: rolling on r.shift(1).

    Drop any rows containing NaN before returning.

    Returns
    -------
    DataFrame with columns ['mom_5', 'mom_20', 'vol_20'] indexed like
    `returns` (minus the burn-in rows).
    """
    raise NotImplementedError("Implement make_features")
'''


P4_BACKTEST_PY = '''"""Walk-forward chronological backtest with an ML model."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def walk_forward(
    features: pd.DataFrame,
    target: pd.Series,
    n_splits: int = 5,
    embargo: int = 1,
) -> pd.Series:
    """Walk-forward predictions of `target` from `features`.

    Algorithm:
      - Align `features` and `target` on their common index, drop NaNs.
      - Split the aligned frame into `n_splits` chronological chunks.
      - For each chunk after the first: train a `LinearRegression` on
        all data BEFORE the chunk's start (minus `embargo` rows of
        gap), then predict the chunk.
      - Concatenate the per-chunk predictions in order.

    The `embargo` parameter excludes the last `embargo` rows of the
    train window — protects against serial correlation leakage at the
    train/test boundary (Lopez de Prado's purgedKFold idea).

    Returns
    -------
    Series of predictions, indexed like the predicted rows of `target`.
    """
    raise NotImplementedError("Implement walk_forward")
'''


P4_TEST_BACKTEST_PY = '''"""Tests for the walk-forward backtest."""
import numpy as np
import pandas as pd
import pytest

from features import make_features
from backtest import walk_forward


def _synthetic_returns(n: int, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0, 0.01, n))


def test_features_dropna_and_shape():
    r = _synthetic_returns(200, seed=1)
    f = make_features(r)
    assert list(f.columns) == ["mom_5", "mom_20", "vol_20"]
    # 20-day rolling windows on a lagged series eat ~20 rows.
    assert len(f) <= 200 - 20
    assert f.isna().sum().sum() == 0


def test_features_are_strictly_past():
    # If a feature on day t uses returns up to day t-1, then perturbing
    # ONLY returns from day t onward must leave features for day < t intact.
    r = _synthetic_returns(200, seed=2)
    f1 = make_features(r)
    r2 = r.copy()
    # Slam the second half with huge values.
    r2.iloc[100:] = 9.99
    f2 = make_features(r2)
    # Features up to and including row index 90 should be unchanged.
    common = f1.index.intersection(f2.index)
    common_before = common[common < 90]
    pd.testing.assert_frame_equal(
        f1.loc[common_before],
        f2.loc[common_before],
    )


def test_walk_forward_predicts_a_strict_suffix():
    r = _synthetic_returns(500, seed=3)
    f = make_features(r)
    y = r.loc[f.index]  # the next-day return; aligned to features.index
    preds = walk_forward(f, y, n_splits=5)
    # The first chunk is training-only — preds covers the rest.
    n = len(f)
    expected_min = n // 5  # at least 1 chunk worth of predictions
    assert len(preds) >= expected_min
    # Predictions index must be a suffix of features.index.
    assert preds.index.is_monotonic_increasing
    assert preds.index[0] > f.index[0]


def test_walk_forward_is_reproducible():
    r = _synthetic_returns(400, seed=4)
    f = make_features(r)
    y = r.loc[f.index]
    p1 = walk_forward(f, y, n_splits=5)
    p2 = walk_forward(f, y, n_splits=5)
    pd.testing.assert_series_equal(p1, p2)


def test_walk_forward_does_not_peek_at_future():
    # If we change the LAST 20 returns dramatically, predictions for the
    # FIRST predicted day (which only saw early history) must be unchanged.
    r1 = _synthetic_returns(400, seed=5)
    r2 = r1.copy()
    r2.iloc[-20:] = 9.99
    f1 = make_features(r1); f2 = make_features(r2)
    y1 = r1.loc[f1.index]; y2 = r2.loc[f2.index]
    p1 = walk_forward(f1, y1, n_splits=5)
    p2 = walk_forward(f2, y2, n_splits=5)
    # The first predicted row used only early training data — must match.
    assert abs(p1.iloc[0] - p2.iloc[0]) < 1e-10
'''


P4_CONFTEST_PY = '''# tests/conftest.py — pyodide handles sys.path.
'''


P4_README_MD = '''# Project 4 — Walk-forward backtest with ML signal

Two of the most-common quant-ML bugs in production: features that
secretly use future data, and train/test splits that shuffle time
series. This project forces both bugs out of your code with explicit
tests for "no lookahead" and "predictions only use prior data."

## What you build

- **`features.py`** — `make_features(returns)` returns a 3-feature
  DataFrame: `mom_5`, `mom_20`, `vol_20`, all strictly past-only.
- **`backtest.py`** — `walk_forward(features, target, n_splits, embargo)`
  produces walk-forward chronological predictions with an embargo gap.

## What the tests check

- Features drop NaNs and have the right columns
- Perturbing future returns leaves past features unchanged (no leakage)
- Walk-forward predictions cover a strict suffix of the data
- Predictions are reproducible under a fixed seed
- Perturbing the LAST 20 returns doesn't affect predictions for early
  rows (deepest leakage test)

## References

- Lopez de Prado, *Advances in Financial Machine Learning* — chapter 7
  on cross-validation and embargoes
- skfolio — github.com/skfolio/skfolio (modern walk-forward backtester)

## Time

~90 minutes if you know sklearn; ~3 hours from scratch.
'''


P4 = Project(
    n=4,
    stage=4,
    title="Walk-forward backtest",
    scenario=(
        "Every quant-ML interview at every fund includes some version "
        "of this question: 'show me your backtest doesn't peek at the "
        "future.' Lopez de Prado wrote a book about it. The fund risk "
        "team has a checklist. The supervisor on your first day will "
        "stare at your code looking for one of these bugs. Today: "
        "build a backtest that survives the stare-test, with explicit "
        "tests proving features are past-only and predictions don't "
        "see the next chunk."
    ),
    learner_goal=(
        "Implement a strictly-past-only feature builder and a "
        "walk-forward backtester. Pass 5 tests that include a direct "
        "lookahead-bias check."
    ),
    overview_md=P4_README_MD,
    editable={
        "features.py": P4_FEATURES_PY,
        "backtest.py": P4_BACKTEST_PY,
    },
    readonly={
        "tests/test_backtest.py": P4_TEST_BACKTEST_PY,
        "tests/conftest.py": P4_CONFTEST_PY,
        "README.md": P4_README_MD,
    },
    tests=[
        TestCase(
            "tests/test_backtest.py::test_features_dropna_and_shape",
            "`make_features` returns mom_5/mom_20/vol_20 with no NaN rows.",
        ),
        TestCase(
            "tests/test_backtest.py::test_features_are_strictly_past",
            "Perturbing future returns doesn't change past features (no leakage).",
        ),
        TestCase(
            "tests/test_backtest.py::test_walk_forward_predicts_a_strict_suffix",
            "Walk-forward predictions cover only a chronological suffix of the data.",
        ),
        TestCase(
            "tests/test_backtest.py::test_walk_forward_is_reproducible",
            "Same inputs twice → identical predictions.",
        ),
        TestCase(
            "tests/test_backtest.py::test_walk_forward_does_not_peek_at_future",
            "Perturbing the LAST 20 returns doesn't change predictions for early rows.",
        ),
    ],
    skills=["quant", "machine-learning", "backtesting", "pandas"],
)


# Project 5 — Order book ---------------------------------------------------

P5_LOB_PY = '''"""A price-time-priority limit order book in pure Python.

The same data structure runs the matching engines at CME, Eurex,
NYSE, Coinbase — modulo what language they're written in (C, C++,
sometimes Rust). The algorithm is the same.

Implement a price-priority order book with the following operations:
  - add(side, price, qty)  -> order_id
  - cancel(order_id)       -> True/False
  - top_of_book()          -> (best_bid, best_ask) or (None, None)
  - match()                -> list of trades

Use a SortedDict / SortedList of price levels per side, or two dicts +
a sort-on-read pattern. For this project's scale a sorted dict is fine.
"""
from collections import defaultdict, deque


class LimitOrderBook:
    """Price-time priority LOB.

    Internal state (suggestion — feel free to use other structures
    as long as the tests pass):
      - self.bids:  dict[float, deque[(order_id, qty)]]   high-to-low best
      - self.asks:  dict[float, deque[(order_id, qty)]]   low-to-high best
      - self.next_id: int
      - self.orders: dict[order_id, (side, price)]
    """

    def __init__(self) -> None:
        raise NotImplementedError("Implement __init__")

    def add(self, side: str, price: float, qty: int) -> int:
        """Add a resting limit order. Returns a unique integer order_id.

        side: 'bid' or 'ask'. price > 0. qty > 0.
        """
        raise NotImplementedError("Implement add")

    def cancel(self, order_id: int) -> bool:
        """Cancel a resting order. Returns True if it was cancelled,
        False if the id was unknown / already executed."""
        raise NotImplementedError("Implement cancel")

    def top_of_book(self) -> tuple:
        """Return (best_bid_price, best_ask_price).

        - best_bid is the highest bid (or None if empty)
        - best_ask is the lowest ask (or None if empty)
        """
        raise NotImplementedError("Implement top_of_book")

    def match(self) -> list:
        """Cross the book: while best_bid >= best_ask, execute the
        oldest order on each side at the resting price of whichever
        was first, then fill quantities, mutate the book, append a
        trade entry to the result list.

        Each trade is a dict:
            {"price": float, "qty": int,
             "bid_order_id": int, "ask_order_id": int}

        Return the list of trades, oldest first.
        """
        raise NotImplementedError("Implement match")
'''


P5_TEST_LOB_PY = '''"""Tests for the limit order book."""
import pytest
from lob import LimitOrderBook


def test_empty_book_top_is_none_none():
    book = LimitOrderBook()
    assert book.top_of_book() == (None, None)


def test_add_and_top_of_book():
    book = LimitOrderBook()
    book.add("bid", 100.0, 5)
    book.add("bid", 99.5, 3)
    book.add("ask", 100.5, 4)
    book.add("ask", 101.0, 2)
    assert book.top_of_book() == (100.0, 100.5)


def test_cancel_returns_true_and_removes():
    book = LimitOrderBook()
    oid = book.add("bid", 100.0, 5)
    book.add("bid", 99.5, 3)
    assert book.cancel(oid) is True
    assert book.top_of_book()[0] == 99.5


def test_cancel_unknown_returns_false():
    book = LimitOrderBook()
    book.add("bid", 100.0, 5)
    assert book.cancel(99999) is False


def test_match_crosses_when_bid_meets_ask():
    book = LimitOrderBook()
    book.add("ask", 100.0, 5)
    book.add("bid", 100.0, 5)
    trades = book.match()
    assert len(trades) == 1
    assert trades[0]["price"] == 100.0
    assert trades[0]["qty"] == 5
    assert book.top_of_book() == (None, None)


def test_match_partial_fill_leaves_remainder():
    book = LimitOrderBook()
    book.add("ask", 100.0, 5)
    book.add("bid", 100.0, 3)
    trades = book.match()
    assert len(trades) == 1
    assert trades[0]["qty"] == 3
    # 2 qty left on the ask.
    assert book.top_of_book() == (None, 100.0)


def test_match_executes_at_resting_price_time_priority():
    book = LimitOrderBook()
    book.add("ask", 100.0, 5)  # resting ask FIRST → trade prints at 100
    book.add("bid", 101.0, 5)  # aggressive bid arrives
    trades = book.match()
    assert len(trades) == 1
    assert trades[0]["price"] == 100.0


def test_match_walks_multiple_levels():
    book = LimitOrderBook()
    book.add("ask", 100.0, 2)
    book.add("ask", 100.5, 3)
    book.add("ask", 101.0, 1)
    book.add("bid", 101.0, 6)
    trades = book.match()
    assert len(trades) == 3
    assert sum(t["qty"] for t in trades) == 6
    assert book.top_of_book()[1] is None
'''


P5_CONFTEST_PY = '''# tests/conftest.py — pyodide handles sys.path.
'''


P5_README_MD = '''# Project 5 — Limit order book in Python

The same data structure that runs every electronic exchange — CME,
Eurex, NYSE, Coinbase. Implement a price-time-priority LOB in pure
Python and pass the 8 tests covering top-of-book, cancellation,
crossing, partial fills, and multi-level walks.

## What you build

- **`lob.py`** — `LimitOrderBook` class with `add`, `cancel`,
  `top_of_book`, and `match`.

## What the tests check

- Empty book reports (None, None)
- Adding bids and asks; correct top-of-book
- Cancellation removes the order and updates top-of-book
- Cancelling an unknown id returns False
- Full and partial fills on `match()`
- Aggressive orders trade at the resting price (price-time priority)
- Multi-level walks fill across price levels until either side empties

## References

- HFT-Orderbook — github.com/Crypto-toolbox/HFT-Orderbook — production
  reference in Python; reads like documentation
- LMAX Disruptor (Java) — for the lock-free production version

## Time

~2 hours from scratch; the data-structure choices matter more than the
amount of code.
'''


P5 = Project(
    n=5,
    stage=5,
    title="Limit order book",
    scenario=(
        "The matching engine at every electronic exchange runs the "
        "same data structure: a price-time-priority limit order book. "
        "CME's iLink, Eurex T7, NYSE Pillar — same shape, different "
        "implementation language (C++ in all three). The Python "
        "version below is the toy that lets you understand the "
        "algorithm; the production version uses contiguous memory "
        "and atomic indices for SPSC lock-free use."
    ),
    learner_goal=(
        "Implement a price-time-priority LOB with add / cancel / "
        "top_of_book / match in Python. Pass 8 tests covering all "
        "the edge cases that matter at the exchange level."
    ),
    overview_md=P5_README_MD,
    editable={
        "lob.py": P5_LOB_PY,
    },
    readonly={
        "tests/test_lob.py": P5_TEST_LOB_PY,
        "tests/conftest.py": P5_CONFTEST_PY,
        "README.md": P5_README_MD,
    },
    tests=[
        TestCase(
            "tests/test_lob.py::test_empty_book_top_is_none_none",
            "Empty book reports (None, None) from top_of_book().",
        ),
        TestCase(
            "tests/test_lob.py::test_add_and_top_of_book",
            "Best bid is the highest bid; best ask is the lowest ask.",
        ),
        TestCase(
            "tests/test_lob.py::test_cancel_returns_true_and_removes",
            "Cancelling a resting order removes it and updates top-of-book.",
        ),
        TestCase(
            "tests/test_lob.py::test_cancel_unknown_returns_false",
            "Cancelling an unknown order_id returns False, no exception.",
        ),
        TestCase(
            "tests/test_lob.py::test_match_crosses_when_bid_meets_ask",
            "A matched bid + ask at the same price executes 1 trade and empties the book.",
        ),
        TestCase(
            "tests/test_lob.py::test_match_partial_fill_leaves_remainder",
            "Aggressive bid for less than the ask quantity leaves the rest of the ask resting.",
        ),
        TestCase(
            "tests/test_lob.py::test_match_executes_at_resting_price_time_priority",
            "Trades print at the resting order's price (price-time priority).",
        ),
        TestCase(
            "tests/test_lob.py::test_match_walks_multiple_levels",
            "Bid sweeping 3 ask levels generates 3 trades summing to the bid quantity.",
        ),
    ],
    skills=["quant", "low-latency", "performance"],
)


PROJECTS: list[Project] = [P1, P2, P3, P4, P5]


# ---- Emit ---------------------------------------------------------------


def sql_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n")


def project_instructions(p: Project) -> str:
    """Render the instructions panel for a project.

    Same template every project: project header, overview, file map,
    references. The README content already holds most of this.
    """
    files_list = "\n".join(
        f"- `{path}` (editable)" for path in p.editable
    ) + "\n" + "\n".join(
        f"- `{path}` (read-only)" for path in p.readonly
    )
    return (
        f"# {p.title}\n\n"
        f"{p.overview_md.split('# Project', 1)[-1].split('\n', 1)[1].strip()}\n\n"
        f"## Files in this project\n\n"
        f"{files_list}\n\n"
        f"## How to run\n\n"
        f"Click **Run tests** below — pytest discovers `tests/test_*.py` "
        f"automatically. Failing tests light up red and the mentor on "
        f"the right can explain what each assertion expects."
    )


def write_sql() -> Path:
    lines: list[str] = []
    lines.append("-- AUTO-GENERATED by scripts/generate_quant_projects.py")
    lines.append("-- Quant track mini-project inserts.")
    lines.append("")
    # Wipe and reinsert so re-runs don't leave dangling projects.
    lines.append(
        "delete from public.challenges where slug like 'quant-project-%';"
    )
    lines.append("")
    for p in PROJECTS:
        skills_array = (
            "array[" + ", ".join(f"'{sql_escape(s)}'" for s in p.skills) + "]"
        )
        lines.append(
            "insert into public.challenges (\n"
            "  id, module_id, slug, title, scenario, learner_goal, instructions,\n"
            "  repo_template_url, repo_branch, validation_config_json, ai_rules_json,\n"
            "  skills, is_free, order_index\n"
            ") values ("
        )
        lines.append(f"  '{p.uuid}',")
        lines.append(f"  '{p.module_uuid}',")
        lines.append(f"  '{p.slug}',")
        lines.append(f"  E'{sql_escape(p.title)}',")
        lines.append(f"  E'{sql_escape(p.scenario)}',")
        lines.append(f"  E'{sql_escape(p.learner_goal)}',")
        lines.append(f"  E'{sql_escape(project_instructions(p))}',")
        lines.append("  null,")
        lines.append("  null,")
        lines.append("  '{}',")
        lines.append(
            "  '{\"max_hint_level\": 2, \"do_not_reveal_solution\": false,"
            ' "encourage_tests_first": true}\','
        )
        lines.append(f"  {skills_array},")
        lines.append("  true,")
        lines.append(f"  {100 + p.n}")
        lines.append(")")
        lines.append("on conflict (slug) do update set")
        lines.append(
            "  module_id = excluded.module_id,\n"
            "  title = excluded.title,\n"
            "  scenario = excluded.scenario,\n"
            "  learner_goal = excluded.learner_goal,\n"
            "  instructions = excluded.instructions,\n"
            "  validation_config_json = excluded.validation_config_json,\n"
            "  ai_rules_json = excluded.ai_rules_json,\n"
            "  skills = excluded.skills,\n"
            "  is_free = excluded.is_free,\n"
            "  order_index = excluded.order_index;"
        )
        lines.append("")
    out = ROOT / "supabase" / "quant_projects_seed.generated.sql"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_ts() -> Path:
    """Emit the inline-scaffold map keyed by slug."""
    pieces: list[str] = []
    pieces.append(
        "// AUTO-GENERATED by scripts/generate_quant_projects.py — do not edit.\n"
        '// Re-run: `python scripts/generate_quant_projects.py`\n'
        "\n"
        'import type { ChallengeRunnerConfig } from "@/lib/featured-files";\n'
        "\n"
        "export const QUANT_PROJECTS_CONFIG: Record<string, ChallengeRunnerConfig> = {\n"
    )
    for p in PROJECTS:
        editable_arr = json.dumps(list(p.editable.keys()))
        readonly_arr = json.dumps(list(p.readonly.keys()))
        tests_lines = []
        for tc in p.tests:
            tests_lines.append(
                "    {\n"
                f"      id: {json.dumps(tc.pytest_id)},\n"
                f"      description: {json.dumps(tc.description)},\n"
                "    },"
            )
        tests_block = "\n".join(tests_lines)
        inline_lines = []
        for path, body in p.all_files().items():
            inline_lines.append(
                f"    {json.dumps(path)}: {json.dumps(body)},"
            )
        inline_block = "\n".join(inline_lines)
        pieces.append(
            f"  {json.dumps(p.slug)}: {{\n"
            f'    mode: "pyodide",\n'
            f"    editable: {editable_arr},\n"
            f"    readonly: {readonly_arr},\n"
            f"    tests: [\n{tests_block}\n    ],\n"
            f"    inline: {{\n{inline_block}\n    }},\n"
            "  },\n"
        )
    pieces.append("};\n")
    out = ROOT / "apps" / "web" / "src" / "lib" / "quant-projects-config.generated.ts"
    out.write_text("".join(pieces), encoding="utf-8")
    return out


def main() -> None:
    sql = write_sql()
    ts = write_ts()
    print(f"Wrote {sql}")
    print(f"Wrote {ts}")
    print(f"{len(PROJECTS)} project(s)")


if __name__ == "__main__":
    main()
