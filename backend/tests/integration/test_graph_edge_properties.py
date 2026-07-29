"""An edge must carry its properties from the moment it is created.

Apache AGE 1.5 silently drops a `SET` that follows a `MERGE` which *creates*
a relationship — the edge appears with `properties: {}`. Node `MERGE` is not
affected, which is why this hid for so long: vertices looked fine.

The blast radius is the whole bi-temporal model. An edge born without
`source`, `valid_from` or `confidence` is invisible to every maintenance pass
that filters on them — most importantly the enrichment expiry step, which
matches `r.source = 'inferred'`. Stale inferred edges could therefore never be
expired, and only started carrying properties if a later run happened to
re-MERGE (and thus MATCH) the same pair.

Requires a real AGE database — a mock cannot reproduce an AGE quirk.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.graph.application.ports.age import cypher as age_cypher
from src.graph.application.ports.age import parse_agtype
from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema
from src.shared.db import get_session_factory

pytestmark = [pytest.mark.integration, pytest.mark.requires_age]


@pytest_asyncio.fixture
async def db_session(_app) -> AsyncIterator[AsyncSession]:
    """A session with RLS bypassed, rolled back so AGE keeps no residue.

    Depends on `_app` because the AGE port functions are wired at app import;
    without it `age_cypher` is still None.
    """
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("SET LOCAL app.bypass_rls = 'on'"))
        try:
            yield session
        finally:
            await session.rollback()


async def _edge_properties(session, user_id) -> list[dict]:
    rows = await age_cypher(
        session,
        schema.GRAPH_PERSONAL,
        "MATCH (a {user_id: $uid})-[r:RELATED_TO]->(b {user_id: $uid}) RETURN r",
        params={"uid": str(user_id)},
        column_defs="r agtype",
    )
    return [parse_agtype(row["r"])["properties"] for row in rows]


async def _make_edge(session, *, user_id, src, dst, source="inferred", confidence=0.77):
    for eid in (src, dst):
        await universe_graph_service.upsert_entity(
            session, entity_id=eid, user_id=user_id, kind="skill", source="seed"
        )
    return await universe_graph_service.upsert_edge(
        session,
        edge_type=schema.RELATED_TO,
        source_id=src,
        target_id=dst,
        user_id=user_id,
        source=source,
        confidence=confidence,
    )


@pytest.mark.asyncio
async def test_edge_carries_properties_on_first_create(db_session) -> None:
    """The regression: properties must exist after ONE upsert, not two."""
    user_id, src, dst = uuid4(), uuid4(), uuid4()
    assert await _make_edge(db_session, user_id=user_id, src=src, dst=dst) is True

    props = await _edge_properties(db_session, user_id)
    assert len(props) == 1, f"expected exactly one edge, got {len(props)}"
    p = props[0]
    assert p.get("source") == "inferred", f"source lost on create: {p}"
    assert p.get("confidence") == 0.77, f"confidence lost on create: {p}"
    assert p.get("valid_from"), f"valid_from lost on create — bi-temporal broken: {p}"
    assert p.get("created_at"), f"created_at lost on create: {p}"


@pytest.mark.asyncio
async def test_freshly_created_edge_is_expirable(db_session) -> None:
    """The user-visible consequence: the enrichment expiry pass filters on
    `source = 'inferred'`, so an edge born without `source` can never expire."""
    user_id, src, dst = uuid4(), uuid4(), uuid4()
    await _make_edge(db_session, user_id=user_id, src=src, dst=dst)

    # Exactly the expiry statement from _infer_semantic_edges.
    await age_cypher(
        db_session,
        schema.GRAPH_PERSONAL,
        "MATCH (a {user_id: $uid})-[r:RELATED_TO]->(b {user_id: $uid}) "
        "WHERE r.valid_to IS NULL AND r.source = 'inferred' SET r.valid_to = $now",
        params={"uid": str(user_id), "now": "2026-07-29T00:00:00+00:00"},
    )

    props = await _edge_properties(db_session, user_id)
    assert props[0].get("valid_to") == "2026-07-29T00:00:00+00:00", (
        f"edge did not expire — the expiry filter could not see it: {props[0]}"
    )


@pytest.mark.asyncio
async def test_upsert_is_idempotent_and_updates_in_place(db_session) -> None:
    """Re-upserting the same pair must update, not duplicate."""
    user_id, src, dst = uuid4(), uuid4(), uuid4()
    await _make_edge(db_session, user_id=user_id, src=src, dst=dst, confidence=0.5)
    await _make_edge(db_session, user_id=user_id, src=src, dst=dst, confidence=0.9)

    props = await _edge_properties(db_session, user_id)
    assert len(props) == 1, f"upsert duplicated the edge: {len(props)} edges"
    assert props[0].get("confidence") == 0.9


@pytest.mark.asyncio
async def test_upsert_edge_reports_missing_endpoints(db_session) -> None:
    """A dangling reference must return False, not silently create nothing."""
    user_id = uuid4()
    ok = await universe_graph_service.upsert_edge(
        db_session,
        edge_type=schema.RELATED_TO,
        source_id=uuid4(),  # never created
        target_id=uuid4(),
        user_id=user_id,
        source="inferred",
    )
    assert ok is False
