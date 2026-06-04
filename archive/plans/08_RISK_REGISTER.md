# 08 — Risk Register

## Risk 1 — Overbuilding environment infrastructure

Likelihood: High  
Impact: High

Problem:

Building a custom IDE/sandbox too early could consume months before proving demand.

Mitigation:

Use GitHub-first workflow for MVP. Upgrade gradually.

## Risk 2 — AI gives answers instead of teaching

Likelihood: High  
Impact: High

Problem:

Learners may copy-paste AI solutions and fail to learn.

Mitigation:

- Hint levels
- Socratic prompts
- Attempt tracking
- Tests as source of truth
- AI reviews process, not just final code
- Reflection questions

## Risk 3 — Setup friction hurts learners

Likelihood: Medium  
Impact: High

Problem:

GitHub, Docker, or local setup may block beginners.

Mitigation:

- Excellent onboarding
- Codespaces option
- Setup verification command
- First challenge focused only on running the app
- Video walkthrough

## Risk 4 — Generic AI coding tools compete

Likelihood: High  
Impact: Medium

Problem:

Users may think ChatGPT/Copilot/Cursor are enough.

Mitigation:

Position around structured production practice, validation, and portfolio evidence.

## Risk 5 — Weak content quality

Likelihood: Medium  
Impact: High

Problem:

If challenges feel fake, users will not value the product.

Mitigation:

- Each challenge must map to a real engineering workflow.
- Include logs, broken tests, PR review, CI issues.
- Use realistic company context.

## Risk 6 — Validation cheating

Likelihood: Medium  
Impact: Medium

Problem:

Users can bypass visible tests.

Mitigation:

- Hidden tests after MVP
- Private validation runner
- Require reasoning/summary
- AI review can flag suspicious diffs

## Risk 7 — AI cost creep

Likelihood: Medium  
Impact: Medium

Problem:

High AI usage can destroy margins.

Mitigation:

- Limit free-tier AI messages
- Summarize context
- Cache challenge context
- Use cheaper models for simple hints
- Use structured compact prompts

## Risk 8 — Too broad a product

Likelihood: High  
Impact: High

Problem:

Trying to support all languages/stacks dilutes the MVP.

Mitigation:

Start with one narrow backend track.
