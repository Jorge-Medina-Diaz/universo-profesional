"""Public twin surface — NO auth. The slug is the capability.

GET  /api/v1/public/twin/{slug}        → profile header (enabled only)
POST /api/v1/public/twin/{slug}/chat   → one grounded twin turn (JSON)
POST /api/v1/public/twin/{slug}/lead   → visitor leaves contact for the owner

Abuse posture (R-P1/R-P2): per-IP slowapi limits on every route, per-slug
daily turn budget in Redis, per-session turn cap, message length cap,
Haiku-only model, PII scrub on output. Failures return typed JSON the widget
can show — never a silent empty answer.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.public_profile.application import twin_service
from src.public_profile.application.twin_agent import run_twin_turn
from src.shared.db import with_user_session
from src.shared.rate_limit import limiter

logger = structlog.get_logger(__name__)

router = APIRouter()


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=1500)


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=twin_service.MAX_MESSAGE_CHARS)
    history: list[ChatTurn] = Field(default_factory=list, max_length=twin_service.MAX_HISTORY_TURNS)
    session_id: UUID | None = None


class LeadBody(BaseModel):
    contact: str = Field(min_length=3, max_length=200)
    message: str | None = Field(default=None, max_length=1000)


async def _profile_or_404(slug: str) -> dict[str, Any]:
    profile = await twin_service.resolve_enabled_profile(slug)
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil no disponible")
    return profile


@router.get("/{slug}")
@limiter.limit("60/minute")
async def public_profile(request: Request, slug: str) -> dict[str, Any]:
    resolved = await _profile_or_404(slug)
    payload = await twin_service.build_profile_payload(
        resolved["user_id"], resolved["curation"]
    )
    return {"slug": slug, **payload}


@router.post("/{slug}/chat")
@limiter.limit("10/minute")
async def public_chat(request: Request, slug: str, body: ChatBody) -> dict[str, Any]:
    resolved = await _profile_or_404(slug)
    owner_id: UUID = resolved["user_id"]
    visitor = twin_service.visitor_hash(
        request.client.host if request.client else "?",
        request.headers.get("user-agent", "?"),
    )

    # Authoritative cap: trust the server-side turn counter when we have a
    # session, falling back to the client-carried history length for the first
    # turn (no session yet). Either tripping the limit ends the conversation.
    server_turns = await twin_service.session_turns(owner_id, body.session_id)
    if (
        server_turns >= twin_service.MAX_SESSION_TURNS
        or len(body.history) >= twin_service.MAX_SESSION_TURNS
    ):
        return {
            "answer": (
                "Hemos llegado al límite de esta conversación. Si quieres "
                "seguir hablando, deja tu contacto y te respondo en persona."
            ),
            "limit_reached": True,
            "session_id": str(body.session_id) if body.session_id else None,
        }
    if not await twin_service.consume_daily_budget(slug, visitor):
        raise HTTPException(
            status_code=429,
            detail="Este perfil ha alcanzado su límite diario de conversación.",
        )

    profile = await twin_service.build_profile_payload(owner_id, resolved["curation"])
    answered = True
    try:
        answer = await run_twin_turn(
            owner_id,
            profile,
            resolved["curation"],
            body.message,
            [t.model_dump() for t in body.history],
        )
    except Exception as exc:
        logger.error("twin_turn_failed", slug=slug, error=str(exc))
        raise HTTPException(
            status_code=503,
            detail="El gemelo no está disponible ahora mismo. Inténtalo en un momento.",
        )
    if not answer:
        answered = False
        answer = (
            "No tengo esa información compartida aquí. ¿Quieres dejarme un "
            "mensaje de contacto?"
        )
    answer = twin_service.scrub_pii(answer)

    session_id: UUID | None = body.session_id
    try:
        session_id = await twin_service.record_turn(
            owner_id, body.session_id, visitor, body.message, answered
        )
    except Exception as exc:  # analytics must never break the chat
        logger.warning("twin_analytics_failed", slug=slug, error=str(exc))

    return {
        "answer": answer,
        "session_id": str(session_id) if session_id else None,
        "disclosure": "Respuesta generada por IA en nombre del propietario del perfil.",
    }


@router.post("/{slug}/lead")
@limiter.limit("5/minute")
async def public_lead(request: Request, slug: str, body: LeadBody) -> dict[str, Any]:
    resolved = await _profile_or_404(slug)
    owner_id: UUID = resolved["user_id"]
    async with with_user_session(owner_id) as session:
        await session.execute(
            text(
                "INSERT INTO twin_leads (user_id, contact, message) "
                "VALUES (:uid, :contact, :message)"
            ),
            {"uid": str(owner_id), "contact": body.contact, "message": body.message},
        )
        await session.commit()
    try:
        from src.identity.infrastructure.tasks import enqueue_transactional_email

        await enqueue_transactional_email(
            user_id=owner_id,
            template="twin_lead",
            context={"contact": body.contact, "message": body.message or ""},
        )
    except Exception as exc:  # the lead row is saved; email is best-effort
        logger.warning("twin_lead_email_failed", slug=slug, error=str(exc))
    return {"ok": True}
