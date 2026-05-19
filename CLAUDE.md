# Claude Code Project Instructions — ProdReady AI

You are building ProdReady AI, an AI-powered production coding simulator.

## Product mission

Help junior developers move beyond tutorials by completing realistic engineering tickets in production-style codebases with AI mentorship, tests, CI, PR-style review, and portfolio output.

## Non-negotiable MVP constraints

1. Do not build a custom cloud IDE in the MVP.
2. Do not run arbitrary untrusted user code on our own infrastructure in the MVP.
3. Prefer GitHub template repos, devcontainers/Codespaces, and GitHub Actions for validation first.
4. Keep the first track narrow: Python FastAPI backend production workflow.
5. Build a sellable thin vertical slice before expanding the curriculum.
6. The AI mentor must guide, review, and explain; it must not simply dump answers.
7. Automated validation, tests, and linting are the source of truth, not the AI.

## Files to read before implementation

Read these in order:

- `plans/00_PRODUCT_SUMMARY.md`
- `plans/01_MVP_SCOPE.md`
- `plans/02_PRODUCTION_ENVIRONMENT_OPTIONS.md`
- `plans/03_ARCHITECTURE.md`
- `plans/04_AI_MENTOR_AND_VALIDATION.md`
- `plans/05_CHALLENGE_CONTENT_BLUEPRINT.md`
- `plans/06_BUILD_ROADMAP.md`
- `plans/07_UPGRADE_PLAN.md`
- `plans/08_RISK_REGISTER.md`
- `plans/09_CLAUDE_CODE_TASK_LIST.md`

## Preferred implementation style

- TypeScript-first for the web app.
- Clear domain modules: auth, tracks, challenges, submissions, AI mentor, billing, admin.
- Use migrations and seed data.
- Use typed API contracts.
- Keep prompt templates versioned.
- Store AI outputs in structured JSON where possible.
- Write tests for business logic and validation parsing.
- Use feature flags for experimental environment providers.

## Definition of done for MVP

The MVP is done when a learner can:

1. Sign up.
2. View the Backend Production Developer track.
3. Start a production-style ticket.
4. Open a linked GitHub template/Codespaces/devcontainer repo.
5. Ask the AI mentor for guidance.
6. Submit a GitHub repo URL or commit SHA.
7. Trigger validation.
8. See pass/fail test results.
9. Receive AI PR-style review.
10. Complete at least one challenge and see progress update.

## Do not overbuild

Avoid these until after paid validation:

- Custom browser IDE.
- Multi-language support.
- Custom secure sandbox infrastructure.
- Complex gamification.
- Enterprise cohort dashboards.
- Advanced analytics.
- Marketplace/content creator systems.
