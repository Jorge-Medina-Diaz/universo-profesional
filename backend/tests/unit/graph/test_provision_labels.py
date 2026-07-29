"""The provisioning SQL must pre-create every AGE label the app can write.

Creating a *new* AGE label is DDL that requires ownership of
`_ag_label_vertex` / `_ag_label_edge`, which the RLS-subject runtime role
(`cvs_app`) rightly lacks. So every label in the ontology allowlist has to
exist before the app ever runs.

When it doesn't, the failure is nasty and silent: the DDL error aborts the
Postgres transaction, and Postgres turns the caller's later COMMIT into a
ROLLBACK — so a whole enrichment pass is discarded while the endpoint still
returns 200. `Community` drifted out of this list exactly that way.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.graph.domain import schema

_SQL = Path(__file__).resolve().parents[3] / "scripts" / "provision_app_role.sql"


def _labels_after(marker: str) -> set[str]:
    """Pull the quoted identifiers from the ARRAY[...] literal following `marker`."""
    body = _SQL.read_text(encoding="utf-8").split(marker, 1)[1]
    array = body.split("ARRAY[", 1)[1].split("]", 1)[0]
    return set(re.findall(r"'([^']+)'", array))


def test_provisioning_precreates_every_vertex_label() -> None:
    assert _labels_after("FOREACH vl IN") == set(schema.PERSONAL_VERTEX_LABELS)


def test_provisioning_precreates_every_edge_type() -> None:
    assert _labels_after("FOREACH el IN") == set(schema.PERSONAL_EDGE_TYPES)


if __name__ == "__main__":  # pragma: no cover - manual run
    test_provisioning_precreates_every_vertex_label()
    test_provisioning_precreates_every_edge_type()
    print("ok")
