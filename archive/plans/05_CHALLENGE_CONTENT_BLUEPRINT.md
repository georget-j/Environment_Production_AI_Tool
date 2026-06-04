# 05 — Challenge Content Blueprint

## Challenge philosophy

Each challenge should feel like a real junior developer ticket, not a textbook exercise.

Good challenge format:

- Context from a fake company
- Clear ticket goal
- Existing broken or incomplete code
- Tests that reveal expected behavior
- Production concept being taught
- AI hints
- Validation criteria
- Reflection/learning summary

## Challenge YAML format

See `templates/challenge.yaml`.

## Example challenge

```yaml
id: fastapi-orders-invalid-coupon
title: "Fix invalid coupon handling"
track: backend-production-python
module: api-debugging
difficulty: beginner-plus

scenario: >
  The commerce API is accepting invalid coupon codes.
  Support has reported that customers can submit random codes
  and still receive a discount.

learner_goal: >
  Update the order creation flow so invalid coupon codes are rejected
  with a clear 400 response.

repo:
  template: github.com/prodready/templates-fastapi-commerce
  branch: challenge-invalid-coupon

visible_checks:
  - pytest tests/test_orders.py::test_invalid_coupon_rejected

hidden_checks:
  - pytest tests/hidden/test_coupon_edge_cases.py

skills:
  - fastapi
  - debugging
  - api-validation
  - pytest
  - production-error-handling

ai_rules:
  max_hint_level: 3
  do_not_reveal_solution: true
  encourage_tests_first: true
```

## First track outline

### Track: Backend Production Developer

#### Module 1 — Working like a developer

1. Open a repo.
2. Run the app.
3. Read project structure.
4. Make a small code change.
5. Run tests.

#### Module 2 — Debugging APIs

6. Fix a failing endpoint.
7. Add input validation.
8. Handle missing data.
9. Return correct HTTP status codes.
10. Improve error messages.

#### Module 3 — Testing

11. Run pytest.
12. Write a unit test.
13. Write an API test.
14. Fix a flaky test.
15. Understand fixtures.

#### Module 4 — Databases

16. Add a database column.
17. Write a migration.
18. Fix a broken query.
19. Add pagination.
20. Handle duplicate records.

#### Module 5 — Git and PRs

21. Create a branch.
22. Make a clean commit.
23. Resolve a merge conflict.
24. Open a PR.
25. Respond to code review.

#### Module 6 — Docker and environments

26. Fix missing environment variables.
27. Debug Docker startup failure.
28. Update docker-compose.
29. Connect API to PostgreSQL.
30. Explain local vs production config.

#### Module 7 — CI/CD

31. Read a GitHub Actions failure.
32. Fix lint failure.
33. Fix CI-only test failure.
34. Add a CI step.
35. Understand deployment gates.

#### Module 8 — Production readiness

36. Add logging.
37. Add health checks.
38. Avoid leaking secrets.
39. Handle rate-limit style errors.
40. Final capstone.

## MVP content cut

For MVP, create only 10 high-quality challenges. Do not write 40 mediocre ones.

Quality beats quantity.
