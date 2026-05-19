# fastapi-commerce

Template repo for the **Backend Production Developer** track on ProdReady AI.

A tiny FastAPI commerce service with PostgreSQL, Docker Compose, pytest, ruff, and GitHub Actions. Every ProdReady challenge in Module 1 is implemented as a branch of this repo; learners fork it once and switch branches per challenge.

## Quickstart

```bash
# 1. Start Postgres
docker compose up -d

# 2. Install deps (use a venv)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Run tests
pytest -q
```

You should see all tests pass on `main`. Each challenge branch (`challenge-fix-failing-test`, `challenge-invalid-coupon`, …) intentionally introduces a bug.

## Repo layout

```text
app/
  __init__.py
  main.py          # FastAPI app + routers
  orders.py        # order creation + total calculation
  coupons.py       # coupon validation
  models.py        # in-memory store for the MVP
tests/
  test_orders.py
  test_coupons.py
.devcontainer/
  devcontainer.json
.github/workflows/
  validate.yml     # runs ruff + pytest on every push
docker-compose.yml # local Postgres
requirements.txt
requirements-dev.txt
```

The `models.py` store is intentionally in-memory for the MVP — challenges focus on API workflow, not persistence. Database challenges arrive later in Module 4.

## Challenge branches

| Branch | What's broken |
|---|---|
| `main` | Nothing — green CI |
| `challenge-fix-failing-test` | `app/orders.py::compute_total` has the wrong precedence |
| `challenge-invalid-coupon` | `app/coupons.py::is_valid` returns True for any code |

## CI

[`.github/workflows/validate.yml`](.github/workflows/validate.yml) runs on every push: ruff + pytest. The ProdReady platform reads this status to mark submissions pass/fail once the GitHub App integration ships (roadmap upgrade #1).
