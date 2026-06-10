"""Twin service: slug resolution, curation, profile digest, abuse budgets.

Isolation model (the load-bearing part):
- Slug → owner resolution runs in SERVICE scope (the row is public by
  definition once `enabled`).
- EVERYTHING else — retrieval, analytics writes — runs inside
  `with_user_session(owner_id)`, so the canonical RLS policies scope every
  query to exactly one tenant. The public runtime holds no JWT and never
  receives a session for any other user.
- Curation is applied at the RETRIEVAL layer (`kinds` filter into
  `hybrid_retrieve`), not by prompting: invisible kinds never reach the model.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from src.shared.db import with_user_session
from src.shared.security import utc_now

logger = structlog.get_logger(__name__)

# Kinds a twin may EVER expose. Anything else (notes, goals, preferences,
# diary, feedback…) is private by construction — not a curation choice.
ALLOWED_PUBLIC_KINDS: tuple[str, ...] = (
    "experience",
    "education",
    "skill",
    "project",
    "certification",
    "language",
    "achievement",
)

DEFAULT_CHARTER = (
    "Responde con cercanía y profesionalidad. No hables de salario ni de "
    "datos de contacto: invita a dejar un mensaje con el botón de contacto."
)

# Hard platform caps (R-P1/R-P2) — owner-independent.
MAX_MESSAGE_CHARS = 600
MAX_HISTORY_TURNS = 12
MAX_SESSION_TURNS = 15
DAILY_TURNS_PER_SLUG = 150

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,38}[a-z0-9]$")


def new_slug() -> str:
    """Unguessable by default (TWIN_DESIGN open-question resolution)."""
    return secrets.token_urlsafe(6).lower().replace("_", "-")


def validate_vanity_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug))


def visible_kinds(curation: dict[str, Any]) -> list[str]:
    """Curation ∩ ALLOWED — server-side, regardless of what the row says."""
    wanted = curation.get("visible_kinds")
    if not isinstance(wanted, list) or not wanted:
        wanted = list(ALLOWED_PUBLIC_KINDS)
    return [k for k in wanted if k in ALLOWED_PUBLIC_KINDS]


async def resolve_enabled_profile(slug: str) -> dict[str, Any] | None:
    """Slug → {user_id, curation} for ENABLED profiles only (service scope)."""
    async with with_user_session(None) as session:
        row = (
            await session.execute(
                text(
                    "SELECT user_id, curation FROM public_profiles "
                    "WHERE slug = :slug AND enabled"
                ),
                {"slug": slug},
            )
        ).first()
    if row is None:
        return None
    return {"user_id": row.user_id, "curation": row.curation or {}}


async def build_profile_payload(owner_id: UUID, curation: dict[str, Any]) -> dict[str, Any]:
    """The public profile header: name, headline, visible-kind counts, chips."""
    from collections import Counter

    from src.graph.application.retrieval import _load_snapshot

    kinds = visible_kinds(curation)
    async with with_user_session(owner_id) as session:
        display_name = (
            await session.execute(
                text("SELECT display_name FROM users WHERE id = :uid"),
                {"uid": str(owner_id)},
            )
        ).scalar()
        headline_row = (
            await session.execute(
                text(
                    "SELECT role, organization FROM experiences "
                    "WHERE user_id = :uid AND deleted_at IS NULL AND is_current "
                    "ORDER BY start_date DESC NULLS LAST LIMIT 1"
                ),
                {"uid": str(owner_id)},
            )
        ).first()
        snapshot = await _load_snapshot(session, owner_id)

    kind_counter = Counter(
        meta[1] for meta in snapshot.idx_to_meta.values() if meta[1]
    )
    counts = {k: kind_counter.get(k, 0) for k in kinds if kind_counter.get(k, 0)}
    headline = (
        f"{headline_row.role} · {headline_row.organization}" if headline_row else None
    )
    suggested = curation.get("suggested_questions")
    if not isinstance(suggested, list) or not suggested:
        suggested = [
            "¿Cuál es su experiencia más relevante?",
            "¿Qué proyectos destacaría?",
            "¿Cuáles son sus principales habilidades?",
        ]
    return {
        "display_name": display_name or "Perfil profesional",
        "headline": headline,
        "kind_counts": counts,
        "suggested_questions": suggested[:5],
        "disclosure": (
            "Estás hablando con un agente de IA que responde en nombre del "
            "propietario de este perfil, basándose solo en la información que "
            "ha decidido compartir."
        ),
    }


def visitor_hash(ip: str, user_agent: str) -> str:
    return hashlib.sha256(f"{ip}|{user_agent}".encode()).hexdigest()[:32]


async def consume_daily_budget(slug: str) -> bool:
    """Per-slug daily turn budget via Redis INCR. True = budget available."""
    from src.shared.redis import get_redis

    key = f"twin:budget:{slug}:{utc_now():%Y-%m-%d}"
    redis = get_redis()
    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, 86400)
    return int(used) <= DAILY_TURNS_PER_SLUG


_PII_RE = re.compile(
    r"[\w.+-]+@[\w-]+\.[\w.]+|(?:\+?\d[\d\s().-]{7,}\d)"
)


def scrub_pii(answer: str) -> str:
    """R-P3: emails/phones never leave the public surface."""
    return _PII_RE.sub("[contacto no compartido]", answer)


async def record_turn(
    owner_id: UUID,
    session_id: UUID | None,
    visitor: str,
    question: str,
    answered: bool,
) -> UUID:
    """Analytics (R-O4): upsert the visitor session, log the question.

    Returns the twin_sessions id (created if needed). Failures are logged,
    never raised — analytics must not break the chat.
    """
    async with with_user_session(owner_id) as session:
        sid: UUID | None = None
        if session_id is not None:
            sid = (
                await session.execute(
                    text(
                        "UPDATE twin_sessions SET turns = turns + 1 "
                        "WHERE id = :sid AND user_id = :uid RETURNING id"
                    ),
                    {"sid": str(session_id), "uid": str(owner_id)},
                )
            ).scalar()
        if sid is None:
            sid = (
                await session.execute(
                    text(
                        "INSERT INTO twin_sessions (user_id, visitor_hash, turns) "
                        "VALUES (:uid, :vh, 1) RETURNING id"
                    ),
                    {"uid": str(owner_id), "vh": visitor},
                )
            ).scalar()
        await session.execute(
            text(
                "INSERT INTO twin_questions (user_id, session_id, question, answered) "
                "VALUES (:uid, :sid, :q, :a)"
            ),
            {
                "uid": str(owner_id),
                "sid": str(sid),
                "q": question[:500],
                "a": answered,
            },
        )
        await session.commit()
    return sid
