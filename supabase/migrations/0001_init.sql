-- ProdReady AI — initial schema
-- Canonical source: this file. apps/api SQLAlchemy models mirror it.
-- All learner-owned tables enforce row-level security.

create extension if not exists "pgcrypto";

-- ------------------------------------------------------------------
-- users  (1:1 with auth.users; profile + subscription state)
-- ------------------------------------------------------------------
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  name text,
  role text not null default 'learner' check (role in ('learner', 'admin')),
  subscription_status text not null default 'free' check (subscription_status in ('free', 'active', 'past_due', 'canceled')),
  stripe_customer_id text,
  created_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.users (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ------------------------------------------------------------------
-- curriculum: tracks → modules → challenges
-- ------------------------------------------------------------------
create table public.tracks (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  title text not null,
  description text,
  difficulty text,
  is_published boolean not null default false,
  created_at timestamptz not null default now()
);

create table public.modules (
  id uuid primary key default gen_random_uuid(),
  track_id uuid not null references public.tracks(id) on delete cascade,
  slug text not null,
  title text not null,
  order_index int not null,
  unique (track_id, slug)
);

create table public.challenges (
  id uuid primary key default gen_random_uuid(),
  module_id uuid not null references public.modules(id) on delete cascade,
  slug text unique not null,
  title text not null,
  scenario text not null,
  learner_goal text not null,
  instructions text not null default '',
  repo_template_url text,
  repo_branch text,
  validation_config_json jsonb not null default '{}',
  ai_rules_json jsonb not null default '{}',
  skills text[] not null default '{}',
  is_free boolean not null default false,
  order_index int not null,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------------
-- learner state: progress + submissions + ai_messages
-- ------------------------------------------------------------------
create table public.user_challenge_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  challenge_id uuid not null references public.challenges(id) on delete cascade,
  status text not null default 'not_started' check (status in ('not_started', 'in_progress', 'completed')),
  started_at timestamptz,
  completed_at timestamptz,
  score int,
  attempts_count int not null default 0,
  unique (user_id, challenge_id)
);

create table public.submissions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  challenge_id uuid not null references public.challenges(id) on delete cascade,
  repo_url text not null,
  commit_sha text,
  test_output text,
  lint_output text,
  passed boolean not null default false,
  ai_review_json jsonb not null default '{}',
  prompt_sha text,
  created_at timestamptz not null default now()
);

create index submissions_user_challenge_idx on public.submissions (user_id, challenge_id, created_at desc);

create table public.ai_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  challenge_id uuid not null references public.challenges(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  hint_level int,
  prompt_sha text,
  metadata_json jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index ai_messages_user_challenge_idx on public.ai_messages (user_id, challenge_id, created_at);

-- ------------------------------------------------------------------
-- skills graph
-- ------------------------------------------------------------------
create table public.skills (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null
);

create table public.user_skills (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  skill_id uuid not null references public.skills(id) on delete cascade,
  proficiency_score int not null default 0,
  unique (user_id, skill_id)
);

-- ------------------------------------------------------------------
-- RLS — curriculum is public-read; learner state is owner-only.
-- The service-role key (used by apps/api) bypasses RLS by design.
-- ------------------------------------------------------------------
alter table public.users enable row level security;
alter table public.tracks enable row level security;
alter table public.modules enable row level security;
alter table public.challenges enable row level security;
alter table public.user_challenge_progress enable row level security;
alter table public.submissions enable row level security;
alter table public.ai_messages enable row level security;
alter table public.skills enable row level security;
alter table public.user_skills enable row level security;

-- users
create policy "users: self read"   on public.users for select using (auth.uid() = id);
create policy "users: self update" on public.users for update using (auth.uid() = id);

-- curriculum: anyone can read published rows
create policy "tracks: read published"     on public.tracks     for select using (is_published);
create policy "modules: read"              on public.modules    for select using (true);
create policy "challenges: read"           on public.challenges for select using (true);
create policy "skills: read"               on public.skills     for select using (true);

-- learner state: owner-only
create policy "progress: self all"   on public.user_challenge_progress for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "submissions: self all" on public.submissions             for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "ai_messages: self all" on public.ai_messages             for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "user_skills: self all" on public.user_skills             for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
