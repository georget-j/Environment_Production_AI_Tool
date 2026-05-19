#!/usr/bin/env bash
# Smoke test: hits a deployed (or local) ProdReady AI stack.
#
# Usage:
#   API_BASE=http://localhost:8000 WEB_BASE=http://localhost:3000 ./scripts/smoke.sh
#
# Exits non-zero if any check fails.
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
WEB_BASE="${WEB_BASE:-http://localhost:3000}"

ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
fail() { printf "  \033[31m✗\033[0m %s\n" "$*"; exit 1; }

echo "Smoke testing API at $API_BASE"

# 1. /healthz
status=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/healthz")
[[ "$status" == "200" ]] && ok "GET /healthz returns 200" || fail "GET /healthz returned $status"

# 2. /api/me requires auth
status=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/api/me")
[[ "$status" == "401" ]] && ok "GET /api/me rejects unauthenticated" || fail "GET /api/me returned $status (expected 401)"

# 3. /api/tracks is public, returns array
body=$(curl -sS "$API_BASE/api/tracks")
echo "$body" | grep -q '"slug"' && ok "GET /api/tracks returns the seeded track" || fail "Track list missing slug field: $body"

# 4. /api/tracks/{slug} for the seeded slug
status=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/api/tracks/backend-production-python")
[[ "$status" == "200" ]] && ok "Backend Production track is published" || fail "Track detail returned $status"

# 5. Web marketing page is reachable
status=$(curl -sS -o /dev/null -w "%{http_code}" "$WEB_BASE")
[[ "$status" == "200" ]] && ok "Web marketing page renders" || fail "Web returned $status"

echo "All smoke checks passed."
