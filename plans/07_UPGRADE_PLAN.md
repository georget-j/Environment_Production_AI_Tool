# 07 — Upgrade Plan

## Upgrade path summary

Do not jump from MVP directly to custom sandbox infrastructure. Upgrade in layers.

## Upgrade 1 — Improve repo workflow

Add:

- GitHub App
- Automatic repo connection
- Automatic commit/PR detection
- Pull request review comments
- Actions webhook ingestion
- Better submission UX

Benefit:

- Keeps real production workflow.
- Reduces manual copy/paste.

## Upgrade 2 — Codespaces-first experience

Add:

- Open in Codespaces button
- Devcontainer for each challenge repo
- Preinstalled dependencies
- Seeded database scripts
- Setup verification command

Benefit:

- Removes local setup friction.
- Keeps GitHub/dev workflow realistic.

## Upgrade 3 — Hidden validation

Add:

- Private validation repo
- Platform-owned validation runner
- Hidden tests injected at validation time
- Test artifact collection
- Plagiarism/cheat checks

Benefit:

- More trustworthy scoring.
- Better paid product.

## Upgrade 4 — Embedded execution provider

Evaluate:

- CodeSandbox SDK for cloud dev environments
- E2B for isolated code execution sandboxes
- Modal Sandboxes for running untrusted code at scale
- WebContainers for browser-based Node/JS tracks

Benefit:

- Better integrated experience.
- Less dependence on user GitHub workflow.

Caution:

- Do this only after proving users will pay.

## Upgrade 5 — Custom sandbox infrastructure

Build only when needed.

Potential architecture:

- API creates validation job.
- Queue schedules ephemeral worker.
- Worker clones repo.
- Worker injects hidden tests.
- Worker runs in isolated container/microVM.
- CPU/memory/network/time limits enforced.
- Logs/artifacts stored.
- Environment destroyed.

Security requirements:

- No long-lived credentials in sandbox.
- Network egress restrictions.
- File system isolation.
- Non-root execution.
- Timeouts.
- Resource quotas.
- Abuse monitoring.

## Upgrade 6 — Curriculum expansion

Add tracks in this order:

1. Node.js Backend Production Developer
2. React Frontend Production Developer
3. Full-stack SaaS Developer
4. DevOps/Platform basics
5. AI application engineer

## Upgrade 7 — B2B

Add:

- Cohorts
- Instructor dashboard
- Curriculum assignment
- Company-specific scenarios
- Reports
- SCORM/LMS integrations if demanded

## Upgrade 8 — Portfolio/career layer

Add:

- Public profile
- Project writeups
- GitHub PR history import
- AI-generated CV bullets
- Interview talking points
- Skill evidence map
