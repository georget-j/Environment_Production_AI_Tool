-- Seed: Backend Production Developer track, Module 1, challenges 1–3.
-- Idempotent: use upserts so `supabase db reset` re-applies cleanly.

insert into public.tracks (id, slug, title, description, difficulty, is_published)
values (
  '00000000-0000-0000-0000-000000000001',
  'backend-production-python',
  'Backend Production Developer',
  'Python, FastAPI, PostgreSQL, Docker, pytest, Git, GitHub Actions. The missing bridge between tutorials and a first real engineering job.',
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
  'Run the app and understand the repo',
  'You just joined a small commerce startup. Your team uses a FastAPI service backed by PostgreSQL. Before you can fix anything, you need to get the app running locally and explain what it does in plain English.',
  'Get the FastAPI commerce app running with `docker compose up`, then make every test pass with `pytest`.',
  '## Steps\n1. Fork the template repo.\n2. `docker compose up -d` to start Postgres.\n3. `pip install -r requirements.txt`.\n4. `pytest` — all tests should already pass on `main`.\n5. Submit the repo URL and your commit SHA.',
  'https://github.com/georget-j/prodready-templates-fastapi-commerce',
  'main',
  '{"tests": ["pytest -q"], "lint": ["ruff check ."]}',
  '{"max_hint_level": 2, "do_not_reveal_solution": true, "encourage_tests_first": true}',
  array['fastapi', 'docker', 'pytest', 'git'],
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
  'A teammate merged a small change overnight and now CI is red. The test `test_orders.py::test_create_order_persists_total` is failing. Read the failure, find the bug, fix it without changing the test.',
  'Make `pytest` go green again without modifying any test file.',
  '## Steps\n1. Check out the `challenge-fix-failing-test` branch.\n2. Run `pytest` and read the failure.\n3. Identify which production-code file is wrong.\n4. Fix it.\n5. Submit the repo URL and your commit SHA.',
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
  'Support tickets are piling up: customers can submit random coupon codes and still get a discount. The order endpoint accepts anything. Make it reject invalid codes with a clear 400 response and add a test that proves it.',
  'Update the order creation flow so invalid coupon codes return HTTP 400. Add a test that fails before your fix and passes after.',
  '## Steps\n1. Check out the `challenge-invalid-coupon` branch.\n2. Read `app/orders.py` and `app/coupons.py`.\n3. Add validation. Add a test in `tests/test_orders.py`.\n4. `pytest` should be green.\n5. Submit the repo URL and your commit SHA.',
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
  ('docker', 'Docker'),
  ('pytest', 'pytest'),
  ('git', 'Git'),
  ('debugging', 'Debugging'),
  ('reading-stack-traces', 'Reading stack traces'),
  ('api-validation', 'API validation'),
  ('production-error-handling', 'Production error handling')
on conflict (slug) do update set name = excluded.name;
