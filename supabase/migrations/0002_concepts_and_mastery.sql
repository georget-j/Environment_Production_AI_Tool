-- ProdReady AI — Phase CC: concept-atom framework
-- Mental Models for Code pilot + shared universal-CS foundation library.
--
-- New tables:
--   concepts             — the atom of the framework; one row per concept atom.
--   concept_prereqs      — directed edges in the concept dependency graph.
--   concept_mastery      — per-user, per-concept stage progress + spaced-recall state.
--   diagnostic_questions — the question bank for placement diagnostics.
--   diagnostic_responses — one row per learner diagnostic attempt.
--
-- RLS: concepts + concept_prereqs + diagnostic_questions are world-readable
-- (no PII). concept_mastery + diagnostic_responses are owner-only, same as
-- user_challenge_progress / submissions in 0001.

-- ------------------------------------------------------------------
-- concepts — the framework's atom
-- ------------------------------------------------------------------
create table public.concepts (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  layer text not null check (layer in ('universal', 'topic', 'applied')),
  -- null for layer='universal'; track slug for layer='topic' (e.g. 'mental-models')
  topic_slug text,
  title text not null,
  one_line text not null,
  -- Try stage (productive-failure attempt before any teaching)
  try_prompt_md text not null,
  try_kind text not null check (try_kind in ('code', 'text-reasoning')),
  -- Common wrong-attempt patterns the Read stage references inline.
  -- Shape: [{"pattern": "regex|substring", "callback_md": "..."}]
  try_expected_attempts_json jsonb not null default '[]',
  -- Read stage
  exposition_md text not null,
  worked_example_md text not null,
  -- Play stage
  play_widget_kind text not null check (play_widget_kind in (
    'code-stepper', 'call-stack-visualiser', 'state-machine-animator',
    'memory-model-viewer', 'complexity-plotter', 'generic-slider-chart'
  )),
  play_widget_json jsonb not null default '{}',
  -- Check stage. Shape: [{"q": "...", "options": [...], "correct": 0, "why": "..."}]
  check_mcqs_json jsonb not null default '[]',
  -- Apply stage. References an existing challenge (lesson) that exercises the concept.
  apply_challenge_slug text references public.challenges(slug) on delete set null,
  -- Reflect stage
  reflect_question text not null,
  -- Shape: {"must_mention": [...], "must_distinguish": [["X", "Y"], ...]}
  reflect_rubric_json jsonb not null default '{}',
  -- Spaced-recall pool — one drawn at random per recall.
  -- Shape: [{"kind": "mcq"|"micro-code", "q": "...", "options": [...], "correct": 0}]
  recall_checks_json jsonb not null default '[]',
  order_index int not null,
  created_at timestamptz not null default now()
);

create index concepts_layer_topic_idx on public.concepts (layer, topic_slug, order_index);

-- ------------------------------------------------------------------
-- concept_prereqs — directed edges. Restrict on delete to prevent
-- silently dropping a graph dependency.
-- ------------------------------------------------------------------
create table public.concept_prereqs (
  concept_id uuid not null references public.concepts(id) on delete cascade,
  prereq_concept_id uuid not null references public.concepts(id) on delete restrict,
  primary key (concept_id, prereq_concept_id),
  check (concept_id <> prereq_concept_id)
);

-- ------------------------------------------------------------------
-- concept_mastery — per-user, per-concept stage progress.
-- Stage completion timestamps roll forward as the learner progresses.
-- mastered_at is set when all five non-Try stages are complete.
-- ------------------------------------------------------------------
create table public.concept_mastery (
  user_id uuid not null references public.users(id) on delete cascade,
  concept_id uuid not null references public.concepts(id) on delete cascade,
  -- Try stage (non-blocking; productive-failure record)
  try_attempted_at timestamptz,
  try_attempt_text text,
  -- Main pipeline
  read_completed_at timestamptz,
  play_completed_at timestamptz,
  check_completed_at timestamptz,
  apply_completed_at timestamptz,
  reflect_completed_at timestamptz,
  mastered_at timestamptz,
  -- Spaced-recall scheduling (SuperMemo-2-lite)
  next_recall_due_at timestamptz,
  recall_interval_days int not null default 1,
  recall_streak int not null default 0,
  -- 'needs-review' set when a recall check fails; UI flags the concept.
  status text not null default 'in_progress' check (status in (
    'in_progress', 'mastered', 'needs_review'
  )),
  primary key (user_id, concept_id)
);

create index concept_mastery_recall_due_idx
  on public.concept_mastery (user_id, next_recall_due_at)
  where next_recall_due_at is not null;

-- ------------------------------------------------------------------
-- diagnostic_questions — the placement quiz bank.
-- ------------------------------------------------------------------
create table public.diagnostic_questions (
  id uuid primary key default gen_random_uuid(),
  track_slug text not null,
  layer text not null check (layer in ('universal', 'topic')),
  question_md text not null,
  question_kind text not null check (question_kind in ('mcq', 'mini-code')),
  -- For mcq: {"options": [...], "correct": 0}
  -- For mini-code: {"starter_code": "...", "expected_stdout": "..."}
  options_json jsonb not null default '{}',
  expected_answer text not null,
  -- Concept slugs this question informs the proficiency vector for.
  maps_to_concept_slugs text[] not null default '{}',
  order_index int not null,
  created_at timestamptz not null default now()
);

create index diagnostic_questions_track_idx
  on public.diagnostic_questions (track_slug, order_index);

-- ------------------------------------------------------------------
-- diagnostic_responses — one row per learner attempt at a diagnostic.
-- inferred_mastery_json: {<concept_slug>: 0..1 proficiency}.
-- ------------------------------------------------------------------
create table public.diagnostic_responses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  track_slug text not null,
  -- {<question_id>: <answer string or 'a'|'b'|'c'|'d'>}
  responses_json jsonb not null default '{}',
  inferred_mastery_json jsonb not null default '{}',
  recommended_start_slug text not null,
  taken_at timestamptz not null default now()
);

create index diagnostic_responses_user_track_idx
  on public.diagnostic_responses (user_id, track_slug, taken_at desc);

-- ------------------------------------------------------------------
-- RLS — concepts/prereqs/diagnostic_questions world-read; mastery +
-- diagnostic_responses owner-only (matches user_challenge_progress).
-- ------------------------------------------------------------------
alter table public.concepts             enable row level security;
alter table public.concept_prereqs      enable row level security;
alter table public.concept_mastery      enable row level security;
alter table public.diagnostic_questions enable row level security;
alter table public.diagnostic_responses enable row level security;

-- world-read
create policy "concepts: read"              on public.concepts             for select using (true);
create policy "concept_prereqs: read"       on public.concept_prereqs      for select using (true);
create policy "diagnostic_questions: read"  on public.diagnostic_questions for select using (true);

-- owner-only
create policy "concept_mastery: self all"
  on public.concept_mastery for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "diagnostic_responses: self all"
  on public.diagnostic_responses for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
