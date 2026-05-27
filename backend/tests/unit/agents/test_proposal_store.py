"""Unit tests for proposal_store pure helpers (no DB)."""
from __future__ import annotations

import time

from src.agents.infrastructure.proposal_store import (
    cleanup_expired,
    delete_proposal,
    get_proposal,
    set_proposal,
)


class TestProposalStore:
    def test_set_and_get(self):
        set_proposal("u1", "p1", entity_type="skill", entity_data={"name": "py"})
        item = get_proposal("u1", "p1")
        assert item is not None
        assert item["entity_type"] == "skill"
        assert item["action"] == "create"

    def test_get_missing(self):
        assert get_proposal("u1", "missing") is None

    def test_delete(self):
        set_proposal("u1", "p2", entity_type="skill", entity_data={})
        delete_proposal("u1", "p2")
        assert get_proposal("u1", "p2") is None

    def test_ttl_expires(self):
        set_proposal("u1", "p3", entity_type="skill", entity_data={})
        # Manually backdate created_at so it appears expired
        from src.agents.infrastructure import proposal_store as ps
        ps._store[ps._key("u1", "p3")]["created_at"] = time.time() - 400
        assert get_proposal("u1", "p3") is None

    def test_cleanup_expired(self):
        from src.agents.infrastructure import proposal_store as ps
        set_proposal("u1", "p4", entity_type="skill", entity_data={})
        set_proposal("u1", "p5", entity_type="skill", entity_data={})
        ps._store[ps._key("u1", "p4")]["created_at"] = time.time() - 400
        ps._store[ps._key("u1", "p5")]["created_at"] = time.time() - 10
        removed = cleanup_expired()
        assert removed == 1
        assert get_proposal("u1", "p4") is None
        assert get_proposal("u1", "p5") is not None
