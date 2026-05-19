# 03 — Architecture

## MVP architecture

```text
User
  ↓
Next.js Web App
  ↓
Backend API
  ├── Auth
  ├── Tracks/Curriculum
  ├── Challenges
  ├── Submissions
  ├── AI Mentor
  ├── Validation
  ├── Billing
  └── Analytics
        ↓
PostgreSQL
Redis/Queue
Object Storage for logs
        ↓
GitHub / GitHub Actions / LLM API / Stripe
```

## Recommended stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Monaco Editor only for viewing snippets/diffs, not full IDE MVP

### Backend

Choose one:

- FastAPI if you want a Python-first product and stack consistency
- NestJS if you prefer TypeScript end-to-end

Recommended for MVP: **FastAPI backend + Next.js frontend**.

### Data

- PostgreSQL
- Redis for queue/jobs
- S3-compatible storage for long logs/artifacts if needed

### AI

- LLM API for mentor chat, error explanation, PR review
- Structured JSON outputs for review results
- Store prompt version with every AI output

### Validation

MVP:

- GitHub Actions workflow in challenge repos
- Learner submits repo URL + commit SHA
- Platform stores test output and AI review

Later:

- GitHub App integration
- Webhooks for CI results
- Private hidden test runner
- Sandboxed validation workers

## Core data model

```sql
users
- id
- email
- name
- role
- subscription_status
- created_at

tracks
- id
- slug
- title
- description
- difficulty
- is_published

modules
- id
- track_id
- title
- order_index

challenges
- id
- module_id
- slug
- title
- scenario
- instructions
- repo_template_url
- validation_config_json
- ai_rules_json
- order_index

user_challenge_progress
- id
- user_id
- challenge_id
- status
- started_at
- completed_at
- score
- attempts_count

submissions
- id
- user_id
- challenge_id
- repo_url
- commit_sha
- test_output
- lint_output
- ai_review_json
- passed
- created_at

ai_messages
- id
- user_id
- challenge_id
- role
- content
- metadata_json
- created_at

skills
- id
- slug
- name

user_skills
- id
- user_id
- skill_id
- proficiency_score
```

## API endpoints

```text
POST /api/auth/signup
GET  /api/tracks
GET  /api/tracks/:trackId
GET  /api/challenges/:challengeId
POST /api/challenges/:challengeId/start
POST /api/challenges/:challengeId/submit
GET  /api/submissions/:submissionId
POST /api/ai/chat
POST /api/ai/review
POST /api/billing/checkout
POST /api/billing/webhook
GET  /api/dashboard
```

## Repo structure

```text
prodready-ai/
  apps/
    web/
    api/
  packages/
    shared/
  challenge-templates/
    fastapi-commerce/
      .devcontainer/
      .github/workflows/
      app/
      tests/
      README.md
  plans/
  prompts/
  templates/
```
