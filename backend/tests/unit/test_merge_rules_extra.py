"""Extra edge-case unit tests for merge_rules helpers."""
from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from src.coherence.domain.merge_rules import (
    _collect_diffs,
    _max_int,
    _max_ranked,
    _to_date,
    merge_for,
)


class TestToDate:
    def test_none(self):
        assert _to_date(None) is None

    def test_date(self):
        d = date(2024, 1, 1)
        assert _to_date(d) == d

    def test_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0)
        assert _to_date(dt) == date(2024, 1, 1)

    def test_iso_string(self):
        assert _to_date("2024-01-15") == date(2024, 1, 15)

    def test_invalid_string(self):
        assert _to_date("not-a-date") is None

    def test_invalid_type(self):
        assert _to_date(12345) is None
        assert _to_date([]) is None


class TestMaxInt:
    def test_both_none(self):
        assert _max_int(None, None) is None

    def test_one_none(self):
        assert _max_int(None, 5) == 5
        assert _max_int(5, None) == 5

    def test_max(self):
        assert _max_int(3, 7) == 7
        assert _max_int(7, 3) == 7


class TestMaxRanked:
    def test_empty_a(self):
        assert _max_ranked(None, "expert", {"expert": 4}) == "expert"

    def test_empty_b(self):
        assert _max_ranked("expert", None, {"expert": 4}) == "expert"

    def test_higher_wins(self):
        ranking = {"basic": 1, "expert": 4}
        assert _max_ranked("basic", "expert", ranking) == "expert"
        assert _max_ranked("expert", "basic", ranking) == "expert"


class TestCollectDiffs:
    def test_no_diffs(self):
        existing = {"a": 1, "b": [1, 2]}
        merged = {"a": 1, "b": [1, 2]}
        assert _collect_diffs(existing, merged) == []

    def test_list_equality(self):
        existing = {"a": [1, 2]}
        merged = {"a": [1, 2]}
        assert _collect_diffs(existing, merged) == []

    def test_detects_diff(self):
        existing = {"a": 1}
        merged = {"a": 2}
        diffs = _collect_diffs(existing, merged)
        assert len(diffs) == 1
        assert diffs[0].field == "a"


class TestMergeForEdgeCases:
    def test_experience_end_date_sets_is_current_false(self):
        existing = {
            "id": uuid4(),
            "organization": "Acme",
            "role": "Dev",
            "start_date": "2020-01-01",
            "end_date": None,
            "is_current": True,
            "description": None,
            "highlights": [],
            "competences": [],
        }
        plan = merge_for(
            "experience",
            existing,
            {"organization": "Acme", "role": "Dev", "end_date": "2023-01-01"},
        )
        assert plan.merged_payload["is_current"] is False

    def test_project_status_overwrite(self):
        existing = {
            "id": uuid4(),
            "name": "P",
            "description": None,
            "role": None,
            "project_type": "side",
            "tech_stack": [],
            "highlights": [],
            "impact": None,
            "status": "active",
            "url": None,
        }
        plan = merge_for("project", existing, {"name": "P", "status": "shipped"})
        assert plan.merged_payload["status"] == "shipped"
