"""Unit tests for the Discovery Progress service."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from src.graph.domain import schema as graph_schema
from src.universe.application.discovery_service import DiscoveryProgressService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_counts():
    """Return a counts dict with all known kinds set to 0."""
    return dict.fromkeys(graph_schema.KIND_TO_LABEL, 0)


def _scalar_result(value):
    m = MagicMock()
    m.scalar.return_value = value
    m.mappings.return_value.all.return_value = []
    return m


def _rows_result(rows):
    m = MagicMock()
    m.scalar.return_value = None
    m.mappings.return_value.all.return_value = rows
    return m


def _make_mock_session(
    counts,
    recent_rows,
    source_rows,
    last_24h_count,
    esco_rows,
    last_activity,
):
    """Return an AsyncMock session with ordered side-effects.

    DiscoveryProgressService.get_progress() calls execute() in a fixed order:
    1. One count query per kind in KIND_TO_LABEL
    2. Recent discoveries (last 7 days)
    3. Source breakdown (GROUP BY source)
    4. Activity last 24h
    5. ESCO linking stats
    6. Last activity timestamp
    """
    session = AsyncMock()
    results = []

    # 1. Per-kind count queries
    for kind in graph_schema.KIND_TO_LABEL:
        results.append(_scalar_result(counts.get(kind, 0)))

    # 2. Recent discoveries
    results.append(_rows_result(recent_rows))

    # 3. Source breakdown
    results.append(_rows_result(source_rows))

    # 4. Activity last 24h
    results.append(_scalar_result(last_24h_count))

    # 5. ESCO linking stats
    results.append(_rows_result(esco_rows))

    # 6. Last activity timestamp
    results.append(_scalar_result(last_activity))

    session.execute.side_effect = results
    return session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_id():
    return UUID(str(uuid4()))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiscoveryProgressCounts:
    async def test_returns_correct_counts_and_total(self, user_id):
        counts = _empty_counts()
        counts.update(
            {
                "experience": 2,
                "education": 1,
                "skill": 5,
                "project": 1,
                "language": 1,
            }
        )
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["counts"] == counts
        assert result["total_entities"] == 10
        assert result["kinds_present"] == 5

    async def test_empty_profile_returns_zeros(self, user_id):
        counts = _empty_counts()
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["total_entities"] == 0
        assert result["kinds_present"] == 0
        assert result["discovery_score"] == 0


class TestDiscoveryProgressCoverage:
    async def test_coverage_at_target_is_one(self, user_id):
        counts = _empty_counts()
        counts.update(
            {
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
        )
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["coverage"]["experience"] == 1.0
        assert result["coverage"]["skill"] == 1.0
        assert result["coverage"]["language"] == 1.0

    async def test_coverage_capped_at_one(self, user_id):
        counts = _empty_counts()
        counts["experience"] = 10
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["coverage"]["experience"] == 1.0

    async def test_sparse_dimensions_lists_low_coverage(self, user_id):
        counts = _empty_counts()
        counts["skill"] = 1  # coverage = 1/10 = 0.1 < 0.5 → sparse
        counts["experience"] = 2  # coverage = 2/3 = 0.66 >= 0.5 → not sparse
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert "skill" in result["sparse_dimensions"]
        assert "experience" not in result["sparse_dimensions"]


class TestDiscoveryProgressScore:
    async def test_base_score_from_coverage(self, user_id):
        counts = _empty_counts()
        counts.update(
            {
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
        )
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        # All 9 tracked kinds at 1.0 coverage → base = 60
        assert result["score_breakdown"]["base"] == 60
        assert result["score_breakdown"]["recency"] == 0
        assert result["score_breakdown"]["diversity"] == 10  # ≥5 kinds
        assert result["score_breakdown"]["esco"] == 0
        assert result["discovery_score"] == 70

    async def test_recency_bonus_last_24h(self, user_id):
        counts = _empty_counts()
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=3,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["score_breakdown"]["recency"] == 20
        assert result["activity_last_24h"] == 3
        assert result["is_alive"] is True

    async def test_recency_bonus_last_7d_only(self, user_id):
        counts = _empty_counts()
        # No 24h activity, but some recent discoveries in the last 7 days
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[
                {
                    "entity_type": "skill",
                    "change_type": "created",
                    "source": "chat",
                    "changed_at": datetime.now(UTC) - timedelta(days=2),
                }
            ],
            source_rows=[{"source": "chat", "n": 1}],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["score_breakdown"]["recency"] == 10
        assert result["is_alive"] is False

    async def test_recency_bonus_no_activity(self, user_id):
        counts = _empty_counts()
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["score_breakdown"]["recency"] == 0

    async def test_diversity_bonus_five_or_more(self, user_id):
        counts = _empty_counts()
        counts.update(dict.fromkeys(graph_schema.KIND_TO_LABEL, 1))
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["score_breakdown"]["diversity"] == 10

    async def test_diversity_bonus_three_to_four(self, user_id):
        counts = _empty_counts()
        counts.update({"experience": 1, "education": 1, "skill": 1})
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["kinds_present"] == 3
        assert result["score_breakdown"]["diversity"] == 5

    async def test_diversity_bonus_below_three(self, user_id):
        counts = _empty_counts()
        counts["experience"] = 1
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["kinds_present"] == 1
        assert result["score_breakdown"]["diversity"] == 0

    async def test_esco_bonus_capped_at_ten(self, user_id):
        counts = _empty_counts()
        esco_rows = [{"target_label": "EscoSkill", "n": 30}]
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=esco_rows,
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["score_breakdown"]["esco"] == 10  # min(10, 30/2)

    async def test_discovery_score_capped_at_100(self, user_id):
        counts = _empty_counts()
        counts.update(dict.fromkeys(graph_schema.KIND_TO_LABEL, 5))
        counts["skill"] = 15  # ensure skill coverage = 1.0 (target = 10)
        esco_rows = [{"target_label": "EscoSkill", "n": 100}]
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=5,
            esco_rows=esco_rows,
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["discovery_score"] == 100


class TestDiscoveryProgressRecentDiscoveries:
    async def test_recent_discoveries_filtered_by_time(self, user_id):
        now = datetime.now(UTC)
        recent_rows = [
            {
                "entity_type": "skill",
                "change_type": "created",
                "source": "chat",
                "changed_at": now - timedelta(days=1),
            },
            {
                "entity_type": "experience",
                "change_type": "updated",
                "source": "import",
                "changed_at": now - timedelta(days=6),
            },
        ]
        counts = _empty_counts()
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=recent_rows,
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert len(result["recent_discoveries"]) == 2
        assert result["recent_discoveries"][0]["entity_type"] == "skill"
        assert result["recent_discoveries"][1]["entity_type"] == "experience"

    async def test_recent_discoveries_include_iso_timestamps(self, user_id):
        now = datetime.now(UTC)
        recent_rows = [
            {
                "entity_type": "skill",
                "change_type": "created",
                "source": "chat",
                "changed_at": now,
            }
        ]
        counts = _empty_counts()
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=recent_rows,
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["recent_discoveries"][0]["changed_at"] == now.isoformat()

    async def test_sources_last_7d_aggregated(self, user_id):
        counts = _empty_counts()
        source_rows = [
            {"source": "chat", "n": 5},
            {"source": "import", "n": 2},
        ]
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=source_rows,
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["sources_last_7d"] == {"chat": 5, "import": 2}

    async def test_last_activity_at_present(self, user_id):
        now = datetime.now(UTC)
        counts = _empty_counts()
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=now,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["last_activity_at"] == now.isoformat()

    async def test_last_activity_at_none_when_empty(self, user_id):
        counts = _empty_counts()
        mock_session = _make_mock_session(
            counts=counts,
            recent_rows=[],
            source_rows=[],
            last_24h_count=0,
            esco_rows=[],
            last_activity=None,
        )

        svc = DiscoveryProgressService(mock_session)
        result = await svc.get_progress(user_id)

        assert result["last_activity_at"] is None
