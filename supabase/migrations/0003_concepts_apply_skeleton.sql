-- 0003 — Mental Models v2 / M2 (Apply made real).
--
-- Adds a nullable `apply_skeleton_json` column to `concepts`. Holds the
-- per-concept inline Pyodide Apply lesson:
--   {
--     "instructions_md": "...",
--     "starter_code": "def add_one(xs): ...",
--     "hidden_test": "def test_add_one(): ..."
--   }
--
-- When non-null, the concept's Apply stage renders an inline runner
-- (no Monaco — just a textarea + Run). When null, the stage falls back
-- to apply_challenge_slug (which links an existing skeleton/fillblank).
-- When both are null, the stage is a no-op placeholder (legacy path).
--
-- Idempotent — safe to re-run.

alter table public.concepts
  add column if not exists apply_skeleton_json jsonb;
