-- 0004 — Mental Models v2 / M8 (concept-level learner feedback).
--
-- Cheap signal so authors see which concepts are confusing real learners.
-- One row per (user, concept, kind) feedback submission. No author dashboard
-- yet — just collect the data. Query: which concepts are most flagged?
--
-- RLS: owner-only. The author dashboard (later phase) will query via the
-- service-role key like the rest of the API.

create table if not exists public.concept_feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  concept_slug text not null,
  stage text,                   -- 'read' / 'play' / 'check' / 'apply' / 'reflect' / null
  kind text not null check (kind in ('helpful', 'confusing', 'other')),
  free_text text,
  created_at timestamptz not null default now()
);

create index if not exists concept_feedback_user_idx on public.concept_feedback (user_id);
create index if not exists concept_feedback_concept_idx on public.concept_feedback (concept_slug, kind);

alter table public.concept_feedback enable row level security;

drop policy if exists "concept_feedback_owner_read" on public.concept_feedback;
create policy "concept_feedback_owner_read" on public.concept_feedback
  for select using (auth.uid() = user_id);

drop policy if exists "concept_feedback_owner_write" on public.concept_feedback;
create policy "concept_feedback_owner_write" on public.concept_feedback
  for insert with check (auth.uid() = user_id);
