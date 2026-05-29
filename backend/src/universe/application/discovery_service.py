"""Discovery progress calculation — shared between REST API and MCP tools."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph.domain import schema as graph_schema


class DiscoveryProgressService:
    """Calculate a user's discovery score and related metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_progress(self, user_id: UUID) -> dict[str, Any]:
        """Return full discovery progress payload."""
        uid = str(user_id)
        now = datetime.now(UTC)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        # 1. Counts per entity kind — read from the igraph snapshot of the
        # user's graph. Counting with `SELECT FROM universe_personal.<label>`
        # is WRONG: those are Apache AGE label tables — case-sensitive (the
        # label is `Experience`, not `experience`) and not created until the
        # first vertex of that label exists. A fresh user (e.g. mid-onboarding)
        # therefore 500s with `UndefinedTableError: relation
        # "universe_personal.experience" does not exist`. The snapshot reflects
        # the active vertices, is cached, and is shared with the retrieval lane.
        from collections import Counter

        from src.graph.application.retrieval import _load_snapshot

        snapshot = await _load_snapshot(self._session, user_id)
        kind_counter = Counter(
            meta[1] for meta in snapshot.idx_to_meta.values() if meta[1]
        )
        counts: dict[str, int] = {
            kind: kind_counter.get(kind, 0) for kind in graph_schema.KIND_TO_LABEL
        }

        total_entities = sum(counts.values())

        # 2. Coverage heuristic
        targets = {
            "experience": 3,
            "education": 2,
            "skill": 10,
            "project": 3,
            "certification": 2,
            "course": 3,
            "language": 2,
            "achievement": 2,
            "interest": 2,
        }
        coverage = {
            kind: min(1.0, counts.get(kind, 0) / target)
            for kind, target in targets.items()
        }
        sparse = [k for k, v in coverage.items() if v < 0.5]

        # 3. Discovery score (0-100)
        base_score = int((sum(coverage.values()) / len(coverage)) * 60)

        # 4. Recent activity from change_log
        recent_rows = (
            await self._session.execute(
                text("""
                    SELECT entity_type, change_type, source, changed_at
                    FROM universe_change_log
                    WHERE user_id = :uid AND changed_at >= :since
                    ORDER BY changed_at DESC
                    LIMIT 20
                """),
                {"uid": uid, "since": week_ago},
            )
        ).mappings().all()

        recent_discoveries = [
            {
                "entity_type": r["entity_type"],
                "change_type": r["change_type"],
                "source": r["source"],
                "changed_at": r["changed_at"].isoformat() if r["changed_at"] else None,
            }
            for r in recent_rows
        ]

        # 5. Source breakdown (last 7 days)
        source_rows = (
            await self._session.execute(
                text("""
                    SELECT source, count(*)::int AS n
                    FROM universe_change_log
                    WHERE user_id = :uid AND changed_at >= :since
                    GROUP BY source
                    ORDER BY n DESC
                """),
                {"uid": uid, "since": week_ago},
            )
        ).mappings().all()
        sources = {r["source"]: r["n"] for r in source_rows}

        # 6. Activity in last 24h
        last_24h = (
            await self._session.execute(
                text("""
                    SELECT count(*)::int AS n
                    FROM universe_change_log
                    WHERE user_id = :uid AND changed_at >= :since
                """),
                {"uid": uid, "since": day_ago},
            )
        ).scalar() or 0

        # 7. ESCO linking stats
        esco_rows = (
            await self._session.execute(
                text("""
                    SELECT target_label, count(*)::int AS n
                    FROM graph_esco_links
                    WHERE user_id = :uid
                    GROUP BY target_label
                """),
                {"uid": uid},
            )
        ).mappings().all()
        esco_links = {r["target_label"]: r["n"] for r in esco_rows}
        total_esco = sum(esco_links.values())

        # 8. Recency bonus
        recency_bonus = 20 if last_24h > 0 else (10 if len(recent_discoveries) > 0 else 0)

        # 9. Diversity bonus
        kinds_present = sum(1 for k, v in counts.items() if v > 0)
        diversity_bonus = 10 if kinds_present >= 5 else (5 if kinds_present >= 3 else 0)

        # 10. ESCO bonus
        esco_bonus = min(10, int(total_esco / 2))

        discovery_score = min(100, base_score + recency_bonus + diversity_bonus + esco_bonus)

        # 11. Last activity timestamp
        last_activity = (
            await self._session.execute(
                text("""
                    SELECT max(changed_at) AS last_at
                    FROM universe_change_log
                    WHERE user_id = :uid
                """),
                {"uid": uid},
            )
        ).scalar()

        return {
            "counts": counts,
            "total_entities": total_entities,
            "coverage": {k: round(v, 2) for k, v in coverage.items()},
            "sparse_dimensions": sparse,
            "discovery_score": discovery_score,
            "score_breakdown": {
                "base": base_score,
                "recency": recency_bonus,
                "diversity": diversity_bonus,
                "esco": esco_bonus,
            },
            "recent_discoveries": recent_discoveries,
            "sources_last_7d": sources,
            "activity_last_24h": last_24h,
            "esco_links": esco_links,
            "kinds_present": kinds_present,
            "last_activity_at": last_activity.isoformat() if last_activity else None,
            "is_alive": last_24h > 0,
        }
