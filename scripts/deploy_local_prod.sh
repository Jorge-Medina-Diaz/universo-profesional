#!/usr/bin/env bash
# Local production deploy: immutable images, nginx frontend, RLS-subject role.
#
# Usage (from repo root, git-bash/WSL):
#   bash scripts/deploy_local_prod.sh
#
# The dev stack must be DOWN first (container names collide):
#   docker compose down
#
# Project name cvs-prod => fresh named volumes (cvs-prod_postgres_data...);
# the dev volumes are untouched.
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml -p cvs-prod --env-file .env.production"
APP_PW=$(grep '^CVS_APP_PASSWORD=' .env.production | cut -d= -f2)
[ -n "$APP_PW" ] || { echo "CVS_APP_PASSWORD missing from .env.production"; exit 1; }

echo "[1/6] postgres + redis"
$COMPOSE up -d postgres redis
for i in $(seq 1 30); do
  docker exec cvs-postgres pg_isready -U cvs -d cvs >/dev/null 2>&1 && break
  sleep 2
done

echo "[2/6] migrations (as owner role cvs)"
SYNC_URL=$(grep '^DATABASE_URL_SYNC=' .env.production | cut -d= -f2-)
MSYS_NO_PATHCONV=1 docker run --rm --network cvs-prod_default \
  -e DATABASE_URL_SYNC="$SYNC_URL" -e PYTHONPATH=/app -w /app \
  --entrypoint python cvs-saas-backend:latest -m alembic upgrade head

echo "[3/6] provision cvs_app (RLS-subject runtime role)"
docker exec -i cvs-postgres psql -U cvs -d cvs -v ON_ERROR_STOP=1 \
  < backend/scripts/provision_app_role.sql >/dev/null
docker exec cvs-postgres psql -U cvs -d cvs \
  -c "ALTER ROLE cvs_app PASSWORD '$APP_PW';" >/dev/null

echo "[4/6] ESCO ontology seed (sample, as owner role — creates AGE labels)"
OWNER_ASYNC_URL=$(echo "$SYNC_URL" | sed -E 's#^postgresql(\+psycopg)?://#postgresql+asyncpg://#')
MSYS_NO_PATHCONV=1 docker run --rm --network cvs-prod_default \
  --env-file .env.production -e DATABASE_URL="$OWNER_ASYNC_URL" \
  -e PYTHONPATH=/app -w /app \
  --entrypoint python cvs-saas-backend:latest -m scripts.seed_esco --sample-only

echo "[5/6] full stack"
$COMPOSE up -d

echo "[6/6] smoke"
for i in $(seq 1 30); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz || true)
  [ "$CODE" = "200" ] && break
  sleep 3
done
echo "  backend  /healthz: $CODE"
curl -s http://localhost:8000/readyz | head -c 300; echo
echo "  frontend: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/)"
echo
echo "Done. App: http://localhost:8080 — emails (verification): http://localhost:8025"
