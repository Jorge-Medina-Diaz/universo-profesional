"""Declarative merge rules per universe entity.

Each rule takes (existing_entity, new_payload) and returns a `MergePlan` —
the projection to persist plus the field-level diffs that downstream layers
(change_log writer, DiffCard) consume.

Design principles:
  1. Conservative by default: when in doubt, preserve the existing value and
     emit a suggestion rather than guess.
  2. Pure functions: rules don't touch the DB. They take dataclass/dict
     inputs and return values. Easy to unit-test.
  3. Domain-specific maxima: for skills `years` is monotonic (max). For
     `level` we use a CEFR-like rank.
  4. Lists merge by set-union with order preserved (existing first).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .upsert_decision import FieldDiff, MergePlan


def _to_date(val: Any) -> date | None:
    """Normalise a date-like value (date, datetime, ISO string) to date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None
    return None

_SKILL_LEVEL_RANK = {"basic": 1, "intermediate": 2, "high": 3, "expert": 4}
_CEFR_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6, "native": 7}


def _union_list(a: list[Any] | None, b: list[Any] | None) -> list[Any]:
    out = list(a or [])
    seen = {str(x).strip().lower() for x in out}
    for x in (b or []):
        key = str(x).strip().lower()
        if key and key not in seen:
            out.append(x)
            seen.add(key)
    return out


def _better_of(a: Any, b: Any) -> Any:
    """Pick `b` when it's truthy AND `a` is empty; else `a` (preserve)."""
    if a in (None, "", []):
        return b
    return a


def _max_int(a: Any, b: Any) -> Any:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return max(int(a), int(b))


def _max_date(a: Any, b: Any) -> date | None:
    a_date = _to_date(a)
    b_date = _to_date(b)
    if a_date is None:
        return b_date
    if b_date is None:
        return a_date
    return max(a_date, b_date)


def _max_ranked(a: str | None, b: str | None, ranking: dict[str, int]) -> str | None:
    if not a:
        return b
    if not b:
        return a
    return a if ranking.get(a, 0) >= ranking.get(b, 0) else b


def _collect_diffs(existing: dict[str, Any], merged: dict[str, Any]) -> list[FieldDiff]:
    out: list[FieldDiff] = []
    for k, new_val in merged.items():
        old_val = existing.get(k)
        # Treat empty list and None as equivalent for diff purposes.
        if old_val == new_val:
            continue
        if (
            isinstance(old_val, list)
            and isinstance(new_val, list)
            and list(old_val) == list(new_val)
        ):
            continue
        out.append(FieldDiff(field=k, old=old_val, new=new_val))
    return out


# --- Per-entity merge plans -------------------------------------------------


def merge_skill(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["name"] = existing.get("name") or payload.get("name")
    merged["years"] = _max_int(existing.get("years"), payload.get("years"))
    merged["last_used_year"] = _max_int(
        existing.get("last_used_year"), payload.get("last_used_year")
    )
    merged["level"] = _max_ranked(
        existing.get("level"), payload.get("level"), _SKILL_LEVEL_RANK
    )
    # Category conflict → preserve existing, flag suggestion downstream.
    needs_confirm = False
    suggestion_kind: str | None = None
    if (
        payload.get("category")
        and existing.get("category")
        and payload["category"] != existing["category"]
    ):
        needs_confirm = True
        suggestion_kind = "skill_category_conflict"
    else:
        merged["category"] = existing.get("category") or payload.get("category") or "hard"

    # evidence_refs dropped in migration 0017 — skill→evidence relations
    # are graph edges now, not a merged list field.
    diffs = _collect_diffs(existing, merged)
    return MergePlan(
        entity_id=existing["id"],
        merged_payload=merged,
        diffs=diffs,
        needs_user_confirmation=needs_confirm,
        suggestion_kind=suggestion_kind,
    )


def merge_experience(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["organization"] = existing.get("organization") or payload.get("organization")
    merged["role"] = existing.get("role") or payload.get("role")
    merged["start_date"] = existing.get("start_date") or payload.get("start_date")
    merged["end_date"] = _max_date(existing.get("end_date"), payload.get("end_date"))
    # `is_current` flips false when end_date moves into the past.
    if merged["end_date"] is not None:
        merged["is_current"] = False
    else:
        merged["is_current"] = payload.get("is_current") or existing.get("is_current") or False
    merged["description"] = _better_of(existing.get("description"), payload.get("description"))
    merged["highlights"] = _union_list(existing.get("highlights"), payload.get("highlights"))
    merged["competences"] = _union_list(existing.get("competences"), payload.get("competences"))
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_education(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["institution"] = existing.get("institution") or payload.get("institution")
    merged["degree"] = _better_of(existing.get("degree"), payload.get("degree"))
    merged["field_of_study"] = _better_of(
        existing.get("field_of_study"), payload.get("field_of_study")
    )
    merged["start_date"] = existing.get("start_date") or payload.get("start_date")
    merged["end_date"] = _max_date(existing.get("end_date"), payload.get("end_date"))
    merged["description"] = _better_of(existing.get("description"), payload.get("description"))
    merged["highlights"] = _union_list(existing.get("highlights"), payload.get("highlights"))
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_project(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["name"] = existing.get("name") or payload.get("name")
    merged["description"] = _better_of(existing.get("description"), payload.get("description"))
    merged["role"] = _better_of(existing.get("role"), payload.get("role"))
    merged["project_type"] = existing.get("project_type") or payload.get("project_type")
    merged["tech_stack"] = _union_list(existing.get("tech_stack"), payload.get("tech_stack"))
    merged["highlights"] = _union_list(existing.get("highlights"), payload.get("highlights"))
    merged["impact"] = _better_of(existing.get("impact"), payload.get("impact"))
    # Status: most recent wins; if both present and differ, prefer payload (newer).
    if payload.get("status"):
        merged["status"] = payload["status"]
    merged["url"] = existing.get("url") or payload.get("url")
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_certification(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["name"] = existing.get("name") or payload.get("name")
    merged["issuer"] = existing.get("issuer") or payload.get("issuer")
    merged["issued_on"] = existing.get("issued_on") or payload.get("issued_on")
    merged["expires_on"] = _max_date(existing.get("expires_on"), payload.get("expires_on"))
    merged["credential_id"] = existing.get("credential_id") or payload.get("credential_id")
    merged["verification_url"] = existing.get("verification_url") or payload.get(
        "verification_url"
    )
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_course(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["title"] = existing.get("title") or payload.get("title")
    merged["platform"] = existing.get("platform") or payload.get("platform")
    merged["started_on"] = existing.get("started_on") or payload.get("started_on")
    # Once completed_on is set, never overwrite.
    merged["completed_on"] = existing.get("completed_on") or payload.get("completed_on")
    merged["duration_hours"] = _max_int(
        existing.get("duration_hours"), payload.get("duration_hours")
    )
    merged["certificate_url"] = existing.get("certificate_url") or payload.get("certificate_url")
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_language(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["code"] = existing.get("code") or payload.get("code")
    merged["name"] = existing.get("name") or payload.get("name")
    merged["level"] = _max_ranked(existing.get("level"), payload.get("level"), _CEFR_RANK)
    merged["certification"] = _better_of(
        existing.get("certification"), payload.get("certification")
    )
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_achievement(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["title"] = existing.get("title") or payload.get("title")
    merged["achieved_on"] = existing.get("achieved_on") or payload.get("achieved_on")
    merged["description"] = _better_of(existing.get("description"), payload.get("description"))
    merged["context"] = _better_of(existing.get("context"), payload.get("context"))
    merged["evidence_url"] = existing.get("evidence_url") or payload.get("evidence_url")
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_interest(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["name"] = existing.get("name") or payload.get("name")
    # Description: concatenate distinct text with a separator.
    old_desc = (existing.get("description") or "").strip()
    new_desc = (payload.get("description") or "").strip()
    if old_desc and new_desc and new_desc not in old_desc:
        merged["description"] = f"{old_desc}\n\n{new_desc}"
    else:
        merged["description"] = old_desc or new_desc or None
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_artifact(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["type"] = existing.get("type") or payload.get("type")
    merged["title"] = existing.get("title") or payload.get("title")
    merged["url"] = existing.get("url") or payload.get("url")
    merged["year"] = existing.get("year") or payload.get("year")
    merged["description"] = _better_of(existing.get("description"), payload.get("description"))
    merged["venue"] = existing.get("venue") or payload.get("venue")
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


def merge_architecture_decision(existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    merged = dict(existing)
    merged["title"] = existing.get("title") or payload.get("title")
    merged["context"] = _better_of(existing.get("context"), payload.get("context"))
    merged["decision"] = _better_of(existing.get("decision"), payload.get("decision"))
    merged["consequences"] = _better_of(existing.get("consequences"), payload.get("consequences"))
    # Status may advance (proposed -> accepted -> superseded); prefer incoming.
    merged["status"] = payload.get("status") or existing.get("status")
    old_tags = existing.get("tags") or []
    new_tags = payload.get("tags") or []
    merged["tags"] = list(dict.fromkeys([*old_tags, *new_tags]))
    diffs = _collect_diffs(existing, merged)
    return MergePlan(entity_id=existing["id"], merged_payload=merged, diffs=diffs)


MERGE_FUNCTIONS = {
    "skill": merge_skill,
    "experience": merge_experience,
    "education": merge_education,
    "project": merge_project,
    "certification": merge_certification,
    "course": merge_course,
    "language": merge_language,
    "achievement": merge_achievement,
    "interest": merge_interest,
    "artifact": merge_artifact,
    "architecture_decision": merge_architecture_decision,
}


def merge_for(entity_type: str, existing: dict[str, Any], payload: dict[str, Any]) -> MergePlan:
    fn = MERGE_FUNCTIONS.get(entity_type)
    if fn is None:
        raise ValueError(f"No merge rule for entity_type={entity_type!r}")
    return fn(existing, payload)
