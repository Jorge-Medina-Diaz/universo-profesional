# Backup & restore

## Strategy

- **Postgres**: daily logical dump to S3-compatible (Cloudflare R2 by default).
  Fly.io managed Postgres also keeps automated snapshots for 7 days — those
  are the fast-recovery layer; logical dumps are the long-tail / off-Fly safety net.
- **Storage volume** (`/app/var`): contains JWT private/public keys + uploaded
  photos + generated PDFs. We snapshot this volume daily (Fly volumes) AND
  the JWT keys themselves get backed up encrypted to R2 weekly so we can
  rebuild a fresh app if the volume is lost.
- **Redis**: NOT backed up. The only durable state in Redis is the Arq queue;
  we accept losing in-flight jobs in the worst case.

## Restore-from-dump

```bash
# 1. Provision a fresh Postgres (managed or local).
# 2. Pull the latest dump from R2.
rclone copy r2:cvs-saas-backups/postgres/latest.sql.gz .
# 3. Restore.
gunzip latest.sql.gz | psql "$DATABASE_URL_SYNC"
# 4. Re-apply migrations (idempotent — `alembic upgrade head` is safe to re-run).
alembic upgrade head
# 5. Smoke test:
curl -fsS https://api.universo.pro/readyz
```

## Cron — `scripts/backup.sh`

Add this to your host (cron / Fly Machine scheduled task / GitHub Actions
cron). The script is in `scripts/backup.sh` — make sure `rclone` is
configured with an R2 token and the `DATABASE_URL_SYNC` env var is set:

```cron
# Every day at 03:30 UTC
30 3 * * * /home/cvs/cvs-saas/scripts/backup.sh >> /var/log/cvs-backup.log 2>&1
```

## Point-in-time recovery (PITR)

Fly Postgres v2 keeps continuous WAL archives for 7 days. To restore to a
specific timestamp:

```bash
flyctl postgres restore --app cvs-saas-db --backup-id <id> --target-time '2026-05-20T10:15:00Z'
```

(Substitute your Fly Postgres provider's UI/CLI if you're not on Fly.)

## Embedding indexes

pgvector HNSW indexes are recreated on restore. They take ~minutes per
million rows. Monitor with:

```sql
SELECT count(*) FROM educations WHERE embedding IS NOT NULL;
```

If you need to rebuild from scratch (different model dimension, etc.),
queue a `refresh_embedding` Arq job per entity — the worker handles it
without blocking the app.
