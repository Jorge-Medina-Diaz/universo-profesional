# Monitoring

## Signals worth watching

### Error rate (Sentry)

| Threshold       | Action                                                |
|-----------------|-------------------------------------------------------|
| > 5 errors/min  | Slack alert (default)                                  |
| > 50 errors/min | PagerDuty (configure via Sentry → Alerts)              |
| New issue type  | Slack notification (Sentry "First seen" alert)         |

### Latency (`/metrics` Prometheus)

RED metrics are exported per matched **route template** (never the raw path, so
cardinality stays bounded): `cvs_http_requests_total{method,route,status}` and
`cvs_http_request_duration_seconds{method,route}`. Alert on
`rate(cvs_http_requests_total{status=~"5.."}[5m])` and per-route p99 latency.

Endpoints to alert on (p99 > 2 s for 5 min):

- `POST /api/v1/documents/generate-cv` — LLM-bound, threshold 30 s
- `POST /agui/agent/*` — streaming, threshold 60 s (full turn)
- `POST /api/v1/integrations/linkedin/brightdata/sync-async` — should be < 1 s (enqueue)
- Everything else — threshold 500 ms

### Health checks

Fly.io probes `/readyz` every 15 s with a 5 s timeout. When 3 consecutive
checks fail, the machine restarts. Stack-trace appears in `flyctl logs`.

### Worker (Arq)

The worker initialises Sentry + OTel on startup, writes a Redis health key
every 30 s (probe with `arq --check src.shared.worker.WorkerSettings`, which the
container HEALTHCHECK now uses), and routes task exceptions through
`src.shared.worker_failures`: transient errors retry with bounded backoff;
terminal errors are captured to Sentry and re-raised — no longer swallowed as a
"successful" job. Watch:

- `cvs_task_runs_total{status="failed"}` — alert on
  `rate(cvs_task_runs_total{status="failed"}[15m]) > 0`; these also reach Sentry.
- `cvs_task_runs_total{status="retry"}` rising — a provider/network wobble.
- `j_failed=N` log lines / `j_ongoing` stuck > 0 for hours — restart worker.

> The worker's process metrics (`cvs_task_runs_total`) still need a scrape
> target — the embedded worker `/metrics` exporter is not yet wired (tracked in
> the roadmap), so until then these surface via Sentry + structured logs.

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
