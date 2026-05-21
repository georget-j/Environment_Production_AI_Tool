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


# Lessons go here. Phase X.2 fills this in.
LESSONS: list[Lesson] = []


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
