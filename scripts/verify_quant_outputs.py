"""Sanity-check the quant lessons by running each Python example and
comparing stdout to the lesson's `expected_stdout` / `expected_stdout_contains`.

Catches typos before they ship to learners. Skips cscript / cwasm lessons
(those have their own runtimes).

    python scripts/verify_quant_outputs.py
"""

from __future__ import annotations

import io
import sys
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


def main() -> int:
    ok = 0
    failed = 0
    for lesson in LESSONS:
        if lesson.mode not in ("predict", "fillblank", "matplot"):
            # cscript / cwasm — different runtimes; skip here.
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
