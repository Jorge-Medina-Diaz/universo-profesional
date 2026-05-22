"""Thin async client for Apache AGE on top of SQLAlchemy + asyncpg.

AGE has a few sharp edges that this module hides from the rest of the app:

  • Every connection has to `LOAD 'age'` and have `ag_catalog` in
    `search_path`. We do this on first use per session via a SQLAlchemy
    event hook.
  • Cypher queries are wrapped in `cypher('<graph>', $$ ... $$)` and
    require column type aliases at the end (`AS (n agtype, ...)`).
  • Parameter binding inside cypher() is brittle: you cannot use bind
    params directly. The pattern that works is to pass a `params` agtype
    JSON object as a third argument to `cypher()` and reference its keys
    inside the literal Cypher with `$key` syntax. We accept normal Python
    dicts and serialise them.
  • Vertex/edge return values come back as agtype strings — we parse
    them with a small JSON helper since agtype is JSON-compatible for
    the value subset we use.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Session setup — run once per connection.
# ---------------------------------------------------------------------------


async def ensure_age_loaded(session: AsyncSession) -> None:
    """Make sure AGE's catalog functions are visible in this session.

    Postgres `shared_preload_libraries = 'age'` already preloads the
    extension server-side, but the per-connection `search_path` may not
    include `ag_catalog`. We set both once per session and remember it on
    `session.info` so subsequent cypher() calls skip the two round-trips.
    """
    if session.info.get("age_loaded"):
        return
    # `LOAD 'age'` is a no-op if shared_preload_libraries already loaded
    # the library, but is required if it didn't (e.g. when running tests
    # against a vanilla postgres image).
    await session.execute(text("LOAD 'age'"))
    await session.execute(
        text("SELECT set_config('search_path', 'ag_catalog,public,\"$user\"', false)")
    )
    session.info["age_loaded"] = True


# ---------------------------------------------------------------------------
# Cypher execution
# ---------------------------------------------------------------------------


_AGE_LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Column-defs allow-list: a comma-separated list of `<ident> agtype`
# pairs. AGE's `cypher(...) AS (col1 agtype, col2 agtype)` clause is the
# only place outside of `graph` where untrusted identifiers reach the SQL
# layer, so we lock it down with a regex rather than trying to escape.
_COLUMN_DEFS_RE = re.compile(
    r"^\s*[A-Za-z_][A-Za-z0-9_]*\s+agtype\s*"
    r"(?:,\s*[A-Za-z_][A-Za-z0-9_]*\s+agtype\s*)*$"
)


def _validate_graph_name(graph: str) -> None:
    if not _AGE_LABEL_RE.match(graph):
        msg = f"invalid AGE graph name: {graph!r}"
        raise ValueError(msg)


def _validate_column_defs(column_defs: str) -> None:
    if not _COLUMN_DEFS_RE.match(column_defs):
        msg = (
            f"invalid AGE column_defs: {column_defs!r} "
            "(expected `<ident> agtype[, <ident> agtype, ...]`)"
        )
        raise ValueError(msg)


def _serialize_params(params: Mapping[str, Any] | None) -> str:
    """Serialise a Python dict into the JSON string AGE expects as agtype.

    UUIDs become strings; everything else passes through json.dumps. The
    JSON is bound as a SQL parameter (AGE *requires* a Param node for the
    third argument of cypher() — embedding the JSON inline triggers
    `third argument of cypher function must be a parameter`).
    """
    if not params:
        return "{}"
    safe: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, UUID):
            safe[key] = str(value)
        else:
            safe[key] = value
    return json.dumps(safe, default=str, ensure_ascii=False)


async def cypher(
    session: AsyncSession,
    graph: str,
    query: str,
    *,
    params: Mapping[str, Any] | None = None,
    column_defs: str = "result agtype",
) -> list[dict[str, Any]]:
    """Execute a Cypher query against an AGE graph and return rows as dicts.

    Args:
        session: an AsyncSession already configured for this database.
        graph: name of the graph (must match `[A-Za-z_][A-Za-z0-9_]*`).
        query: the Cypher body (without the `cypher('graph', $$ ... $$)`
            wrapper). It may reference parameters as `$paramName`.
        params: optional dict of named parameters.
        column_defs: column list for the `AS (...)` clause — must match
            the Cypher RETURN clause. Defaults to a single `result agtype`
            column; pass e.g. `"id agtype, name agtype"` for multi-column
            RETURNs.

    Returns:
        A list of dicts keyed by the column names in `column_defs`. Each
        value is the raw agtype string — call `parse_agtype()` to extract
        Python objects.
    """
    _validate_graph_name(graph)
    _validate_column_defs(column_defs)
    await ensure_age_loaded(session)

    # AGE requires the params arg to be a SQL Param node (not a literal).
    # The SQL parameter is sent via psycopg/asyncpg bind variables, which
    # is what sqlalchemy's `:cypher_params` turns into.
    params_json = _serialize_params(params)
    if params:
        # The `::agtype` cast is applied AFTER bind substitution, so AGE
        # sees a Param node at parse time (its requirement) while postgres
        # later coerces the JSON string into agtype.
        sql = (
            f"SELECT * FROM cypher('{graph}', $cypher$ {query} $cypher$, "
            f"CAST(:cypher_params AS agtype)) AS ({column_defs})"
        )
        result = await session.execute(text(sql), {"cypher_params": params_json})
    else:
        # No-params form: AGE's two-argument cypher() doesn't expect the
        # Param node at all, and many built-in Cypher utilities still
        # work without it. We avoid sending an empty `{}` agtype to keep
        # the SQL clean.
        sql = (
            f"SELECT * FROM cypher('{graph}', $cypher$ {query} $cypher$) "
            f"AS ({column_defs})"
        )
        result = await session.execute(text(sql))

    rows = result.mappings().all()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# agtype → Python parsing
# ---------------------------------------------------------------------------


_VERTEX_SUFFIX = "::vertex"
_EDGE_SUFFIX = "::edge"


def parse_agtype(value: Any) -> Any:
    """Parse an agtype value (string) into a Python object.

    The agtype scalar grammar is JSON with a `::vertex` / `::edge` /
    `::path` annotation suffix. For scalars (numbers, strings, bools,
    null) it is plain JSON. We strip the annotation and json.loads it.
    """
    if value is None or not isinstance(value, str):
        return value

    raw = value
    for suffix in (_VERTEX_SUFFIX, _EDGE_SUFFIX, "::path", "::numeric"):
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)]
            break
    raw = raw.strip()
    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to the raw string — some AGE responses (e.g. function
        # names) come back unquoted.
        return raw
