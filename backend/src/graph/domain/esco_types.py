"""Shared ESCO types — break circular imports between linker and reranker."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LinkState(str, Enum):
    LINKED = "linked"
    SUGGESTED = "suggested"
    ORPHAN = "orphan"
    ERROR = "error"


@dataclass
class EscoCandidate:
    uri: str
    label: str
    pref_label_es: str | None = None
    pref_label_en: str | None = None
    score: float = 0.0


@dataclass
class EscoLinkResult:
    state: LinkState
    esco_uri: str | None = None
    candidates: list[EscoCandidate] = field(default_factory=list)
    score: float = 0.0
    reason: str | None = None
