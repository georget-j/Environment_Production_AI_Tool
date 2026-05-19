# ProdReady AI

AI-powered production coding simulator. Learners complete realistic engineering tickets in real repos, get guided by an AI senior engineer, pass automated checks, and graduate with portfolio evidence.

> The missing bridge between coding tutorials and a first production software engineering job.

See [plans/00_PRODUCT_SUMMARY.md](plans/00_PRODUCT_SUMMARY.md) for the full product summary.

## Status

Pre-MVP. Building the first paid-testable slice: the **Backend Production Developer** track (Python / FastAPI / PostgreSQL / Docker / pytest / Git / GitHub Actions).

The execution plan lives at [.claude/plans/i-have-created-a-mutable-rain.md](../.claude/plans/i-have-created-a-mutable-rain.md) (outside the repo) — the canonical reading order for contributors is [CLAUDE.md](CLAUDE.md), then [plans/](plans/) numerically.

## Monorepo layout

```text
apps/
  web/                  Next.js 15 + App Router (TypeScript, Tailwind, shadcn/ui)
  api/                  FastAPI + SQLAlchemy + Alembic
packages/
  shared/               TS types shared between web and api contracts
challenge-templates/
  fastapi-commerce/     First learner template repo (pushed to GitHub separately)
supabase/
  migrations/           SQL migrations (Supabase Postgres is canonical)
  seed.sql              Track + module + challenges seed
scripts/                Dev + content-import scripts
plans/                  Product + technical planning docs
prompts/                AI mentor system prompts (git-SHA-versioned at runtime)
templates/              Authoring templates (challenge.yaml, db_schema.sql, GH Actions)
```

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15 + TypeScript + Tailwind + shadcn/ui |
| Backend | FastAPI (Python 3.12) |
| Auth + DB + Storage | Supabase |
| LLM | OpenAI (chat: `gpt-4o-mini`, PR review: `gpt-4o`) |
| Payments | Stripe (test mode for MVP) |
| Validation | GitHub Actions in template repos |
| Hosting | Vercel (web) + Fly.io or Render (api) + Supabase (db) |

## Quickstart

Prereqs: Node 20+, pnpm 9+, Python 3.12+, Supabase CLI, Docker.

```bash
# Install deps
pnpm install
python3 -m venv apps/api/.venv && source apps/api/.venv/bin/activate
pip install -r apps/api/requirements.txt

# Env
cp .env.example .env.local
cp .env.example apps/api/.env

# DB
supabase start
supabase db reset    # applies migrations + seed

# Dev
pnpm dev:web         # http://localhost:3000
uvicorn app.main:app --reload --app-dir apps/api  # http://localhost:8000
```

## Non-negotiable MVP constraints

From [CLAUDE.md](CLAUDE.md):

1. No custom cloud IDE in the MVP.
2. No arbitrary untrusted user code on our own infrastructure.
3. GitHub template repos + devcontainers/Codespaces + GitHub Actions for validation first.
4. First track is narrow: Python FastAPI backend production workflow.
5. AI mentor guides and reviews; automated checks are the source of truth for pass/fail.

## License

Proprietary, all rights reserved (until further notice).
