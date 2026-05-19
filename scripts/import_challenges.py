"""Import challenge YAML files into Supabase.

Usage:
  python scripts/import_challenges.py <yaml-glob>

Reads YAML files matching the glob (default `templates/*.yaml`), validates the
shape, and upserts into `public.challenges` using the Supabase service-role
key. Idempotent on `slug`.

Env vars required:
  SUPABASE_URL                  e.g. https://<project>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY     service-role key (NOT anon)
"""

from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

import httpx
import yaml

REQUIRED_FIELDS = ("id", "title", "track", "module", "scenario", "learner_goal")


def load_challenges(pattern: str) -> list[dict]:
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise SystemExit(f"No YAML files matched: {pattern}")
    out: list[dict] = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        missing = [f for f in REQUIRED_FIELDS if f not in doc]
        if missing:
            raise SystemExit(f"{p}: missing fields {missing}")
        out.append(_to_row(doc))
    return out


def _to_row(doc: dict) -> dict:
    repo = doc.get("repo", {}) or {}
    validation = doc.get("validation", {}) or {}
    return {
        "slug": doc["id"],
        "title": doc["title"],
        "scenario": doc["scenario"].strip(),
        "learner_goal": doc["learner_goal"].strip(),
        "instructions": (doc.get("instructions") or "").strip(),
        "repo_template_url": repo.get("template"),
        "repo_branch": repo.get("branch"),
        "validation_config_json": json.dumps({
            "tests": validation.get("tests", []),
            "lint": validation.get("lint", []),
            "visible_checks": doc.get("visible_checks", []),
            "hidden_checks": doc.get("hidden_checks", []),
        }),
        "ai_rules_json": json.dumps(doc.get("ai_rules", {})),
        "skills": doc.get("skills", []),
    }


def upsert(rows: list[dict]) -> None:
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    endpoint = f"{url}/rest/v1/challenges?on_conflict=slug"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(endpoint, headers=headers, content=json.dumps(rows))
        if resp.status_code >= 300:
            raise SystemExit(f"Upsert failed ({resp.status_code}): {resp.text}")
        print(f"Upserted {len(rows)} challenges")


def main(argv: list[str]) -> int:
    pattern = argv[1] if len(argv) > 1 else str(Path("templates") / "*.yaml")
    rows = load_challenges(pattern)
    if "SUPABASE_URL" not in os.environ:
        print("DRY RUN — set SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY to actually upsert.")
        print(json.dumps(rows, indent=2))
        return 0
    upsert(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
