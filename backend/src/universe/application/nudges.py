"""Nudge eligibility engine (P3.A) — the system's proactive heartbeat.

Decides which proactive prompts a user should see, with per-kind cooldowns so
"proactive" never degrades into "repetitive". The daily sweep inserts
`pending` rows; the frontend surfaces them (composer chips, Home badge); the
user acting/dismissing arms the cooldown.

Kinds (v1):
  weekly_capture   "¿Qué has hecho esta semana?" — the daily-use diary loop.
  goal_checkin     An active goal with no movement for 14 days.
  curation_pending ESCO disambiguations / suggestions waiting for review.
  stale_entity     A current experience/project untouched for 60 days.

Adding a kind = one `_Candidate` builder here; storage/API/UI are generic.
"""
from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.security import utc_now

logger = structlog.get_logger(__name__)

# Per-kind cooldown: no new nudge of this kind while one was acted/dismissed
# within the window, and never while one is still pending/surfaced.
_COOLDOWN_DAYS: dict[str, int] = {
    "weekly_capture": 6,
    "goal_checkin": 14,
    "curation_pending": 7,
    "stale_entity": 30,
}


@dataclass(frozen=True)
class _Candidate:
    kind: str
    dedupe_key: str
    payload: dict[str, Any]


async def _on_cooldown(session: AsyncSession, user_id: UUID, kind: str) -> bool:
    row = (
        await session.execute(
            text(
                "SELECT 1 FROM nudges WHERE user_id = :uid AND kind = :kind AND ("
                "  status IN ('pending','surfaced')"
                "  OR (status IN ('acted','dismissed') AND acted_at > :cutoff)"
                ") LIMIT 1"
            ),
            {
                "uid": str(user_id),
                "kind": kind,
                "cutoff": utc_now() - timedelta(days=_COOLDOWN_DAYS[kind]),
            },
        )
    ).first()
    return row is not None


async def _weekly_capture(session: AsyncSession, user_id: UUID) -> _Candidate | None:
    """Activated users with no universe change in the last 5 days."""
    activated = (
        await session.execute(
            text("SELECT activated_at FROM users WHERE id = :uid"),
            {"uid": str(user_id)},
        )
    ).scalar()
    if not activated:
        return None
    recent_change = (
        await session.execute(
            text(
                "SELECT 1 FROM universe_change_log WHERE user_id = :uid "
                "AND changed_at > :cutoff LIMIT 1"
            ),
            {"uid": str(user_id), "cutoff": utc_now() - timedelta(days=5)},
        )
    ).first()
    if recent_change:
        return None
    week = utc_now().strftime("%G-W%V")  # ISO week → idempotent per week
    return _Candidate(
        kind="weekly_capture",
        dedupe_key=week,
        payload={
            "prompt": "¿Qué has hecho esta semana? Cuéntamelo en una frase y lo apunto.",
            "chip": "Revisar mi semana",
        },
    )


async def _goal_checkin(session: AsyncSession, user_id: UUID) -> _Candidate | None:
    row = (
        await session.execute(
            text(
                "SELECT id, title FROM goals WHERE user_id = :uid "
                "AND status = 'active' AND updated_at < :cutoff "
                "ORDER BY updated_at ASC LIMIT 1"
            ),
            {"uid": str(user_id), "cutoff": utc_now() - timedelta(days=14)},
        )
    ).first()
    if row is None:
        return None
    return _Candidate(
        kind="goal_checkin",
        dedupe_key=f"{row.id}:{utc_now():%Y-%m}",
        payload={
            "goal_id": str(row.id),
            "prompt": f"¿Cómo vas con tu meta «{row.title}»?",
            "chip": "Revisar mis metas",
        },
    )


async def _curation_pending(session: AsyncSession, user_id: UUID) -> _Candidate | None:
    count = (
        await session.execute(
            text(
                "SELECT count(*) FROM entity_quarantine WHERE user_id = :uid "
                "AND resolved_at IS NULL"
            ),
            {"uid": str(user_id)},
        )
    ).scalar()
    if not count:
        return None
    return _Candidate(
        kind="curation_pending",
        dedupe_key=utc_now().strftime("%G-W%V"),
        payload={
            "count": int(count),
            "prompt": f"Tienes {count} elemento(s) esperando tu revisión.",
            "chip": "Revisar pendientes",
        },
    )


async def _stale_entity(session: AsyncSession, user_id: UUID) -> _Candidate | None:
    row = (
        await session.execute(
            text(
                "SELECT id, role, organization FROM experiences "
                "WHERE user_id = :uid AND deleted_at IS NULL AND is_current "
                "AND updated_at < :cutoff ORDER BY updated_at ASC LIMIT 1"
            ),
            {"uid": str(user_id), "cutoff": utc_now() - timedelta(days=60)},
        )
    ).first()
    if row is None:
        return None
    return _Candidate(
        kind="stale_entity",
        dedupe_key=f"{row.id}:{utc_now():%Y-%m}",
        payload={
            "entity_id": str(row.id),
            "entity_type": "experience",
            "prompt": f"¿Sigues en {row.organization} como {row.role}? ¿Algo nuevo allí?",
            "chip": "Actualizar mi puesto",
        },
    )


_BUILDERS = (_weekly_capture, _goal_checkin, _curation_pending, _stale_entity)


async def sweep_user_nudges(session: AsyncSession, user_id: UUID) -> int:
    """Insert eligible nudges for one user; returns how many were created."""
    created = 0
    for build in _BUILDERS:
        kind = build.__name__.lstrip("_")
        try:
            # SAVEPOINT per builder: a failed query would otherwise abort the
            # shared transaction and silently poison every later builder.
            async with session.begin_nested():
                if await _on_cooldown(session, user_id, kind):
                    continue
                candidate = await build(session, user_id)
                if candidate is None:
                    continue
                result = await session.execute(
                text(
                    "INSERT INTO nudges (user_id, kind, dedupe_key, payload) "
                    "VALUES (:uid, :kind, :dk, CAST(:payload AS jsonb)) "
                    "ON CONFLICT (user_id, kind, dedupe_key) DO NOTHING"
                ),
                    {
                        "uid": str(user_id),
                        "kind": candidate.kind,
                        "dk": candidate.dedupe_key,
                        "payload": json.dumps(candidate.payload),
                    },
                )
                if result.rowcount:
                    created += 1
        except Exception as exc:  # one bad builder must not starve the rest
            logger.error("nudge_builder_failed", kind=kind, user_id=str(user_id), error=str(exc))
    return created


async def question_asked_recently(
    session: AsyncSession, user_id: UUID, question_hash: str, days: int = 30
) -> bool:
    """Anti-repetition check shared by discovery + nudges."""
    row = (
        await session.execute(
            text(
                "SELECT 1 FROM capture_log WHERE user_id = :uid "
                "AND question_hash = :qh AND asked_at > :cutoff LIMIT 1"
            ),
            {
                "uid": str(user_id),
                "qh": question_hash,
                "cutoff": utc_now() - timedelta(days=days),
            },
        )
    ).first()
    return row is not None


async def log_question_asked(
    session: AsyncSession, user_id: UUID, question_hash: str, topic: str | None
) -> None:
    await session.execute(
        text(
            "INSERT INTO capture_log (user_id, question_hash, topic) "
            "VALUES (:uid, :qh, :topic)"
        ),
        {"uid": str(user_id), "qh": question_hash, "topic": topic},
    )


def hash_question(question: str) -> str:
    """Stable, whitespace/case-insensitive hash of a discovery question."""
    import hashlib
    import re

    norm = re.sub(r"\W+", "", question.lower())
    return hashlib.sha256(norm.encode()).hexdigest()[:32]


__all__ = [
    "hash_question",
    "log_question_asked",
    "question_asked_recently",
    "sweep_user_nudges",
]

