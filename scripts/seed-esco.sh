#!/usr/bin/env bash
#
# Manually trigger ESCO seed inside the backend container.
#
# Usage:
#   ./scripts/seed-esco.sh
#   ./scripts/seed-esco.sh --force
#   ./scripts/seed-esco.sh --sample-only

set -euo pipefail

CMD="python -m scripts.seed_esco"
if [ $# -gt 0 ]; then
  CMD="$CMD $*"
fi

echo "[seed-esco] running: $CMD"
docker compose exec backend bash -c "$CMD"
echo "[seed-esco] done."
