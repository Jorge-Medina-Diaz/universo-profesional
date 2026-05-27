#!/usr/bin/env bash
#
# Truncate ESCO tables and re-seed from scratch.
#
# Usage:
#   ./scripts/reset-esco.sh

set -euo pipefail

echo "[reset-esco] clearing ontology graph and tables..."
docker compose exec backend python -c "
import asyncio
from sqlalchemy import text
from src.shared.db import get_session_factory, dispose_engine
from src.graph.infrastructure.age_client import cypher, ensure_age_loaded

async def clear():
    factory = get_session_factory()
    async with factory() as session:
        await ensure_age_loaded(session)
        await cypher(session, 'universe_ontology', 'MATCH (n) DETACH DELETE n')
        await session.execute(text('TRUNCATE ontology_embeddings, ontology_search, graph_ingest_meta'))
        await session.commit()

asyncio.run(clear())
asyncio.run(dispose_engine())
"

echo "[reset-esco] re-seeding..."
./scripts/seed-esco.sh --force

echo "[reset-esco] done."
