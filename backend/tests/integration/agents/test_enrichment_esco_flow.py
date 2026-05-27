"""Integration tests: enrichment engine + ESCO linking flow.

These tests verify that UniverseEnrichmentEngine.process() wires the
entity extraction → upsert → ESCO linking pipeline correctly, and that
_link_to_esco behaves for success / failure / non-skill entities.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.agents.workflows.universe_enrichment import (
    ExtractedEntity,
    UniverseEnrichmentEngine,
)
from src.graph.application.esco_linker import LinkState
from src.graph.domain.esco_types import EscoLinkResult


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def engine(mock_session):
    return UniverseEnrichmentEngine(mock_session, uuid4())


# ---------------------------------------------------------------------------
# process() → _link_to_esco wiring
# ---------------------------------------------------------------------------

class TestProcessCallsLinkToEsco:
    async def test_process_calls_link_to_esco_for_skills(self, engine):
        ent_raw = json.dumps(
            [
                {"kind": "skill", "payload": {"name": "Python"}},
                {"kind": "experience", "payload": {"organization": "ACME", "role": "Dev"}},
            ]
        )
        rel_raw = json.dumps([])

        with patch.object(engine, "_call_llm", side_effect=[ent_raw, rel_raw]):
            with patch.object(engine, "_upsert_entity", return_value=uuid4()):
                with patch.object(
                    engine, "_link_to_esco", return_value=False
                ) as mock_link:
                    with patch(
                        "src.agents.workflows.universe_enrichment.universe_graph_service.upsert_edge",
                        new_callable=AsyncMock,
                    ):
                        with patch(
                            "src.universe.application.enrichment.enrich_user_graph",
                            new_callable=AsyncMock,
                        ):
                            await engine.process("I use Python at ACME")

        assert mock_link.await_count == 2
        # Both skill and experience should be linked
        kinds_linked = [call.args[0].kind for call in mock_link.await_args_list]
        assert "skill" in kinds_linked
        assert "experience" in kinds_linked

    async def test_process_counts_esco_linked(self, engine):
        ent_raw = json.dumps(
            [
                {"kind": "skill", "payload": {"name": "Python"}},
                {"kind": "skill", "payload": {"name": "Kubernetes"}},
            ]
        )
        rel_raw = json.dumps([])

        with patch.object(engine, "_call_llm", side_effect=[ent_raw, rel_raw]):
            with patch.object(engine, "_upsert_entity", return_value=uuid4()):
                with patch.object(
                    engine, "_link_to_esco", side_effect=[True, False]
                ):
                    with patch(
                        "src.agents.workflows.universe_enrichment.universe_graph_service.upsert_edge",
                        new_callable=AsyncMock,
                    ):
                        with patch(
                            "src.universe.application.enrichment.enrich_user_graph",
                            new_callable=AsyncMock,
                        ):
                            result = await engine.process("I know Python and Kubernetes")

        assert result.esco_linked == 1

    async def test_process_skips_esco_when_link_esco_false(self, engine):
        ent_raw = json.dumps(
            [{"kind": "skill", "payload": {"name": "Python"}}]
        )
        rel_raw = json.dumps([])

        with patch.object(engine, "_call_llm", side_effect=[ent_raw, rel_raw]):
            with patch.object(engine, "_upsert_entity", return_value=uuid4()):
                with patch.object(
                    engine, "_link_to_esco", return_value=True
                ) as mock_link:
                    with patch(
                        "src.agents.workflows.universe_enrichment.universe_graph_service.upsert_edge",
                        new_callable=AsyncMock,
                    ):
                        with patch(
                            "src.universe.application.enrichment.enrich_user_graph",
                            new_callable=AsyncMock,
                        ):
                            result = await engine.process("I know Python", link_esco=False)

        mock_link.assert_not_awaited()
        assert result.esco_linked == 0


# ---------------------------------------------------------------------------
# _link_to_esco success / failure cases
# ---------------------------------------------------------------------------

class TestLinkToEscoSuccessCases:
    async def test_link_to_esco_success_for_skill(self, engine):
        ent = ExtractedEntity(kind="skill", payload={"name": "Python"})
        entity_id = uuid4()

        mock_result = EscoLinkResult(
            state=LinkState.LINKED,
            esco_uri="http://data.europa.eu/esco/skill/python",
            score=0.92,
        )

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock(return_value=mock_result)
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            with patch(
                "src.agents.workflows.universe_enrichment.universe_graph_service._execute_cypher",
                new_callable=AsyncMock,
            ) as mock_cypher:
                linked = await engine._link_to_esco(ent, entity_id)

        assert linked is True
        mock_linker.link.assert_awaited_once_with(
            engine._session,
            text_in="Python",
            kind="skill",
        )
        mock_cypher.assert_awaited_once()

    async def test_link_to_esco_success_for_experience(self, engine):
        ent = ExtractedEntity(
            kind="experience", payload={"role": "Senior Dev", "organization": "ACME"}
        )
        entity_id = uuid4()

        mock_result = EscoLinkResult(
            state=LinkState.LINKED,
            esco_uri="http://data.europa.eu/esco/occupation/software-developer",
            score=0.88,
        )

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock(return_value=mock_result)
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            with patch(
                "src.agents.workflows.universe_enrichment.universe_graph_service._execute_cypher",
                new_callable=AsyncMock,
            ) as mock_cypher:
                linked = await engine._link_to_esco(ent, entity_id)

        assert linked is True
        mock_linker.link.assert_awaited_once_with(
            engine._session,
            text_in="Senior Dev ACME",
            kind="occupation",
        )
        mock_cypher.assert_awaited_once()

    async def test_link_to_esco_suggested_state_returns_false(self, engine):
        """SUGGESTED state does not count as linked (no DB write)."""
        ent = ExtractedEntity(kind="skill", payload={"name": "Rust"})
        entity_id = uuid4()

        mock_result = EscoLinkResult(
            state=LinkState.SUGGESTED,
            score=0.75,
        )

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock(return_value=mock_result)
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            with patch(
                "src.agents.workflows.universe_enrichment.universe_graph_service._execute_cypher",
                new_callable=AsyncMock,
            ) as mock_cypher:
                linked = await engine._link_to_esco(ent, entity_id)

        assert linked is False
        mock_cypher.assert_not_awaited()


class TestLinkToEscoFailureCases:
    async def test_link_to_esco_orphan_state(self, engine):
        ent = ExtractedEntity(kind="skill", payload={"name": "UnknownSkillXYZ"})
        entity_id = uuid4()

        mock_result = EscoLinkResult(
            state=LinkState.ORPHAN,
            reason="no candidates",
        )

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock(return_value=mock_result)
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            with patch(
                "src.agents.workflows.universe_enrichment.universe_graph_service._execute_cypher",
                new_callable=AsyncMock,
            ) as mock_cypher:
                linked = await engine._link_to_esco(ent, entity_id)

        assert linked is False
        mock_cypher.assert_not_awaited()

    async def test_link_to_esco_error_state(self, engine):
        ent = ExtractedEntity(kind="skill", payload={"name": "Docker"})
        entity_id = uuid4()

        mock_result = EscoLinkResult(
            state=LinkState.ERROR,
            reason="embed_failed",
        )

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock(return_value=mock_result)
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            with patch(
                "src.agents.workflows.universe_enrichment.universe_graph_service._execute_cypher",
                new_callable=AsyncMock,
            ) as mock_cypher:
                linked = await engine._link_to_esco(ent, entity_id)

        assert linked is False
        mock_cypher.assert_not_awaited()

    async def test_link_to_esco_exception_handled(self, engine):
        ent = ExtractedEntity(kind="skill", payload={"name": "Kubernetes"})
        entity_id = uuid4()

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock(side_effect=RuntimeError("DB down"))
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            with patch(
                "src.agents.workflows.universe_enrichment.universe_graph_service._execute_cypher",
                new_callable=AsyncMock,
            ) as mock_cypher:
                linked = await engine._link_to_esco(ent, entity_id)

        assert linked is False
        mock_cypher.assert_not_awaited()

    async def test_link_to_esco_non_linkable_kind(self, engine):
        """Languages and other kinds are not passed to the linker."""
        ent = ExtractedEntity(kind="language", payload={"name": "English", "level": "C1"})
        entity_id = uuid4()

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock()
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            linked = await engine._link_to_esco(ent, entity_id)

        assert linked is False
        mock_linker.link.assert_not_called()

    async def test_link_to_esco_empty_text(self, engine):
        ent = ExtractedEntity(kind="skill", payload={"name": ""})
        entity_id = uuid4()

        mock_linker = MagicMock()
        mock_linker.link = AsyncMock()
        with patch(
            "src.agents.workflows.universe_enrichment.esco_linker",
            mock_linker,
        ):
            linked = await engine._link_to_esco(ent, entity_id)

        assert linked is False
        mock_linker.link.assert_not_called()
