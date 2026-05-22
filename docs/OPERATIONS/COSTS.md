# Cost estimation

Numbers are conservative ranges as of 2026-05. Re-check before quoting investors.

## Fixed infra (per month)

| Service                       | Tier               | Cost (€/mo)  |
|-------------------------------|--------------------|--------------|
| Fly.io backend (1 GB shared)  | machine-hours      | ~7           |
| Fly.io worker (1 GB shared)   | machine-hours      | ~7           |
| Fly.io frontend (256 MB)      | nginx, mostly idle | ~3           |
| Fly Postgres 10 GB            | shared-cpu-1x      | ~15          |
| Upstash Redis (256 MB)        | pay-per-request    | ~0–5         |
| Cloudflare R2 backups (5 GB)  | included free tier | 0            |
| **Subtotal**                  |                    | **~37**      |

## Per-user variable

Assumes a "typical" active user: 30 chat turns + 3 CVs + 1 LinkedIn sync per month.

### Anthropic Claude Sonnet 4.6
- ~5k input tokens × 30 turns × $3/M = $0.45
- ~1k output tokens × 30 turns × $15/M = $0.45
- With prompt caching: input cost drops ~70% → **~$0.30/user/month**

### Brevo emails
- Welcome + 2 reminders + 1 weekly digest = 4 emails
- Free tier: 300/day = ~9,000/month. **First ~2,250 users free.** Then $25/mo for 20k emails.

### Stripe fees
- 1.4% + €0.25 per transaction in EU
- On a €9.99 sub: **fee ≈ €0.39 per charge**

### BrightData (PRO-tier only)
- ~$0.50 per LinkedIn profile scrape
- Capped to 1/day per user via rate limit

## Per-user margin (Premium tier, €9.99)

| Item                | Cost          |
|---------------------|---------------|
| Stripe fee          | €0.39         |
| Anthropic           | €0.28 (~$0.30)|
| Brevo (amortised)   | €0.005        |
| Infra (amortised)   | €0.05 / user  |
| **Total cost**      | **~€0.73**    |
| **Net margin**      | **€9.26**     |

## Per-user margin (Pro tier, €19.99)

Pro users tend to use more (more CVs, BrightData syncs):

| Item                | Cost      |
|---------------------|-----------|
| Stripe fee          | €0.53     |
| Anthropic (3× usage)| €0.84     |
| BrightData (3 syncs)| €1.35     |
| Brevo               | €0.01     |
| Infra (amortised)   | €0.10     |
| **Total cost**      | **~€2.83**|
| **Net margin**      | **€17.16**|

## Break-even point

Fixed costs ~€37/mo + Sentry pro ~€26/mo + domain + misc ≈ **€80/mo**.

- 10 Premium users → break even.
- 5 Pro users → break even.

Tighter than it looks: don't go over budget on Anthropic by not setting
prompt caching + retry/backoff in the LLM client.
