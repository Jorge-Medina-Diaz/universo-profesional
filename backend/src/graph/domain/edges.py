"""Graph edge dataclasses.

Each edge carries the Graphiti-style temporal pair `valid_from`/`valid_to`.
A NULL `valid_to` means "active"; soft-delete sets it to `now()` without
removing the row, so timelines remain queryable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class GraphEdge:
    """Generic typed edge between two nodes.

    `source_id` / `target_id` are the SQL primary keys of the rows the
    vertices mirror; we look up the AGE vertex_id at write time.
    """

    edge_type: str               # one of the constants in schema.py
    source_id: UUID
    target_id: UUID
    user_id: UUID                # tenant filter; mirrors property on edge
    valid_from: datetime
    valid_to: datetime | None = None
    confidence: float | None = None
    source: str = "manual"
    label: str | None = None     # only used for :RELATED_TO
    properties: dict[str, Any] | None = None
