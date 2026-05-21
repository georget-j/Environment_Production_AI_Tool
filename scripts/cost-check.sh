#!/usr/bin/env bash
# Cost dashboard for ProdReady AI infra. Prints:
#   - Fly machine list + state (so you can spot runaway machine counts)
#   - Last 7 days of AI calls grouped by kind and user
#
# Requires: flyctl, psql.
# DATABASE_URL must point at the Supabase Postgres connection string.
# Run from anywhere in the repo.

set -euo pipefail

echo "── Fly machines (prodready-api) ──────────────────────────────"
flyctl status --app prodready-api 2>/dev/null \
  || echo "  flyctl not authed or app not reachable"

echo
echo "── AI call counts, last 7 days ──────────────────────────────"
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "  DATABASE_URL not set — skipping DB stats."
  echo "  Export it with the Supabase pooler URL, then re-run."
  exit 0
fi

psql "$DATABASE_URL" -P pager=off <<'SQL'
WITH usage AS (
  SELECT
    DATE_TRUNC('day', created_at) AS day,
    CASE
      WHEN role = 'user' THEN 'chat'
      WHEN metadata_json->>'source' = 'show_answer' THEN 'show_answer'
      WHEN metadata_json->>'source' = 'explain_tests' THEN 'explain_tests'
      ELSE 'other'
    END AS kind
  FROM ai_messages
  WHERE created_at >= NOW() - INTERVAL '7 days'
)
SELECT
  day::date AS day,
  kind,
  COUNT(*) AS calls
FROM usage
GROUP BY day, kind
ORDER BY day DESC, kind;
SQL

echo
echo "── Top 10 users by call volume, last 7 days ─────────────────"
psql "$DATABASE_URL" -P pager=off <<'SQL'
SELECT
  user_id,
  COUNT(*) FILTER (WHERE role = 'user')                                  AS chat_calls,
  COUNT(*) FILTER (WHERE metadata_json->>'source' = 'show_answer')       AS show_answer_calls,
  COUNT(*) FILTER (WHERE metadata_json->>'source' = 'explain_tests')     AS explain_calls
FROM ai_messages
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY user_id
ORDER BY chat_calls + show_answer_calls + explain_calls DESC
LIMIT 10;
SQL

echo
echo "Tips: if any single user is anomalous, set AI_KILL_SWITCH=true"
echo "      on Fly (\`flyctl secrets set AI_KILL_SWITCH=true\`) to freeze"
echo "      AI features instantly. Investigate, then unset to resume."
