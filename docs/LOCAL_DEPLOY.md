# Setup — run the whole stack locally

Everything runs in Docker with **no API keys and no accounts**. LLM, embeddings,
email, storage and payments all default to mocks, so a fresh clone boots offline
and every screen is reachable. Adding real providers later is one `.env` edit.

> This guide is in English because it is the one document a visitor has to read.
> Most other docs are in Spanish, the product's own language.

---

## 1. Requirements

- **Docker Desktop** (or Docker Engine) with Compose v2. Check: `docker compose version`.
- **~6 GB free disk** and **~4 GB RAM** available to Docker.
- Ports free on the host: `5173`, `8000`, `5432`, `6379`, `1025`, `8025`.

Nothing else — no local Python, Node or Postgres.

## 2. Start it

```bash
git clone https://github.com/Jorge-Medina-Diaz/universo-profesional.git
cd universo-profesional
cp .env.example .env
docker compose up -d --build
```

The first run builds a custom Postgres image (Postgres 16 + pgvector + Apache AGE
compiled in) and installs dependencies — budget **5–10 minutes**. Later runs take
seconds. To skip the Postgres build entirely, point `POSTGRES_IMAGE` at a prebuilt
tag (see [`.github/workflows/publish-postgres.yml`](../.github/workflows/publish-postgres.yml)).

**Migrations and seed data run themselves.** Compose brings services up in a
fixed order, and the app only starts once each step has finished:

```
postgres  →  migrate  →  db-bootstrap  →  seed  →  backend + worker + frontend
 (health)    (alembic     (creates the     (ESCO sample
             upgrade      cvs_app RLS      + 44 rubric
             head)        role + grants)   documents)
```

Watch it settle:

```bash
docker compose ps
docker compose logs -f backend
```

When `cvs-backend` reports healthy, open:

| | |
|---|---|
| **App** | <http://localhost:5173> |
| **API docs (Swagger)** | <http://localhost:8000/docs> |
| **Inbox (MailHog)** | <http://localhost:8025> |
| **Metrics (Prometheus)** | <http://localhost:8000/metrics> |

Health checks:

```bash
curl http://localhost:8000/healthz   # liveness
curl http://localhost:8000/readyz    # DB + Redis + JWT keys + LLM
```

`/readyz` should return `{"status":"ok","checks":{…}}`. If it says `degraded`, the
`checks` object names the failing dependency.

## 3. First login

1. Go to <http://localhost:5173/#/register> and create an account.
   Password policy: ≥10 characters, one uppercase, one digit, not a common password
   (e.g. `Welcome2026!`).
2. Open <http://localhost:8025>, find the verification email, click the link.
3. You land back in the app, logged in.

To skip the email step, set `AUTO_VERIFY_EMAILS_IN_DEV=true` in `.env` and
`docker compose up -d backend`.

**Want a populated graph immediately?** Seed a clearly-labelled fictional profile:

```bash
docker compose exec backend python -m scripts.seed_demo_twin
```

That creates ~29 entities and publishes a public twin at
<http://localhost:5173/#/t/demo>. Login: `demo-twin@universo.pro` / `VegaDemo-2026!seed`.

## 4. What works without any API key

| Area | Works | Notes |
|---|---|---|
| Auth (register, login, refresh, reset, MFA) | ✅ | Email via MailHog |
| Universe: entities, graph, semantic search | ✅ | `deterministic` embeddings, no OpenAI needed |
| CV + cover letter generation, 4 templates | ✅ | WeasyPrint renders locally |
| Document sharing, export PDF/DOCX/JSON Resume/Europass | ✅ | |
| Applications tracker (kanban) | ✅ | |
| LinkedIn ZIP import, PDF CV import | ✅ | Parsed locally |
| Billing | ✅ | Mock — Upgrade simulates the webhook |
| Reminders, suggestions, notifications | ✅ | No LLM needed |
| ESCO ontology + rubrics | ✅ | 200-occupation synthetic sample + 44 rubric documents, seeded automatically |
| Rate limiting, security headers, GDPR export/delete | ✅ | |
| **Agent chat** | ⚠️ | Needs a real LLM key — see below |

The chat is the one thing a mock cannot fake: the mock LLM deliberately refuses
rather than fabricating a profile for you.

## 5. Turning on real providers

Add keys to `.env` in the repo root, then re-apply:

```bash
docker compose up -d
```

Use `up -d`, not `restart`. `docker compose restart` reuses the existing
containers with the environment they were created with, so a `.env` edit appears
to do nothing; `up -d` recreates any container whose config changed.

Every key in `.env` reaches the containers. Container-internal values
(`DATABASE_URL`, `REDIS_URL`, `EMAIL_HOST`) are pinned in `docker-compose.yml` and
deliberately override `.env`, so the localhost defaults `.env.example` ships for
non-Docker runs cannot break the Docker setup.

### LLM — makes the chat work

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

That is the whole change. `AGENTS_PROVIDER` and `LLM_PROVIDER` auto-resolve from
`mock` to `anthropic` once a key is present; the same applies to `OPENAI_API_KEY`.
Keys: <https://console.anthropic.com/settings/keys>. A thorough test session costs
well under $1 — the coordinator's system prompt is prompt-cached.

### Embeddings — better semantic search

```env
OPENAI_API_KEY=sk-proj-...
```

`EMBEDDINGS_PROVIDER` auto-resolves `deterministic` → `openai`. The deterministic
provider is a real, stable hash embedding; search works without this, it is just
less semantically sharp.

### Everything else (all optional)

| Feature | Keys | Where to get them |
|---|---|---|
| Real email | `EMAIL_PROVIDER=brevo`, `BREVO_API_KEY` | <https://app.brevo.com/settings/keys/api> (300/day free) |
| Stripe checkout | `STRIPE_PROVIDER=real`, `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*` | <https://dashboard.stripe.com/test/apikeys> |
| GitHub sync | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` | <https://github.com/settings/developers> → callback `http://localhost:8000/api/v1/integrations/github/callback` |
| LinkedIn sign-in | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | <https://www.linkedin.com/developers/apps> → redirect `http://localhost:8000/api/v1/auth/linkedin/callback`, scopes `openid profile email` |
| Error tracking | `SENTRY_DSN`, `VITE_SENTRY_DSN` | Frontend Sentry only starts after the user accepts the diagnostics cookie bucket |

For Stripe webhooks locally: `stripe listen --forward-to http://localhost:8000/api/v1/billing/webhook`
prints the `whsec_...` to use as `STRIPE_WEBHOOK_SECRET`. Test card `4242 4242 4242 4242`.

Every available variable is documented in [`.env.example`](../.env.example).

## 6. Common commands

```bash
docker compose logs -f backend            # follow logs (also: worker, frontend)
docker compose up -d                      # pick up .env changes (restart will NOT)
docker compose down                       # stop, keep data
docker compose down -v                    # stop and DELETE all data
docker compose exec backend bash          # shell into the API
docker compose exec backend alembic upgrade head   # only needed after pulling new migrations
```

Migrations apply automatically on every `docker compose up`, so the manual
`alembic` command is only useful if you changed models while the stack was running.

## 7. Troubleshooting

**`docker compose up` exits immediately / postgres unhealthy.**
Check `docker compose logs postgres`. If the data volume was created by an older
build, reset it: `docker compose down -v && docker compose up -d --build`. This
deletes local data.

**Backend restart-loops with `password authentication failed for user "cvs_app"`.**
The `db-bootstrap` step did not complete. Run `docker compose logs db-bootstrap`,
then `docker compose up -d db-bootstrap` to retry. The app deliberately connects as
a non-superuser role that cannot bypass row-level security; see
[SECURITY_RLS_STATUS.md](SECURITY_RLS_STATUS.md).

**Backend restart-loops with `ModuleNotFoundError`.**
The image is stale: `docker compose build backend && docker compose up -d backend`.

**Frontend shows a blank page.**
`docker compose logs frontend`. On dependency errors: `docker compose exec frontend npm install`.

**`/readyz` returns `degraded`.**
Read the `checks` object — the entry with `error` names the broken dependency.

**"Invalid credentials" on login.**
Either the password fails the policy (≥10 chars, uppercase, digit, not common) or
the account is not verified — check MailHog at <http://localhost:8025>.

**Rate limited (`retry_after_seconds`).**
Wait, or set `RATE_LIMIT_ENABLED=false` in `.env` and restart the backend.

**Ports already in use.**
Something else is on `5432` or `8000`. Stop it, or edit the `ports:` mappings in
`docker-compose.yml`.

## 8. Where to go next

| | |
|---|---|
| Repo map, bounded contexts, test/lint commands | [../AGENTS.md](../AGENTS.md) |
| Production deploy (Fly.io or VPS) | [OPERATIONS/DEPLOYMENT.md](OPERATIONS/DEPLOYMENT.md) |
| Prod-flavoured stack on your own machine | [OPERATIONS/DEPLOY.md](OPERATIONS/DEPLOY.md) |
| How retrieval works | [architecture/graph-rag.md](architecture/graph-rag.md) |
| All documentation | [README.md](README.md) |
