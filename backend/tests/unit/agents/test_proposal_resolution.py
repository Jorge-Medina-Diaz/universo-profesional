"""Unit tests for proposal resolution endpoint logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from src.agents.infrastructure.proposal_store import set_proposal
from src.agents.interfaces.api.router import ResolveProposalBody, resolve_proposal


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_user_id():
    return uuid4()


@pytest.fixture
def sample_proposal(mock_user_id: UUID):
    pid = str(uuid4())
    set_proposal(
        user_id=str(mock_user_id),
        proposal_id=pid,
        entity_type="experience",
        entity_data={
            "organization": "Acme Corp",
            "role": "Senior Dev",
            "start_date": "2023-01-01",
        },
        action="create",
        confidence=0.9,
        reason="User mentioned this job",
        thread_id="main-user-123",
    )
    return pid


class TestConfirm:
    async def test_confirm_creates_entity(self, mock_session, mock_user_id, sample_proposal):
        body = ResolveProposalBody(action="confirm")

        mock_outcome = MagicMock()
        mock_outcome.status.value = "created"
        mock_outcome.entity_id = uuid4()
        mock_outcome.diffs = []
        mock_outcome.reason = "Created via proposal"

        with patch(
            "src.agents.interfaces.api.router.UpsertUniverseEntity"
        ) as MockUC:
            instance = MockUC.return_value
            instance.execute = AsyncMock(return_value=mock_outcome)

            resp = await resolve_proposal(
                proposal_id=sample_proposal,
                body=body,
                user_id=mock_user_id,
                session=mock_session,
            )

        assert resp.status == "created"
        assert resp.entity_id is not None
        assert resp.reason == "Created via proposal"

    async def test_confirm_merges_entity(self, mock_session, mock_user_id, sample_proposal):
        body = ResolveProposalBody(action="confirm")

        mock_outcome = MagicMock()
        mock_outcome.status.value = "merged"
        mock_outcome.entity_id = uuid4()
        mock_outcome.diffs = [MagicMock(field="end_date", old=None, new="2024-06-01")]
        mock_outcome.reason = "Merged with existing"

        with patch(
            "src.agents.interfaces.api.router.UpsertUniverseEntity"
        ) as MockUC:
            instance = MockUC.return_value
            instance.execute = AsyncMock(return_value=mock_outcome)

            resp = await resolve_proposal(
                proposal_id=sample_proposal,
                body=body,
                user_id=mock_user_id,
                session=mock_session,
            )

        assert resp.status == "merged"
        assert len(resp.diffs) == 1
        assert resp.diffs[0]["field"] == "end_date"


class TestReject:
    async def test_reject_records_feedback(self, mock_session, mock_user_id, sample_proposal):
        body = ResolveProposalBody(action="reject")

        with patch(
            "src.agents.interfaces.api.router.SelfLearningEngine"
        ) as MockEngine:
            mock_engine = MockEngine.return_value
            mock_engine.record = AsyncMock()

            resp = await resolve_proposal(
                proposal_id=sample_proposal,
                body=body,
                user_id=mock_user_id,
                session=mock_session,
            )

        assert resp.status == "rejected"
        mock_engine.record.assert_awaited_once()
        call_args = mock_engine.record.call_args[0][0]
        assert call_args.sentiment == "negative"
        assert call_args.scope == "proposal_rejection"


class TestModify:
    async def test_modify_applies_changes_then_upserts(
        self, mock_session, mock_user_id, sample_proposal
    ):
        body = ResolveProposalBody(
            action="modify",
            modified_data={"role": "Lead Engineer", "end_date": "2024-12-31"},
        )

        mock_outcome = MagicMock()
        mock_outcome.status.value = "created"
        mock_outcome.entity_id = uuid4()
        mock_outcome.diffs = []
        mock_outcome.reason = "Created with modifications"

        with patch(
            "src.agents.interfaces.api.router.UpsertUniverseEntity"
        ) as MockUC:
            instance = MockUC.return_value
            instance.execute = AsyncMock(return_value=mock_outcome)

            resp = await resolve_proposal(
                proposal_id=sample_proposal,
                body=body,
                user_id=mock_user_id,
                session=mock_session,
            )

        assert resp.status == "created"
        # Verify the upsert was called with merged data
        call_kwargs = instance.execute.call_args.kwargs
        assert call_kwargs["payload"]["role"] == "Lead Engineer"
        assert call_kwargs["payload"]["end_date"] == "2024-12-31"
        assert call_kwargs["payload"]["organization"] == "Acme Corp"


class TestEdgeCases:
    async def test_proposal_not_found_raises_404(self, mock_session, mock_user_id):
        body = ResolveProposalBody(action="confirm")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await resolve_proposal(
                proposal_id="non-existent-id",
                body=body,
                user_id=mock_user_id,
                session=mock_session,
            )
        assert exc_info.value.status_code == 404

    async def test_invalid_action_raises_400(self, mock_session, mock_user_id, sample_proposal):
        body = ResolveProposalBody(action="invalid_action")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await resolve_proposal(
                proposal_id=sample_proposal,
                body=body,
                user_id=mock_user_id,
                session=mock_session,
            )
        assert exc_info.value.status_code == 400

    async def test_proposal_expired_raises_404(self, mock_session, mock_user_id):
        """Expired proposals are cleaned up on read and return 404."""
        from src.agents.infrastructure.proposal_store import _store

        pid = str(uuid4())
        import time

        _store[f"proposal:{mock_user_id}:{pid}"] = {
            "entity_type": "skill",
            "entity_data": {"name": "Python"},
            "created_at": time.time() - 400,  # > 300s TTL
        }

        body = ResolveProposalBody(action="confirm")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await resolve_proposal(
                proposal_id=pid,
                body=body,
                user_id=mock_user_id,
                session=mock_session,
            )
        assert exc_info.value.status_code == 404
