# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product, today

**ProdReady AI** — an AI-mentored, in-browser Python coding learning platform.

> **History note:** The product originally planned a GitHub-first MVP (template repos, Codespaces, GitHub Actions). It pivoted in the May 2026 build to an **in-browser Pyodide runner** — learners edit Python and run pytest entirely client-side, never touching Git. Files under `plans/` describe the _original_ MVP. They are kept for history but are not authoritative. This file is.

|                    |                                                                                                                                                                                                                               |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Web                | Next.js 15 (App Router, TypeScript) + Tailwind + shadcn-style components, deployed to Vercel: https://prodready-ai.vercel.app                                                                                                 |
| API                | FastAPI 0.115 + SQLAlchemy 2 + Pydantic 2, Python 3.12, deployed to Fly.io: https://prodready-api.fly.dev                                                                                                                     |
| DB / Auth          | Supabase (Postgres + Auth + Storage), project ref `ztrtiyvzzxiepbrognzf`, region `eu-west-2`                                                                                                                                  |
| In-browser runtime | Pyodide 0.26.4 from jsdelivr; pytest installed via micropip on first run                                                                                                                                                      |
| AI                 | OpenAI; `gpt-4o-mini` for chat/explainer, `gpt-4o` for PR review and show-answer                                                                                                                                              |
| Payments           | Stripe in **emulated mode** (`STRIPE_EMULATED=true` on Fly). Real Stripe code paths exist but are gated until paid validation.                                                                                                |
| Auth on the API    | Supabase user JWTs verified via JWKS (ES256). HS256 fallback supported for tests via `SUPABASE_JWT_SECRET`.                                                                                                                   |
| Hosting / GitHub   | Source on `main` at https://github.com/georget-j/Environment_Production_AI_Tool. Per-challenge template repo at https://github.com/georget-j/prodready-templates-fastapi-commerce (canonical content; learners never see it). |

## Commands

```bash
# Install
pnpm install                                              # web + shared workspace deps
python3.12 -m venv apps/api/.venv && source apps/api/.venv/bin/activate
pip install -r apps/api/requirements-dev.txt              # api deps + test/lint extras

# Dev servers (two terminals)
pnpm --filter web dev                                     # web on http://localhost:3000
uvicorn app.main:app --reload --app-dir apps/api          # api on http://localhost:8000
# scripts/dev.sh boots both with the venv active.

# Tests
cd apps/api && python -m pytest -q                        # api suite (~23 tests)
cd apps/api && python -m pytest tests/test_mentor.py      # single file
cd apps/api && python -m pytest tests/test_mentor.py::test_hint_level_clamped   # single test
pnpm --filter web typecheck                               # web type-check (no unit tests yet)

# Lint
cd apps/api && ruff check .                               # ruff for api + scripts
cd apps/api && ruff check --fix .                         # auto-fix
pnpm --filter web lint                                    # next lint

# Database (Supabase)
supabase db push --password '<db-pass>'                   # apply migrations to linked project
psql "postgresql://postgres@db.<ref>.supabase.co:5432/postgres" -f supabase/seed.sql   # re-seed

# Deploy
vercel --prod --yes                                       # web (from repo root; rootDirectory in Vercel project = apps/web)
flyctl deploy --remote-only                               # api (from apps/api). App name: prodready-api
# Vercel auto-deploys on every push to main; Fly is manual.

# Smoke test against deployed env
API_BASE=https://prodready-api.fly.dev WEB_BASE=https://prodready-ai.vercel.app bash scripts/smoke.sh
```

## Repo layout

```text
apps/
  web/          Next.js app — challenge page, mentor sidebar, Monaco editor, Pyodide runner
  api/          FastAPI — auth, tracks, challenges, submissions, AI endpoints, billing
challenge-templates/
  fastapi-commerce/   Source repo for the 3 seeded challenges (mirrored to its own GitHub repo)
supabase/
  migrations/   0001_init.sql (canonical schema)
  seed.sql      Backend Production Developer track + Module 1 + 3 challenges
packages/shared/    Zod schema for the AI PR review (referenced once, may be inlined)
plans/        Original GitHub-first MVP plans (HISTORICAL — do not implement against)
prompts/      Original prompt templates (HISTORICAL — runtime prompts live in apps/api/app/ai/system_prompts.md)
docs/launch.md      Operational playbook (env vars, deploy commands)
```

## Domain modules (apps/api/app)

- `routers/tracks.py` — track list + detail
- `routers/challenges.py` — challenge detail, `POST /challenges/{slug}/start` (creates progress row)
- `routers/submissions.py` — `POST /challenges/{slug}/submit` (parses pytest output, triggers AI review)
- `routers/ai.py` — `POST /ai/chat`, `POST /ai/explain-tests`, `POST /ai/show-answer`, `GET /ai/messages/{cid}`, `DELETE /ai/messages/{cid}`
- `routers/billing.py` — `POST /billing/checkout`, `POST /billing/webhook` (both honour `STRIPE_EMULATED`)
- `ai/mentor.py`, `ai/explainer.py`, `ai/review.py`, `ai/answers.py` — OpenAI clients per use case; all share the prompt-loader in `ai/prompts.py` (versioned via git blob SHA of `ai/system_prompts.md`)
- `auth.py` — JWT verification (JWKS + HS256 fallback)
- `access.py` — paywall gate: `ensure_can_access(user, challenge)` for non-free challenges
- `validation.py` — parse pytest text output to a `TestSummary`

## Web architecture (apps/web/src)

- `app/challenges/[slug]/page.tsx` — server-rendered hero (scenario/goal/instructions); delegates to `<ChallengeView>` for the interactive surface
- `components/challenge-view.tsx` — client shell that owns the runner ref and the mentor ref; lays out a 2-col grid (workspace + mentor sidebar) on `lg+`
- `components/challenge-runner.tsx` — Monaco editor + Pyodide runner + tests panel + results. Exposes `ChallengeRunnerHandle { jumpTo, applyFiles }` via `forwardRef`
- `components/mentor-chat.tsx` — chat with Hint 1/2/3 buttons + "Show me the answer". Exposes `MentorChatHandle { askMentor, scrollIntoView, appendAssistantNotice }`
- `components/mentor-message.tsx` — parses assistant text for `app/...py(:N)` refs and renders inline jump-to-code buttons
- `components/show-answer-modal.tsx` — confirm-then-replace dialog for "Show me the answer"
- `components/onboarding-tour.tsx` — centered modal carousel, fires on first visit, persists in `localStorage.prodready:onboarded`
- `components/glossary.tsx` + `lib/glossary.ts` — inline tooltips for technical terms (pytest, assertion, etc.)
- `lib/pyodide.ts` — single-instance Pyodide loader (`getPyodide`), writes the file tree, runs pytest, parses `--tb=short` output for failure line numbers
- `lib/featured-files.ts` — per-challenge `CHALLENGE_CONFIG` declaring editable + readonly + test cases per slug
- `lib/api.ts` — typed `apiFetch` for server components against the FastAPI service
- `lib/supabase/{client,server,middleware}.ts` — `@supabase/ssr` integration

## Imperative ref bridge between sibling client components

`ChallengeView` is the parent for the workspace and the mentor. It holds refs to both so:

- the mentor's `<MentorMessage>` file-link clicks can call `runnerRef.current?.jumpTo(file, line)` to drive the editor
- the show-answer flow can read the current file snapshot (via the runner's `onFilesChange` callback) and apply the AI-generated replacement via `runnerRef.current?.applyFiles(next)`
- the runner's "I'm stuck — help" button can call `mentorRef.current?.askMentor(prebakedMessage, hintLevel)`

This pattern (forwardRef + `useImperativeHandle` exposing a typed `Handle`) is the established way to coordinate sibling clients — don't introduce Context or external stores for cross-component imperative actions.

## Conventions

**Backend:**

- Pydantic `BaseModel` for request/response, `ConfigDict(from_attributes=True)` when reading from SQLAlchemy.
- AI inputs are `dataclass(frozen=True)`; AI outputs go through OpenAI structured outputs with strict JSON Schema and a small filter step (e.g. `answers.py` drops fixed_files whose path isn't in the learner's editable set).
- Every AI call records `prompt_sha` (git blob hash of `apps/api/app/ai/system_prompts.md`) in `AIMessage.metadata_json`.
- Ruff line-length 120; B008 ignored (FastAPI `Depends()` in defaults).
- No mocks in DB tests — Supabase Postgres is canonical, Alembic stays in sync for local parity.

**Web:**

- Server components fetch via `apiFetch`; client components carry the user's bearer token from the Supabase session.
- LocalStorage namespace: `prodready:<purpose>:<slug>` (edits, answer-viewed, onboarded).
- No `dangerouslySetInnerHTML`. All user-/AI-rendered text goes through `react-markdown` or `<MentorMessage>`.
- Tailwind utilities, no CSS modules. Custom Monaco decorations are CSS in `globals.css` under `.prodready-*` classnames.

## Non-negotiable constraints

1. Pytest output → `submissions.passed` is the source of truth. The AI never decides pass/fail.
2. The mentor is Socratic at Hint 1 (asks questions), specific at Hint 2 (file/function pointer), and only sketches pseudocode at Hint 3. "Show me the answer" is the explicit escape hatch — replaces the learner's code with a working version and is persisted as an `AIMessage` row tagged `metadata_json.source = "show_answer"`.
3. No code execution server-side — Pyodide in the browser. We do NOT run arbitrary learner Python on our infrastructure.
4. Auth is centralised in `apps/api/app/auth.py`; routes use `user = Depends(get_current_user)`. Owner-only data (progress, submissions, ai_messages) is RLS-enforced at Supabase; the API uses the service-role key but funnels everything through `user.id`.
5. Stripe webhook handling honours `STRIPE_EMULATED`; flipping to live = swap env vars on Fly, no code change.
6. Don't reintroduce Git-based workflow steps in challenge instructions ("fork the repo", "run `docker compose up`"). The product runs in the browser; instructions must be spatially neutral (no "scenario above", "workspace below").

## When making changes

- Plans under `plans/` are historical — do not implement against them. Current product decisions live in this file and in the operational playbook at [docs/launch.md](docs/launch.md); any other planning artefacts are tracked outside this repository.
- Run `pytest -q` in `apps/api` and `pnpm --filter web typecheck` before commit.
- Push to `main` (no PR workflow yet). Vercel auto-redeploys; Fly is manual via `flyctl deploy --remote-only`.
- For UX work in the challenge surface: the layout is hero + 2-col (workspace left, mentor sidebar right on `lg+`, stacked on `md` and below). Don't reintroduce a 3-col layout — it cramps Monaco at 1024–1279px and was the Phase Q regression that Phase R fixed.

## Out of scope until paid validation

- Custom browser IDE beyond Monaco.
- Server-side code execution (sandbox infra).
- Multi-language tracks (Python only).
- Cohort/enterprise features.
- Real Stripe live keys (emulation is intentional).
- Mobile-first design (md+ is primary).
