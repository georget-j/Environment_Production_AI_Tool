# Cost guards — keeping the monthly bill bounded

Target: **~$10/month** combined across Fly + OpenAI.

## What protects us

### 1. Fly: machine count & runtime

- `apps/api/fly.toml` pins `max_machines_running = 1`. Fly cannot autoscale past one
  machine, even under load. Concurrency limits (`soft_limit = 20`, `hard_limit = 25`)
  make Fly's proxy queue/shed traffic instead of spinning up replicas.
- `auto_stop_machines = 'stop'` + `min_machines_running = 0` means the machine stops
  when idle. Cost ~= runtime. The first request after idle eats a ~5s cold start.
- No warm-keep cron. We deliberately accept cold starts in exchange for ~$0.30/mo Fly cost.

### 2. OpenAI: kill switch + per-user daily quotas

Implemented in `apps/api/app/cost_guard.py`, called from every AI route.

**Kill switch** — flips all AI endpoints to HTTP 503 in one Fly command:

```bash
flyctl secrets set AI_KILL_SWITCH=true --app prodready-api
# To resume:
flyctl secrets unset AI_KILL_SWITCH --app prodready-api
```

**Per-user daily quotas** (UTC day, counted from `ai_messages` table):
| Endpoint | Default cap/day/user | Override env |
|---|---|---|
| `POST /api/ai/chat` | 50 | `AI_DAILY_CHAT_LIMIT` |
| `POST /api/ai/show-answer` | 10 | `AI_DAILY_SHOW_ANSWER_LIMIT` |
| `POST /api/ai/explain-tests` | 30 | `AI_DAILY_EXPLAIN_LIMIT` |

Setting any limit to `0` disables that endpoint with a 503.

### 3. OpenAI hard cap (manual — do this once)

Code can't enforce a cap on the OpenAI account itself. Set one on the dashboard:

1. https://platform.openai.com/account/limits
2. Set **Hard limit: $10** and **Soft limit (email alert): $5**.
3. When hit, OpenAI returns 429s and our routes surface a 503.

### 4. Visibility

```bash
DATABASE_URL='postgresql://...' bash scripts/cost-check.sh
```

Prints Fly machine state, AI calls per day for the last 7 days, and the top 10
users by call volume. Run any time you want to know what's going on.

## Tuning the per-user limits

The defaults assume gpt-4o-mini for chat/explain and gpt-4o for show-answer:

```
chat:         50 calls × ~$0.0004 = ~$0.02/user/day
explain:      30 calls × ~$0.0006 = ~$0.018/user/day
show_answer:  10 calls × ~$0.020  = ~$0.20/user/day
                                    ────────────────
                                   ~$0.24/user/day cap
```

For ~30 daily-active users at the cap: ~$7/day, ~$210/month. To hit the $10/month
ceiling, that's roughly 1–2 active users/day at full quota — fine for early stage.

If a real cohort lands, raise the caps via env vars and watch `cost-check.sh`.

## What happens when a guard fires

- Kill switch on → every AI route returns 503 with `"AI features are temporarily disabled"`. The web app surfaces this in the mentor panel as an error banner.
- Quota hit → 429 with `"Daily limit reached for {kind} ({limit}/day)"`.
- Fly hard concurrency hit → Fly's edge returns 503; learners retry.
- Fly soft hit → Fly queues briefly; no learner-visible behaviour.

## Incident response

1. Open the Fly dashboard (https://fly.io/dashboard/personal). Confirm 1 machine.
2. Open the OpenAI usage dashboard (https://platform.openai.com/usage).
3. If spend is climbing: `flyctl secrets set AI_KILL_SWITCH=true --app prodready-api`.
4. Run `cost-check.sh` to find the offending user.
5. Investigate; lift the kill switch when safe.
