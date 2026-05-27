"""Unit tests for upsert_use_cases pure helpers (no DB)."""
from __future__ import annotations

from src.coherence.application.upsert_use_cases import (
    _strip_metadata_keys,
    _to_json,
    entities_supporting_stale,
    is_known_entity,
)


class TestIsKnownEntity:
    def test_known(self):
        assert is_known_entity("skill") is True

    def test_unknown(self):
        assert is_known_entity("unicorn") is False


class TestEntitiesSupportingStale:
    def test_returns_list(self):
        result = entities_supporting_stale()
        assert isinstance(result, list)


class TestStripMetadataKeys:
    def test_removes_system_fields(self):
        payload = {"id": "x", "user_id": "u", "name": "Python", "created_at": "now"}
        out = _strip_metadata_keys(payload)
        assert "id" not in out
        assert "user_id" not in out
        assert "created_at" not in out
        assert out["name"] == "Python"

    def test_removes_derived_from(self):
        payload = {"name": "Python", "derived_from_skill_id": "abc"}
        out = _strip_metadata_keys(payload)
        assert "derived_from_skill_id" not in out

    def test_removes_relation_keys(self):
        payload = {"name": "Python", "linked_skill_ids": ["a"], "mentioned_in_note_id": "n"}
        out = _strip_metadata_keys(payload)
        assert "linked_skill_ids" not in out
        assert "mentioned_in_note_id" not in out


class TestToJson:
    def test_serializes_dict(self):
        assert _to_json({"a": 1}) == '{"a": 1}'

    def test_serializes_uuid(self):
        import uuid

        text = _to_json({"id": uuid.UUID("12345678-1234-5678-1234-567812345678")})
        assert "12345678-1234-5678-1234-567812345678" in text
