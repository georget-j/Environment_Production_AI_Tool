#!/usr/bin/env bash
# Boot the web + api together for local dev. Assumes pnpm install + venv are done.
set -euo pipefail

cd "$(dirname "$0")/.."

# Activate the api venv if it exists.
if [[ -f apps/api/.venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source apps/api/.venv/bin/activate
fi

trap 'kill 0' INT TERM EXIT

pnpm --filter web dev &
uvicorn app.main:app --reload --app-dir apps/api --host 0.0.0.0 --port 8000 &

wait
