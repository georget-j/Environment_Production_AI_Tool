"""Parse pasted CLI output for pass/fail signal.

MVP shortcut: the learner pastes pytest output and we regex it.
Upgrade #1 in the roadmap replaces this with GitHub Actions webhooks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# pytest summary forms we recognise:
#   "5 passed in 1.23s"
#   "5 passed, 2 failed in 1.23s"
#   "1 failed, 4 passed, 1 skipped in 1.23s"
#   "no tests ran in 0.01s"
_PASSED_RE = re.compile(r"(\d+)\s+passed", re.IGNORECASE)
_FAILED_RE = re.compile(r"(\d+)\s+(?:failed|errors?)", re.IGNORECASE)
_NO_TESTS_RE = re.compile(r"no tests ran", re.IGNORECASE)


@dataclass(frozen=True)
class TestSummary:
    passed: bool
    passed_count: int
    failed_count: int
    raw: str


def parse_pytest_output(text: str | None) -> TestSummary:
    if not text:
        return TestSummary(passed=False, passed_count=0, failed_count=0, raw="")
    stripped = text.strip()
    if _NO_TESTS_RE.search(stripped):
        return TestSummary(passed=False, passed_count=0, failed_count=0, raw=stripped)
    passed_match = _PASSED_RE.search(stripped)
    failed_match = _FAILED_RE.search(stripped)
    passed_n = int(passed_match.group(1)) if passed_match else 0
    failed_n = int(failed_match.group(1)) if failed_match else 0
    return TestSummary(
        passed=failed_n == 0 and passed_n > 0,
        passed_count=passed_n,
        failed_count=failed_n,
        raw=stripped,
    )
