"""MCP tool definitions and handlers for the Universo Profesional server.

Ten tools are exposed through the official MCP Python SDK:
  read_universe_summary, read_entity, search_entities, list_entities,
  create_entity, update_entity, delete_entity, link_esco,
  get_discovery_progress, generate_cv

All write operations (create/update/delete) return a *proposal_id* and go
through the HITL flow stored in ``proposal_store.py``.
"""
from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from mcp.types import Tool

from src.agents.infrastructure.proposal_store import set_proposal
from src.documents.application.use_cases import GenerateCv, GenerateCvInput
from src.documents.infrastructure.job_parser import MockJobParser
from src.documents.infrastructure.llm_client import build_document_llm_client
from src.documents.infrastructure.renderer import WeasyPrintRenderer
from src.documents.infrastructure.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyJobRepository,
)
from src.graph.application.esco_linker import esco_linker
from src.shared.db import with_user_session
from src.shared.embeddings import get_embeddings_service
from src.shared.uow import unit_of_work
from src.universe.application.discovery_service import DiscoveryProgressService
from src.universe.application.registry import CrudRegistry
from src.universe.application.use_cases import (
    GetUniverseSummary,
    SearchUniverse,
    _serialize,
)
from src.universe.infrastructure.repositories import (
    SqlAlchemyCareerPreferencesRepository,
    SqlAlchemyEducationRepository,
    SqlAlchemyExperienceRepository,
    SqlAlchemyLanguageRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemySkillRepository,
    SqlAlchemyUniverseRepository,
)
from src.universe.infrastructure.semantic_search import PgVectorSemanticSearch

# ---------------------------------------------------------------------------
# Tool definitions for the MCP SDK
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[Tool] = [
    Tool(
        name="read_universe_summary",
        description="Returns the user's professional summary (headline, counts, top skills, recent experiences, languages, preferences).",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="read_entity",
        description="Read a specific entity by type and ID or name.",
        inputSchema={
            "type": "object",
            "required": ["entity_type"],
            "properties": {
                "entity_type": {"type": "string", "enum": list(CrudRegistry.kinds())},
                "id": {"type": "string", "format": "uuid"},
                "name": {"type": "string"},
            },
        },
    ),
    Tool(
        name="search_entities",
        description="Semantic search across the user's universe by keyword or phrase.",
        inputSchema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 10},
                "entity_types": {"type": "array", "items": {"type": "string"}},
            },
        },
    ),
    Tool(
        name="list_entities",
        description="List all entities of a given type.",
        inputSchema={
            "type": "object",
            "required": ["entity_type"],
            "properties": {
                "entity_type": {"type": "string", "enum": list(CrudRegistry.kinds())},
            },
        },
    ),
    Tool(
        name="create_entity",
        description="Propose creation of a new entity (HITL — returns proposal_id).",
        inputSchema={
            "type": "object",
            "required": ["entity_type", "data"],
            "properties": {
                "entity_type": {"type": "string", "enum": list(CrudRegistry.kinds())},
                "data": {"type": "object"},
                "confidence": {"type": "number", "default": 0.85},
                "reason": {"type": "string"},
            },
        },
    ),
    Tool(
        name="update_entity",
        description="Propose update of an existing entity (HITL — returns proposal_id).",
        inputSchema={
            "type": "object",
            "required": ["entity_type", "entity_id", "data"],
            "properties": {
                "entity_type": {"type": "string", "enum": list(CrudRegistry.kinds())},
                "entity_id": {"type": "string", "format": "uuid"},
                "data": {"type": "object"},
                "confidence": {"type": "number", "default": 0.85},
                "reason": {"type": "string"},
            },
        },
    ),
    Tool(
        name="delete_entity",
        description="Propose deletion of an existing entity (HITL — returns proposal_id).",
        inputSchema={
            "type": "object",
            "required": ["entity_type", "entity_id"],
            "properties": {
                "entity_type": {"type": "string", "enum": list(CrudRegistry.kinds())},
                "entity_id": {"type": "string", "format": "uuid"},
                "reason": {"type": "string"},
            },
        },
    ),
    Tool(
        name="link_esco",
        description="Link a personal entity text to the ESCO ontology (skill or occupation).",
        inputSchema={
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string"},
                "kind": {"type": "string", "enum": ["skill", "occupation"], "default": "skill"},
            },
        },
    ),
    Tool(
        name="get_discovery_progress",
        description="Return discovery score, entity counts, coverage, recent activity, and ESCO links.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="generate_cv",
        description="Generate a CV from universe data (returns PDF URL, DOCX URL, JSON Resume).",
        inputSchema={
            "type": "object",
            "properties": {
                "job_url": {"type": "string"},
                "job_description": {"type": "string"},
                "template": {"type": "string", "default": "ats-classic"},
                "language": {"type": "string", "enum": ["es", "en"], "default": "es"},
                "tone": {"type": "string"},
                "length": {"type": "string", "enum": ["1-page", "2-page"]},
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# Scopes per tool
# ---------------------------------------------------------------------------

_TOOL_SCOPES: dict[str, str | None] = {
    "read_universe_summary": "universe:read",
    "read_entity": "universe:read",
    "search_entities": "universe:read",
    "list_entities": "universe:read",
    "create_entity": "universe:write",
    "update_entity": "universe:write",
    "delete_entity": "universe:delete",
    "link_esco": "universe:write",
    "get_discovery_progress": "universe:read",
    "generate_cv": "documents:generate",
}


def _repo_for(kind: str, session: Any) -> Any:
    """Instantiate the SQLAlchemy repository for *kind*."""
    repo_cls = CrudRegistry.get_repo_class(kind)
    return repo_cls(session)


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------


async def _read_universe_summary(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    async with with_user_session(user_id) as session:
        uc = GetUniverseSummary(
            SqlAlchemyUniverseRepository(session),
            SqlAlchemyEducationRepository(session),
            SqlAlchemyExperienceRepository(session),
            SqlAlchemySkillRepository(session),
            SqlAlchemyLanguageRepository(session),
            SqlAlchemyProjectRepository(session),
            SqlAlchemyCareerPreferencesRepository(session),
        )
        return await uc.execute(user_id=str(user_id))


async def _read_entity(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    entity_type: str = args["entity_type"]
    entity_id: str | None = args.get("id")
    name: str | None = args.get("name")

    if entity_type not in CrudRegistry.kinds():
        raise ValueError(f"Unknown entity type: {entity_type}")

    async with with_user_session(user_id) as session:
        repo = _repo_for(entity_type, session)

        if entity_id:
            row = await repo.get(user_id, UUID(entity_id))
            if row is None:
                raise ValueError(f"Entity {entity_id} not found")
            return {"entity": _serialize(row)}

        if name:
            rows = await repo.list(user_id)
            matches = [r for r in rows if name.lower() in str(getattr(r, "name", "") or "").lower()]
            if not matches:
                raise ValueError(f"No entity matching name '{name}'")
            return {"entities": [_serialize(r) for r in matches]}

    raise ValueError("Provide either 'id' or 'name'")


async def _search_entities(*, user_id: UUID, args: dict[str, Any]) -> list[dict[str, Any]]:
    query: str = args["query"]
    top_k: int = int(args.get("top_k", 10))
    entity_types: list[str] | None = args.get("entity_types")

    async with with_user_session(user_id) as session:
        search = PgVectorSemanticSearch(session)
        embedder = get_embeddings_service()
        uc = SearchUniverse(search, embedder)
        return await uc.execute(
            user_id=str(user_id),
            query=query,
            top_k=top_k,
            entity_types=entity_types,
        )


async def _list_entities(*, user_id: UUID, args: dict[str, Any]) -> list[dict[str, Any]]:
    entity_type: str = args["entity_type"]
    if entity_type not in CrudRegistry.kinds():
        raise ValueError(f"Unknown entity type: {entity_type}")

    async with with_user_session(user_id) as session:
        repo = _repo_for(entity_type, session)
        rows = await repo.list(user_id)
        return [_serialize(r) for r in rows]


# ---------------------------------------------------------------------------
# Write tools (HITL)
# ---------------------------------------------------------------------------


async def _create_entity(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    entity_type: str = args["entity_type"]
    entity_data: dict[str, Any] = dict(args.get("data", {}))

    if entity_type not in CrudRegistry.kinds():
        raise ValueError(f"Unknown entity type: {entity_type}")

    proposal_id = str(uuid.uuid4())
    set_proposal(
        str(user_id),
        proposal_id,
        entity_type=entity_type,
        entity_data=entity_data,
        action="create",
        confidence=float(args.get("confidence", 0.85)),
        reason=args.get("reason", "Propuesta generada por el agente MCP"),
    )
    return {
        "proposal_id": proposal_id,
        "action": "create",
        "entity_type": entity_type,
        "entity_data": entity_data,
        "message": "User must confirm this proposal via the HITL flow.",
    }


async def _update_entity(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    entity_type: str = args["entity_type"]
    entity_id: str = args["entity_id"]
    patch: dict[str, Any] = dict(args.get("data", {}))

    if entity_type not in CrudRegistry.kinds():
        raise ValueError(f"Unknown entity type: {entity_type}")

    proposal_id = str(uuid.uuid4())
    set_proposal(
        str(user_id),
        proposal_id,
        entity_type=entity_type,
        entity_data={"id": entity_id, **patch},
        action="update",
        confidence=float(args.get("confidence", 0.85)),
        reason=args.get("reason", "Propuesta de actualización generada por el agente MCP"),
    )
    return {
        "proposal_id": proposal_id,
        "action": "update",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "patch": patch,
        "message": "User must confirm this proposal via the HITL flow.",
    }


async def _delete_entity(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    entity_type: str = args["entity_type"]
    entity_id: str = args["entity_id"]

    if entity_type not in CrudRegistry.kinds():
        raise ValueError(f"Unknown entity type: {entity_type}")

    proposal_id = str(uuid.uuid4())
    set_proposal(
        str(user_id),
        proposal_id,
        entity_type=entity_type,
        entity_data={"id": entity_id},
        action="delete",
        confidence=1.0,
        reason=args.get("reason", "Propuesta de borrado generada por el agente MCP"),
    )
    return {
        "proposal_id": proposal_id,
        "action": "delete",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "message": "User must confirm this proposal via the HITL flow.",
    }


# ---------------------------------------------------------------------------
# ESCO + Discovery + CV
# ---------------------------------------------------------------------------


async def _link_esco(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    text_in: str = args["text"]
    kind: str = args.get("kind", "skill")

    async with with_user_session(user_id) as session:
        result = await esco_linker.link(session, text_in, kind)  # type: ignore[arg-type]
        return {
            "state": result.state.value,
            "esco_uri": result.esco_uri,
            "score": result.score,
            "reason": result.reason,
            "candidates": [
                {
                    "uri": c.uri,
                    "label": c.label,
                    "pref_label_es": c.pref_label_es,
                    "pref_label_en": c.pref_label_en,
                    "score": c.score,
                }
                for c in (result.candidates or [])
            ],
        }


async def _get_discovery_progress(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    async with with_user_session(user_id) as session:
        svc = DiscoveryProgressService(session)
        return await svc.get_progress(user_id)


async def _generate_cv(*, user_id: UUID, args: dict[str, Any]) -> dict[str, Any]:
    async with with_user_session(user_id) as session:
        async with unit_of_work(session) as uow:
            uc = GenerateCv(
                documents=SqlAlchemyDocumentRepository(session),
                jobs=SqlAlchemyJobRepository(session),
                parser=MockJobParser(),
                embedder=get_embeddings_service(),
                search=PgVectorSemanticSearch(session),
                llm=build_document_llm_client(session),
                renderer=WeasyPrintRenderer(),
            )
            r = await uc.execute(
                user_id=str(user_id),
                payload=GenerateCvInput(
                    job_url=args.get("job_url"),
                    job_description=args.get("job_description"),
                    template=args.get("template", "ats-classic"),
                    language=args.get("language", "es"),
                    tone=args.get("tone", "professional"),
                    length=args.get("length", "1-page"),
                ),
                uow=uow,
            )
        if r.is_failure:
            raise r.error  # type: ignore[union-attr]
        dto = r.value  # type: ignore[union-attr]
        return {
            "document_id": dto.document_id,
            "pdf_url": dto.pdf_url,
            "docx_url": dto.docx_url,
            "json_resume": dto.json_resume,
        }


# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

TOOL_HANDLERS: dict[str, Any] = {
    "read_universe_summary": _read_universe_summary,
    "read_entity": _read_entity,
    "search_entities": _search_entities,
    "list_entities": _list_entities,
    "create_entity": _create_entity,
    "update_entity": _update_entity,
    "delete_entity": _delete_entity,
    "link_esco": _link_esco,
    "get_discovery_progress": _get_discovery_progress,
    "generate_cv": _generate_cv,
}
