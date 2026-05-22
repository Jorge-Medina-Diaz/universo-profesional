#!/usr/bin/env bash
#
# Daily Postgres backup → S3-compatible object storage.
#
# Requirements:
#   * `pg_dump` available on PATH (apt install postgresql-client).
#   * `rclone` configured with a remote called `r2` (or whatever).
#   * `DATABASE_URL_SYNC` env var set in the cron env (cron doesn't read
#     your shell profile — put it in the crontab line directly or here).
#
# Retention: we keep `latest.sql.gz` always, plus 30 daily snapshots
# (YYYYMMDD.sql.gz). Rclone's `--max-age` on `delete` does the housekeeping.

set -euo pipefail

: "${DATABASE_URL_SYNC:?DATABASE_URL_SYNC required}"
: "${BACKUP_REMOTE:=r2:cvs-saas-backups/postgres}"

DATE=$(date -u +%Y%m%d)
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

DUMP="$TMPDIR/cvs-${DATE}.sql.gz"

echo "[backup] dumping..."
pg_dump --format=plain --no-owner --no-privileges "$DATABASE_URL_SYNC" | gzip -9 > "$DUMP"
SIZE=$(stat -c%s "$DUMP" 2>/dev/null || stat -f%z "$DUMP")
echo "[backup] dump size: $SIZE bytes"

echo "[backup] uploading dated + latest..."
rclone copyto "$DUMP" "$BACKUP_REMOTE/cvs-${DATE}.sql.gz"
rclone copyto "$DUMP" "$BACKUP_REMOTE/latest.sql.gz"

echo "[backup] pruning >30d snapshots..."
rclone delete "$BACKUP_REMOTE" --min-age 30d --include "cvs-*.sql.gz" || true

echo "[backup] done."
