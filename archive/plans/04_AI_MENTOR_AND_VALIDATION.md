# 04 — AI Mentor and Validation

## Principle

The AI is a mentor, not the judge.

Automated checks are the source of truth. The AI explains, guides, reviews, and summarizes.

## AI mentor modes

### 1. Socratic hint mode

Used when the learner asks for help.

Behavior:

- Ask one useful diagnostic question.
- Give a small next step.
- Do not provide the full answer immediately.
- Encourage running tests.
- Refer to the current ticket goal.

### 2. Error explainer mode

Used when tests fail.

Behavior:

- Explain the failure in plain English.
- Identify likely file/function.
- Suggest next debugging step.
- Avoid giving final code unless the learner has made multiple failed attempts.

### 3. PR reviewer mode

Used after submission.

Behavior:

- Review correctness, maintainability, tests, readability, edge cases, and production readiness.
- Give score out of 100.
- Return structured JSON.
- Include strengths, issues, required fixes, and learning summary.

### 4. Learning summary mode

Used after challenge completion.

Behavior:

- Summarize what the learner practiced.
- Connect the task to real production work.
- Update skill progress.

## AI guardrails

- Do not immediately reveal final solutions.
- Avoid creating dependency on copy-paste answers.
- Use hint levels.
- Encourage the learner to inspect logs/tests.
- Encourage small commits and test-first thinking.
- Never mark a challenge passed without validation.

## AI tool functions

The backend should expose internal functions such as:

```json
[
  {
    "name": "get_challenge_context",
    "description": "Get challenge scenario, goals, hints, skills, and validation rules."
  },
  {
    "name": "get_latest_test_output",
    "description": "Fetch latest test/lint output for this submission."
  },
  {
    "name": "get_user_diff",
    "description": "Fetch the learner's code diff if available."
  },
  {
    "name": "submit_code_review",
    "description": "Return structured PR-style feedback."
  },
  {
    "name": "mark_skill_progress",
    "description": "Update learner skill graph after completion."
  }
]
```

## Structured PR review schema

```json
{
  "passed": true,
  "score": 86,
  "summary": "The implementation correctly validates coupon codes and adds a useful test.",
  "strengths": [
    "Clear validation path",
    "Good API status code",
    "Test covers expected invalid input"
  ],
  "issues": [
    {
      "severity": "minor",
      "title": "Error message could be more specific",
      "suggestion": "Return a stable error code as well as a human-readable message."
    }
  ],
  "required_fixes": [],
  "skills_practiced": [
    "api-validation",
    "pytest",
    "error-handling"
  ],
  "next_recommended_challenge": "add-pagination-to-orders"
}
```

## Validation options

### MVP validation

- Learner runs tests locally or in Codespaces.
- GitHub Actions also runs tests.
- Learner submits repo URL/commit SHA and test output.
- Platform uses AI review and stored output.

### Better V1 validation

- GitHub App listens to Actions results.
- Platform reads workflow status automatically.
- Hidden tests run in private validation repo or self-hosted runner.

### Later validation

- Ephemeral sandbox worker pulls learner repo.
- Injects hidden tests.
- Runs tests/lint/typecheck.
- Stores logs/artifacts.
- Destroys environment.

## Validation command examples

```bash
pytest
ruff check .
mypy app || true
```

## Do not rely on AI to decide pass/fail

AI can explain why something failed or review quality, but pass/fail should come from automated checks.
