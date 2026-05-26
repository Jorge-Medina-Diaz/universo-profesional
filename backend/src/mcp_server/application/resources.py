"""MCP resources — read-only views over universe + schemas."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

RESOURCES = {
    "universe://summary": {
        "uri": "universe://summary",
        "name": "Universe summary",
        "mimeType": "application/json",
        "description": "Headline, counts, top skills, recent experiences.",
    },
    "universe://education": {
        "uri": "universe://education",
        "name": "Education entries",
        "mimeType": "application/json",
    },
    "universe://experience": {
        "uri": "universe://experience",
        "name": "Experience entries",
        "mimeType": "application/json",
    },
    "documents://recent": {
        "uri": "documents://recent",
        "name": "Recent documents",
        "mimeType": "application/json",
    },
    "schema://json-resume": {
        "uri": "schema://json-resume",
        "name": "JSON Resume v1.0.0 schema",
        "mimeType": "application/json",
    },
    "schema://mac": {
        "uri": "schema://mac",
        "name": "Manfred MAC schema (v0.6, subset)",
        "mimeType": "application/json",
    },
}


async def read_resource(session: AsyncSession, user_id: UUID, uri: str) -> Any:
    if uri == "universe://summary":
        from src.mcp_server.application.tools import _h_get_profile

        return await _h_get_profile(
            session=session, user_id=user_id, client_id=user_id, args={}
        )
    if uri == "universe://education":
        from src.universe.infrastructure.repositories import SqlAlchemyEducationRepository

        return [e.__dict__ for e in await SqlAlchemyEducationRepository(session).list(user_id)]
    if uri == "universe://experience":
        from src.universe.infrastructure.repositories import SqlAlchemyExperienceRepository

        return [e.__dict__ for e in await SqlAlchemyExperienceRepository(session).list(user_id)]
    if uri == "documents://recent":
        from src.documents.application.use_cases import ListDocuments
        from src.documents.infrastructure.repositories import SqlAlchemyDocumentRepository

        return await ListDocuments(SqlAlchemyDocumentRepository(session)).execute(
            user_id=str(user_id), limit=10
        )
    if uri == "schema://json-resume":
        return _JSON_RESUME_SCHEMA
    if uri == "schema://mac":
        return _MAC_SCHEMA
    return {"error": f"Unknown resource: {uri}"}


_JSON_RESUME_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "JSON Resume",
    "version": "v1.0.0",
    "type": "object",
    "properties": {
        "basics": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "label": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "url": {"type": "string"},
                "summary": {"type": "string"},
            },
        },
        "work": {"type": "array"},
        "education": {"type": "array"},
        "skills": {"type": "array"},
        "languages": {"type": "array"},
        "projects": {"type": "array"},
    },
}

_MAC_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "MAC — Manfred Awesomic CV",
    "version": "v0.6",
    "type": "object",
    "properties": {
        "settings": {"type": "object"},
        "aboutMe": {"type": "object"},
        "experience": {"type": "object"},
        "knowledge": {"type": "object"},
        "preferences": {"type": "object"},
        "careerGoals": {"type": "object"},
    },
    "description": "Open-source schema by Manfred (CC BY-SA 4.0). Subset for interop.",
}
