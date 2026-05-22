"""Value objects describing the outcome of an upsert.

The agent (or any caller) gets back a typed `UpsertOutcome` so the chat layer
can decide whether to show a "created" toast, a DiffCard merge confirmation,
or an ambiguity prompt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID


class MatchKind(str, Enum):
    NONE = "none"
    EXACT = "exact"          # same name (case-insensitive) — auto-merge
    SEMANTIC = "semantic"     # embedding similarity > threshold — auto-merge
    AMBIGUOUS = "ambiguous"   # near-threshold or conflicting types — suggest


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Outcome of looking up an existing entity for a proposed payload."""

    kind: MatchKind
    entity_id: UUID | None = None
    score: float | None = None       # semantic similarity, when relevant
    candidates: list[UUID] = field(default_factory=list)  # ambiguity tie-breaks

    @property
    def has_match(self) -> bool:
        return self.kind in (MatchKind.EXACT, MatchKind.SEMANTIC)


@dataclass(frozen=True, slots=True)
class FieldDiff:
    field: str
    old: Any
    new: Any


@dataclass(frozen=True, slots=True)
class MergePlan:
    """A merge plan is a set of field changes ready to apply.

    `merged_payload` is the projection that gets persisted via the existing
    `*Crud.update` path. `diffs` feeds both the DiffCard UI and the
    change_log writer.
    """

    entity_id: UUID
    merged_payload: dict[str, Any]
    diffs: list[FieldDiff]
    needs_user_confirmation: bool = False
    suggestion_kind: str | None = None  # set when needs_user_confirmation


class UpsertStatus(str, Enum):
    CREATED = "created"
    MERGED = "merged"
    NOOP = "noop"
    SUGGESTED = "suggested"  # ambiguous — wrote a suggestion, no entity mutation


@dataclass(frozen=True, slots=True)
class UpsertOutcome:
    status: UpsertStatus
    entity_id: UUID | None
    diffs: list[FieldDiff] = field(default_factory=list)
    suggestion_id: UUID | None = None
    reason: str | None = None
