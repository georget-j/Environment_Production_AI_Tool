# 09 — Claude Code Task List

Use these tasks in order. Complete one task before moving to the next.

## Task 1 — Initialize project

Create a monorepo:

```text
prodready-ai/
  apps/web
  apps/api
  packages/shared
  challenge-templates/fastapi-commerce
  plans
  prompts
  templates
```

Use:

- Next.js + TypeScript for `apps/web`
- FastAPI for `apps/api`
- PostgreSQL with Docker Compose
- Alembic or equivalent migrations
- Basic `.env.example`

## Task 2 — Implement database models

Create models for:

- users
- tracks
- modules
- challenges
- progress
- submissions
- ai_messages
- skills
- user_skills

Add seed data for one track, one module, and three challenges.

## Task 3 — Build frontend shell

Create pages:

- `/`
- `/pricing`
- `/dashboard`
- `/tracks`
- `/tracks/[slug]`
- `/challenges/[slug]`

Use clean responsive UI.

## Task 4 — Build challenge flow

Implement:

- start challenge
- display scenario/instructions
- repo link
- validation commands
- submit repo URL/commit SHA
- view result

## Task 5 — Add AI mentor

Implement:

- chat panel
- backend `/api/ai/chat`
- challenge context injection
- hint-level system
- message persistence

## Task 6 — Add AI PR review

Implement:

- `/api/ai/review`
- structured JSON output
- review display component
- score, strengths, issues, required fixes, skills practiced

## Task 7 — Add validation record

Implement:

- submission status
- pass/fail
- test output storage
- manual validation input first
- later replace with GitHub webhook

## Task 8 — Create challenge template repo

Under `challenge-templates/fastapi-commerce`, create:

- FastAPI app
- PostgreSQL docker-compose
- pytest tests
- `.devcontainer`
- GitHub Actions workflow
- README instructions
- one intentionally broken challenge branch or folder

## Task 9 — Add billing gate

Implement:

- free access to first 2–3 challenges
- Pro access flag
- Stripe placeholder or real checkout

## Task 10 — Launch checklist

Add:

- landing page copy
- privacy/terms placeholders
- analytics events
- seed data
- smoke tests
- README setup guide
- demo walkthrough script
