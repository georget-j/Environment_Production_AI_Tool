"""Sanity-check the quant lessons before they ship to learners.

Two distinct check modes, applied per lesson:

- predict / fillblank / matplot: run the example_code (or `code` for
  predict) and compare stdout to `expected_stdout` / `_contains`.
- debug / skeleton: write a tiny pytest project (solution.py +
  tests/test_solution.py) and run pytest twice — first against the
  shipped editable_template (expect failure: bug trips for debug, or
  NotImplementedError trips for skeleton), then against the reference
  solution (expect pass).

cscript / cwasm lessons run in browser-only runtimes (picoc-js / WASM)
and are skipped here.

    python scripts/verify_quant_outputs.py
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
import traceback
from contextlib import redirect_stdout

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_quant import LESSONS  # noqa: E402

# When Pyodide runs lessons, /data/quant/<slug>.csv is mounted via the
# worker's ensureDataset. Locally there's no such mount, so we rewrite
# the URL to the on-disk file relative to the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "apps" / "web" / "public" / "data" / "quant"


def rewrite_data_paths(code: str) -> str:
    """Replace /data/quant/foo.csv with the absolute local path."""
    return code.replace("/data/quant/", f"{DATASET_DIR}/")


def normalise(s: str) -> str:
    return s.strip()


def run_example(code: str) -> tuple[str, str | None]:
    """Run a Python snippet and return (stdout, error)."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            exec(compile(code, "<lesson>", "exec"), {"__name__": "__main__"})
        return buf.getvalue(), None
    except Exception:
        return buf.getvalue(), traceback.format_exc(limit=2)


def verify_pytest_lesson(lesson) -> tuple[bool, str]:
    """For debug/skeleton/apifetch lessons, write a temp pytest project and
    assert that the editable_template fails AND the reference_solution
    passes. For apifetch, also mount the readonly mock_api.py module."""
    with tempfile.TemporaryDirectory(prefix=f"qverify_{lesson.slug}_") as raw:
        d = Path(raw)
        (d / "tests").mkdir(parents=True, exist_ok=True)
        (d / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (d / "tests" / "test_solution.py").write_text(
            lesson.tests_py, encoding="utf-8"
        )
        if lesson.mode == "apifetch":
            (d / "mock_api.py").write_text(
                lesson.mock_api_py, encoding="utf-8"
            )
        for filename, content in lesson.extra_readonly.items():
            full_path = d / filename
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        def run() -> int:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(d)],
                capture_output=True,
                text=True,
                cwd=str(d),
            )
            return res.returncode

        # Editable should NOT pass — proves the bug/skeleton genuinely trips.
        (d / "solution.py").write_text(
            lesson.editable_template, encoding="utf-8"
        )
        if run() == 0:
            return False, "editable_template passed all tests — bug doesn't trip"

        # Reference solution must pass — proves tests are correctly authored.
        (d / "solution.py").write_text(
            lesson.reference_solution, encoding="utf-8"
        )
        if run() != 0:
            return False, "reference_solution did not pass all tests"

    return True, "ok"


def main() -> int:
    ok = 0
    failed = 0
    for lesson in LESSONS:
        if lesson.mode in ("cscript", "cwasm"):
            # Browser-only runtimes; skip here.
            continue
        if lesson.mode in ("debug", "skeleton", "apifetch"):
            success, message = verify_pytest_lesson(lesson)
            if success:
                ok += 1
            else:
                print(f"  ✗ {lesson.slug}  ({lesson.mode}): {message}")
                failed += 1
            continue
        # predict: the LEARNER sees `code` and predicts its output.
        # fillblank / matplot: `example_code` is the filled-in version.
        runnable = lesson.code if lesson.mode == "predict" else lesson.example_code
        runnable = rewrite_data_paths(runnable)
        stdout, err = run_example(runnable)
        expected = lesson.expected_stdout
        if err:
            print(f"  ✗ {lesson.slug}  PYTHON ERROR\n{err.rstrip()}")
            failed += 1
            continue
        if normalise(stdout) == normalise(expected):
            ok += 1
        else:
            print(f"  ✗ {lesson.slug}")
            print(f"      expected: {expected!r}")
            print(f"      got     : {stdout.rstrip()!r}")
            failed += 1

    print(f"\n{ok} ok, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
