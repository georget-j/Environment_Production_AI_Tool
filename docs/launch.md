# Launch playbook

Operational reference for taking the MVP from `main` → live → "first paying user". Read [.claude/plans/i-have-created-a-mutable-rain.md](.claude/plans/i-have-created-a-mutable-rain.md) for the why; this doc is the what and how.

## Environments

| Env | Web | API | DB / Auth |
|---|---|---|---|
| Local | `pnpm dev:web` (3000) | `scripts/dev.sh` (8000) | `supabase start` (54322) |
| Staging | Vercel preview (per-PR) | Fly.io app `prodready-api-staging` | Supabase project `prodready-staging` |
| Prod | Vercel main domain | Fly.io app `prodready-api` | Supabase project `prodready` |

## Environment variables

Set the same keys in each env; only values change.

### Web (Vercel project)
```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_API_BASE_URL
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
SUPABASE_SERVICE_ROLE_KEY          # only for server-component reads, never exposed
API_BASE_URL                        # server-component → api
```

### API (Fly.io app secrets)
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET                # used to verify learner JWTs (HS256)
DATABASE_URL                       # Supabase Postgres connection string
OPENAI_API_KEY
OPENAI_MODEL_CHAT                  # default: gpt-4o-mini
OPENAI_MODEL_REVIEW                # default: gpt-4o
STRIPE_SECRET_KEY                  # sk_test_… in staging, sk_live_… in prod
STRIPE_WEBHOOK_SECRET              # whsec_…
STRIPE_PRICE_PRO_MONTHLY           # price_…
CORS_ORIGINS                       # JSON list, e.g. ["https://prodready.ai"]
```

### Stripe → API webhook URL
- Staging: `https://prodready-api-staging.fly.dev/api/billing/webhook`
- Prod: `https://api.prodready.ai/api/billing/webhook`

Events to subscribe (Stripe dashboard → Webhooks → Add endpoint):
- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## First deploy

```bash
# 1. Supabase
supabase projects create prodready-staging
supabase link --project-ref <ref>
supabase db push           # applies migrations
psql "$SUPABASE_DB_URL" -f supabase/seed.sql

# 2. API (Fly.io)
fly launch --name prodready-api-staging --dockerfile apps/api/Dockerfile --no-deploy
fly secrets set SUPABASE_URL=... SUPABASE_JWT_SECRET=...  # all the keys above
fly deploy

# 3. Web (Vercel)
cd apps/web
vercel link
vercel env add NEXT_PUBLIC_SUPABASE_URL  # repeat for each
vercel --prod

# 4. Wire Stripe webhook in dashboard (URL above)
```

## Going from test mode → live

1. In Stripe, switch to live mode and grab `sk_live_…` + a new `whsec_…`.
2. Create the Pro product + `price_live_…`.
3. `fly secrets set STRIPE_SECRET_KEY=sk_live_… STRIPE_WEBHOOK_SECRET=whsec_… STRIPE_PRICE_PRO_MONTHLY=price_live_… -a prodready-api`
4. Update the live webhook endpoint URL in Stripe to prod.
5. Trigger one test purchase with a real card; verify `subscription_status` flips to `active` in Supabase Studio.

## Smoke test

```bash
API_BASE=https://prodready-api-staging.fly.dev \
  WEB_BASE=https://prodready-staging.vercel.app \
  bash scripts/smoke.sh
```

Returns non-zero on any failure. Run this after every staging deploy.

## Rollback

API: `fly releases -a prodready-api` then `fly deploy --image registry.fly.io/prodready-api:v<N-1>`.
Web: Vercel → Deployments → click the previous green deploy → Promote.
DB: Supabase migrations are forward-only for MVP. Hand-write a revert SQL file if needed; do not auto-rollback schema.

## Observability (MVP minimum)

- Vercel logs (web) and Fly logs (api): keep open during launch.
- Supabase Studio → table editor: spot-check `submissions`, `ai_messages`, `users.subscription_status`.
- OpenAI usage dashboard: watch daily cost; flip `OPENAI_MODEL_CHAT` to `gpt-4o-mini` (already default) and reduce history window in `apps/api/app/routers/ai.py` if cost exceeds £3/active-user/month.

## Pre-launch checklist

- [ ] `pnpm test` and `pytest` green locally
- [ ] `.github/workflows/ci.yml` green on `main`
- [ ] `supabase db reset` applies migrations + seed cleanly
- [ ] `scripts/smoke.sh` passes against staging
- [ ] One end-to-end manual run: signup → start free challenge → mentor chat → submit → AI review renders → progress marked complete
- [ ] One end-to-end manual run: signup → click Upgrade → pay with `4242 4242 4242 4242` → access a Pro challenge
- [ ] Privacy + terms pages live (placeholders OK for MVP, real copy before paid launch)
- [ ] Analytics events firing (PostHog or Plausible — decide and wire before MVP launch)
- [ ] Stripe live keys swapped in and one real card tested
