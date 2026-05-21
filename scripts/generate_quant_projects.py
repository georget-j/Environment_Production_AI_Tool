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


PROJECTS: list[Project] = [P1]


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
