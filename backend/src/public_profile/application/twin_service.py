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
    """Curation ∩ ALLOWED — server-side, regardless of what the row says.

    CRITICAL distinction: an ABSENT `visible_kinds` key means "owner never
    curated" → default to all allowed kinds. An EXPLICIT empty list means the
    owner deselected everything ("expose nothing") and MUST be honoured as
    empty. Collapsing the two (the old `or not wanted` check) inverted the
    safest possible choice into the least safe one — hide-all silently exposed
    everything.
    """
    if "visible_kinds" not in curation:
        return list(ALLOWED_PUBLIC_KINDS)
    wanted = curation.get("visible_kinds")
    if not isinstance(wanted, list):
        return list(ALLOWED_PUBLIC_KINDS)
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


# Public kind → (table) for visibility-aware header counts. Every table carries
# a `visibility` column (per-entity hiding rides it) — see twin_agent._KIND_DETAILS.
_KIND_TABLE: dict[str, str] = {
    "experience": "experiences",
    "education": "educations",
    "skill": "skills",
    "project": "projects",
    "certification": "certifications",
    "language": "languages",
    "achievement": "achievements",
}


async def _public_kind_counts(
    session: Any, owner_id: UUID, kinds: list[str]
) -> dict[str, int]:
    """Count ONLY public rows per visible kind (never private rows)."""
    counts: dict[str, int] = {}
    for kind in kinds:
        table = _KIND_TABLE.get(kind)
        if table is None:
            continue
        n = (
            await session.execute(
                text(
                    f"SELECT count(*) FROM {table} "
                    "WHERE user_id = :uid AND deleted_at IS NULL "
                    "AND visibility = 'public'"
                ),
                {"uid": str(owner_id)},
            )
        ).scalar() or 0
        if n:
            counts[kind] = int(n)
    return counts


async def build_profile_payload(owner_id: UUID, curation: dict[str, Any]) -> dict[str, Any]:
    """The public profile header: name, headline, visible-kind counts, chips."""
    kinds = visible_kinds(curation)
    kinds_set = set(kinds)
    async with with_user_session(owner_id) as session:
        display_name = (
            await session.execute(
                text("SELECT display_name FROM users WHERE id = :uid"),
                {"uid": str(owner_id)},
            )
        ).scalar()
        # Headline = current role, but ONLY if the owner exposes experience AND
        # the row is public. Without these gates the public header (and the twin
        # system prompt, which bakes in `headline`) broadcast the current job
        # even when the owner marked it private or hid the experience kind.
        headline_row = None
        if "experience" in kinds_set:
            headline_row = (
                await session.execute(
                    text(
                        "SELECT role, organization FROM experiences "
                        "WHERE user_id = :uid AND deleted_at IS NULL AND is_current "
                        "AND visibility = 'public' "
                        "ORDER BY start_date DESC NULLS LAST LIMIT 1"
                    ),
                    {"uid": str(owner_id)},
                )
            ).first()
        # Public kind counts: count ONLY public, visible-kind entities. The
        # igraph snapshot carries every vertex regardless of `visibility`, so
        # counting from it disclosed how many hidden rows exist per kind.
        counts = await _public_kind_counts(session, owner_id, kinds)

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


async def session_turns(owner_id: UUID, session_id: UUID | None) -> int:
    """Authoritative server-side turn count for a twin session.

    The client carries `history` and re-sends it each turn, so the
    `len(history)` gate is client-honesty only — a visitor sends an empty
    history to reset it. This reads the server-incremented counter so the
    per-conversation cap can't be bypassed."""
    if session_id is None:
        return 0
    async with with_user_session(owner_id) as session:
        return int(
            (
                await session.execute(
                    text(
                        "SELECT turns FROM twin_sessions "
                        "WHERE id = :sid AND user_id = :uid"
                    ),
                    {"sid": str(session_id), "uid": str(owner_id)},
                )
            ).scalar()
            or 0
        )


# A single visitor may not drain the whole per-slug budget. Without this, one
# actor rotating IPs past the 10/min per-IP limit could burn the entire daily
# allowance and 429 every other visitor (economic/availability denial). The
# slug budget remains the absolute ceiling; this is the per-actor sub-budget.
DAILY_TURNS_PER_VISITOR = 40


async def consume_daily_budget(slug: str, visitor: str | None = None) -> bool:
    """Per-slug AND per-visitor daily turn budgets via Redis INCR.

    True = budget available. Returns False (caller → 429) if EITHER the shared
    per-slug cap or this visitor's per-actor sub-cap is exhausted. When the slug
    cap is hit we log loudly so the exhaustion is observable (a twin silently
    refusing every visitor for the rest of the day is a failure the owner should
    be able to see in logs/metrics, per the no-silent-errors doctrine).
    """
    from src.shared.config import get_settings
    from src.shared.redis import get_redis

    settings = get_settings()
    is_demo = slug == settings.demo_twin_slug
    cap = settings.demo_twin_daily_turns if is_demo else DAILY_TURNS_PER_SLUG
    redis = get_redis()
    day = f"{utc_now():%Y-%m-%d}"

    # Per-visitor sub-budget first (cheap brake on a single actor). The demo
    # slug is exempt — it's meant to be hammered for the landing demo.
    if visitor and not is_demo:
        vkey = f"twin:vbudget:{slug}:{visitor}:{day}"
        vused = await redis.incr(vkey)
        if vused == 1:
            await redis.expire(vkey, 86400)
        if int(vused) > DAILY_TURNS_PER_VISITOR:
            logger.info("twin_visitor_budget_exhausted", slug=slug, visitor=visitor)
            return False

    key = f"twin:budget:{slug}:{day}"
    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, 86400)
    if int(used) > cap:
        logger.warning("twin_slug_budget_exhausted", slug=slug, cap=cap)
        return False
    return True


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
