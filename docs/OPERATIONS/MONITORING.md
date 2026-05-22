# Monitoring

## Signals worth watching

### Error rate (Sentry)

| Threshold       | Action                                                |
|-----------------|-------------------------------------------------------|
| > 5 errors/min  | Slack alert (default)                                  |
| > 50 errors/min | PagerDuty (configure via Sentry → Alerts)              |
| New issue type  | Slack notification (Sentry "First seen" alert)         |

### Latency (`/metrics` Prometheus)

Endpoints to alert on (p99 > 2 s for 5 min):

- `POST /api/v1/documents/generate-cv` — LLM-bound, threshold 30 s
- `POST /agui/agent/*` — streaming, threshold 60 s (full turn)
- `POST /api/v1/integrations/linkedin/brightdata/sync-async` — should be < 1 s (enqueue)
- Everything else — threshold 500 ms

### Health checks

Fly.io probes `/readyz` every 15 s with a 5 s timeout. When 3 consecutive
checks fail, the machine restarts. Stack-trace appears in `flyctl logs`.

### Worker (Arq)

Look for these log lines:

- `j_complete=N` per hour — should be > 0 if the app is in use.
- `j_failed=N` — alert on `failed/complete > 0.1`.
- `j_ongoing` stays > 0 for hours — likely a stuck task; restart worker.

## Dashboards

- **Sentry**: project dashboards. The default "Issues" view is enough; add
  saved searches for `level:error environment:production`.
- **Fly.io**: built-in Grafana for memory/CPU/disk. Auto-emails on
  threshold breaches if you enable them.
- **Stripe**: subscription churn, MRR — built into the Stripe dashboard.

## Cost monitoring

- **Anthropic**: dashboard usage per day. Set a billing alert at $X.
- **Brevo**: free tier is 300 emails/day. The dashboard shows current
  usage; upgrade plan when approaching the cap.
- **Fly.io**: machine-hours per app on `flyctl scale show`. Cost graph
  in the Fly dashboard.

## SLO

We aim for:

| Service           | SLO                          | Window |
|-------------------|------------------------------|--------|
| Backend API       | 99.5% < 500 ms p95           | 30d    |
| LLM chat turn     | 95% < 10 s (first chunk)     | 30d    |
| Webhook ingestion | 100% delivered (Stripe retries) | 30d    |
| Worker queue lag  | < 60 s p99                   | 30d    |
