-- Seed: Backend Production Developer track, Module 1, challenges 1–3.
-- Idempotent: use upserts so `supabase db reset` re-applies cleanly.

insert into public.tracks (id, slug, title, description, difficulty, is_published)
values (
  '00000000-0000-0000-0000-000000000001',
  'backend-production-python',
  'Backend Production Developer',
  'Python, FastAPI, and pytest — read realistic broken services and ship the fix, all in your browser. The missing bridge between tutorials and a first real engineering job.',
  'beginner-plus',
  true
)
on conflict (slug) do update set
  title = excluded.title,
  description = excluded.description,
  difficulty = excluded.difficulty,
  is_published = excluded.is_published;

insert into public.modules (id, track_id, slug, title, order_index)
values (
  '00000000-0000-0000-0000-000000000010',
  '00000000-0000-0000-0000-000000000001',
  'working-like-a-developer',
  'Module 1 — Working like a developer',
  1
)
on conflict (track_id, slug) do update set
  title = excluded.title,
  order_index = excluded.order_index;

-- Challenge 1 — Run the app and understand repo structure
insert into public.challenges (
  id, module_id, slug, title, scenario, learner_goal, instructions,
  repo_template_url, repo_branch, validation_config_json, ai_rules_json,
  skills, is_free, order_index
) values (
  '00000000-0000-0000-0000-000000000100',
  '00000000-0000-0000-0000-000000000010',
  'fastapi-commerce-run-and-explore',
  'Explore a FastAPI service',
  'You just joined a small commerce startup. The team''s FastAPI service is on the left — routes, order logic, and tests. Before fixing anything in the next challenge, get a feel for how the pieces fit together by reading the code.',
  'Read the FastAPI app''s routes, order logic, and tests so you understand the codebase before changing anything.',
  E'**Concept.** A FastAPI service has three layers worth scanning before you change anything: the *routes* that handle HTTP, the *business logic* that does the work, and the *tests* that pin down expected behaviour.\n\n**Example.**\n\n```python\n# A FastAPI route looks like this:\n@app.post("/orders")\ndef create_order(body: dict):\n    return {"total": compute_total(body)}\n```\n\n**Read.** Open `app/main.py`, then `app/orders.py`, then `tests/test_orders.py`. Answer in your head: where is the route, which function computes the total, and what does the first test check?\n\n**Expected.** `An understanding of the codebase — then continue to the next challenge.`',
  'https://github.com/georget-j/prodready-templates-fastapi-commerce',
  'main',
  '{"tests": ["pytest -q"], "lint": ["ruff check ."]}',
  '{"max_hint_level": 2, "do_not_reveal_solution": true, "encourage_tests_first": true}',
  array['fastapi', 'pytest', 'reading-code'],
  true,
  1
)
on conflict (slug) do update set
  title = excluded.title,
  scenario = excluded.scenario,
  learner_goal = excluded.learner_goal,
  instructions = excluded.instructions,
  repo_template_url = excluded.repo_template_url,
  repo_branch = excluded.repo_branch,
  validation_config_json = excluded.validation_config_json,
  ai_rules_json = excluded.ai_rules_json,
  skills = excluded.skills,
  is_free = excluded.is_free,
  order_index = excluded.order_index;

-- Challenge 2 — Fix a failing test
insert into public.challenges (
  id, module_id, slug, title, scenario, learner_goal, instructions,
  repo_template_url, repo_branch, validation_config_json, ai_rules_json,
  skills, is_free, order_index
) values (
  '00000000-0000-0000-0000-000000000101',
  '00000000-0000-0000-0000-000000000010',
  'fastapi-commerce-fix-failing-test',
  'Fix a failing test',
  'A teammate pushed a small change overnight and one of the order tests is now failing. The test `tests/test_orders.py::test_compute_total_create_order_persists_total` is red. Read the failure, find the bug in the source file, and make every test pass without touching the test file.',
  'Get every test green again without modifying any test file.',
  E'**Concept.** When a test fails, the failure message points at the file and line. Read what the test expects, find the bug in the *production* code (never the test), fix it, run again.\n\n**Example.**\n\n```\nFAILED tests/test_orders.py::test_compute_total_create_order_persists_total\n  expected 33.5, got 30.0\n  app/orders.py:24 in compute_total\n```\n\n**Your turn.** Edit `app/orders.py` until Run shows green. The test file is read-only. Click failing-test references to jump straight to the line.\n\n**Expected.** `All tests pass. Click Submit.`',
  'https://github.com/georget-j/prodready-templates-fastapi-commerce',
  'challenge-fix-failing-test',
  '{"tests": ["pytest -q"], "lint": ["ruff check ."]}',
  '{"max_hint_level": 3, "do_not_reveal_solution": true, "encourage_tests_first": true}',
  array['debugging', 'pytest', 'reading-stack-traces'],
  true,
  2
)
on conflict (slug) do update set
  title = excluded.title,
  scenario = excluded.scenario,
  learner_goal = excluded.learner_goal,
  instructions = excluded.instructions,
  repo_template_url = excluded.repo_template_url,
  repo_branch = excluded.repo_branch,
  validation_config_json = excluded.validation_config_json,
  ai_rules_json = excluded.ai_rules_json,
  skills = excluded.skills,
  is_free = excluded.is_free,
  order_index = excluded.order_index;

-- Challenge 3 — Reject invalid coupons (Pro)
insert into public.challenges (
  id, module_id, slug, title, scenario, learner_goal, instructions,
  repo_template_url, repo_branch, validation_config_json, ai_rules_json,
  skills, is_free, order_index
) values (
  '00000000-0000-0000-0000-000000000102',
  '00000000-0000-0000-0000-000000000010',
  'fastapi-commerce-reject-invalid-coupons',
  'Fix invalid coupon handling',
  'Support tickets are piling up: customers submit random coupon codes and still get a discount. The order endpoint accepts anything. Make it reject invalid codes with a clear error and add a test that proves your fix works.',
  'Reject invalid coupon codes in the order flow, and write a test that fails before your fix and passes after.',
  E'**Concept.** Validation belongs near the data. Fix `is_valid()` so it actually checks the coupon code, then make the order route reject unknown codes with HTTP 400, then prove it with a test.\n\n**Example.**\n\n```python\nKNOWN = {"WELCOME10", "FRIEND20"}\n\ndef is_valid(code: str | None) -> bool:\n    return code in KNOWN\n```\n\n**Your turn.** Edit `app/coupons.py`, `app/main.py`, and `tests/test_coupons.py` until all tests pass.\n\n**Expected.** `All tests pass. Click Submit.`',
  'https://github.com/georget-j/prodready-templates-fastapi-commerce',
  'challenge-invalid-coupon',
  '{"tests": ["pytest -q"], "lint": ["ruff check ."]}',
  '{"max_hint_level": 3, "do_not_reveal_solution": true, "encourage_tests_first": true}',
  array['fastapi', 'api-validation', 'pytest', 'production-error-handling'],
  false,
  3
)
on conflict (slug) do update set
  title = excluded.title,
  scenario = excluded.scenario,
  learner_goal = excluded.learner_goal,
  instructions = excluded.instructions,
  repo_template_url = excluded.repo_template_url,
  repo_branch = excluded.repo_branch,
  validation_config_json = excluded.validation_config_json,
  ai_rules_json = excluded.ai_rules_json,
  skills = excluded.skills,
  is_free = excluded.is_free,
  order_index = excluded.order_index;

-- Skills graph (slugs referenced by challenges.skills text[])
insert into public.skills (slug, name) values
  ('fastapi', 'FastAPI'),
  ('pytest', 'pytest'),
  ('reading-code', 'Reading code'),
  ('debugging', 'Debugging'),
  ('reading-stack-traces', 'Reading stack traces'),
  ('api-validation', 'API validation'),
  ('production-error-handling', 'Production error handling')
on conflict (slug) do update set name = excluded.name;
