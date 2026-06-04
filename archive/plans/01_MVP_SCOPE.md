# 01 — MVP Scope

## MVP goal

Build a paid-testable MVP that proves users want production-style coding practice with AI mentorship.

## MVP should include

### User-facing

- Landing page
- Auth
- Track overview
- Challenge detail page
- AI mentor chat
- Submission form
- Validation results page
- Progress dashboard
- Basic pricing/paywall placeholder or Stripe integration
- Completion status per challenge

### Admin/content

- Seeded track/module/challenge data
- Markdown or YAML challenge authoring format
- Basic admin script to import challenges
- Prompt templates stored in repo

### AI

- AI mentor chat
- Error explainer
- PR-style code review
- Structured review output

### Validation

- GitHub Actions or local worker-based validation
- Visible check output
- Hidden check design documented, even if MVP uses visible checks first
- Store test output and pass/fail state

## MVP should not include

- Custom cloud IDE
- Full browser-based terminal
- Running untrusted code on our own infra
- Multiple tracks
- Cohort management
- Advanced certificates
- Advanced gamification
- Marketplace/content authoring UI
- Complex enterprise features

## First 10 MVP challenges

1. Run the app and understand repo structure.
2. Fix a failing test.
3. Add email validation to a registration endpoint.
4. Fix invalid coupon handling in an orders API.
5. Add pagination to an endpoint.
6. Write an API test.
7. Fix a Docker environment variable issue.
8. Debug a PostgreSQL connection issue.
9. Read and fix a GitHub Actions failure.
10. Final mini-ticket: add a production-ready feature with tests and logging.

## MVP completion criteria

A learner can complete one full loop:

1. Sign up.
2. Start challenge.
3. Access repo instructions.
4. Ask AI for help.
5. Submit repo URL/commit SHA.
6. System validates.
7. AI reviews.
8. Challenge marked complete.

## MVP pricing test

Start with:

- Free: 2 or 3 tickets, limited AI help
- Pro: £19/month or £29/month
- Early-access lifetime/annual offer optional

The MVP is not considered validated until at least 5–10 users pay or commit to pay.
