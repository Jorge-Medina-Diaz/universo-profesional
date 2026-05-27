"""Graph query tools — Text2Cypher exposed to Agno agents.

These tools let specialists ask complex graph questions without writing Cypher
themselves.  The engine generates openCypher, validates it, executes it on
AGE, and returns structured results.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from agno.run.base import RunContext
from agno.tools import tool

from src.graph.application.text2cypher import Text2CypherEngine
from src.shared.db import get_session_factory, set_rls_user

logger = structlog.get_logger(__name__)


@tool(
    name="query_graph",
    description=(
        "Consulta el grafo profesional del usuario usando lenguaje natural. "
        "El motor traduce la pregunta a openCypher, la ejecuta en Apache AGE, "
        "y devuelve resultados estructurados.\n\n"
        "Usa esta herramienta para preguntas que requieren razonamiento sobre "
        "relaciones, trayectorias o ESCO, por ejemplo:\n"
        "• '¿Qué skills tengo que son esenciales para Data Scientist?'\n"
        "• '¿Cuál ha sido mi trayectoria cronológica?'\n"
        "• '¿Qué skill debería aprender next según mi posición actual?'\n"
        "• '¿He usado Python en algún proyecto o experiencia?'\n"
        "• '¿Qué certificaciones respaldan mis skills de cloud?'\n\n"
        "NO uses esta herramienta para búsquedas puramente textuales; usa "
        "universe_retrieve() en su lugar."
    ),
)
async def query_graph(run_context: RunContext, question: str) -> dict[str, Any]:
    """Run a natural-language graph query and return results."""
    user_id_raw = run_context.user_id
    if not user_id_raw:
        return {"ok": False, "error": "missing user_id"}
    user_id = UUID(str(user_id_raw))

    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_id)
        engine = Text2CypherEngine(session, user_id)
        result = await engine.ask(question)
        await session.commit()

    if result.error:
        return {
            "ok": False,
            "error": result.error,
            "explanation": result.explanation,
            "cypher": result.cypher,
        }

    if result.cypher is None:
        return {
            "ok": False,
            "error": "query not supported",
            "explanation": result.explanation,
        }

    return {
        "ok": True,
        "cypher": result.cypher,
        "explanation": result.explanation,
        "rows": result.rows or [],
        "row_count": len(result.rows or []),
        "latency_ms": round(result.latency_ms, 1),
    }


@tool(
    name="explain_graph_query",
    description=(
        "Genera (pero NO ejecuta) la query openCypher correspondiente a una "
        "pregunta en lenguaje natural. Útil para debugging o para mostrar al "
        "usuario cómo se traduce su pregunta a Cypher."
    ),
)
async def explain_graph_query(run_context: RunContext, question: str) -> dict[str, Any]:
    """Generate Cypher without executing it."""
    user_id_raw = run_context.user_id
    if not user_id_raw:
        return {"ok": False, "error": "missing user_id"}
    user_id = UUID(str(user_id_raw))

    factory = get_session_factory()
    async with factory() as session:
        await set_rls_user(session, user_id)
        engine = Text2CypherEngine(session, user_id)
        result = await engine.generate(question)

    return {
        "ok": result.cypher is not None and result.error is None,
        "cypher": result.cypher,
        "params": result.params,
        "explanation": result.explanation,
        "error": result.error,
    }
