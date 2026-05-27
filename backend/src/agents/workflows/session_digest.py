"""Session digest job — compacts chat history into a structured summary.

Run as an arq task triggered periodically (cron) and on demand whenever the
agent senses the chat is getting long. Output schema:

    {
      "open_questions": [...],
      "decisions": [...],
      "mentioned_entities": [...],
      "mentioned_topics": [...]
    }

In `LLM_PROVIDER=mock` we fall back to a deterministic, lossy digest so the
machinery is testable offline. With real keys, we use Haiku — small enough
that running daily is virtually free.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from src.agents.memory.sliding_window import messages_to_digest, store_digest
from src.shared.config import get_settings
from src.shared.db import with_user_session

logger = structlog.get_logger(__name__)


async def _llm_digest(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Call the configured LLM to produce a structured digest.

    Falls back to a regex-only summary when no provider is configured so dev
    flows keep working.
    """
    settings = get_settings()
    if settings.agents_provider_resolved == "mock":
        return _fallback_digest(messages)
    try:
        from agno.agent import Agent

        from src.agents.factory import _build_model

        digester = Agent(
            name="session_digester",
            model=_build_model("specialist"),
            instructions=[
                "Resume la siguiente conversación en JSON con cuatro claves: "
                "open_questions, decisions, mentioned_entities, mentioned_topics.",
                "Cada clave debe ser una lista de strings cortos. Máximo 800 tokens total.",
            ],
        )
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        result = await digester.arun(input=text, stream=False)
        body = getattr(result, "content", "") or ""
        import json

        try:
            return json.loads(body)
        except Exception:
            return _fallback_digest(messages)
    except Exception as exc:
        logger.warning("session_digest_llm_failed", error=str(exc))
        return _fallback_digest(messages)


def _fallback_digest(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic offline digest — extracts uppercase tokens as entities."""
    import re

    text = " ".join(m.get("content", "") or "" for m in messages)
    entities = sorted(set(re.findall(r"[A-Z][A-Za-z0-9+#.-]{2,}", text)))[:20]
    questions = [m["content"] for m in messages if "?" in (m.get("content", "") or "")][:5]
    return {
        "open_questions": questions,
        "decisions": [],
        "mentioned_entities": entities,
        "mentioned_topics": [],
        "_source": "fallback",
        "_message_count": len(messages),
    }


async def run_session_digest(*, user_id: str) -> dict[str, Any]:
    """Recompute the digest for a single user. Returns the new digest dict."""
    session_id = f"main-{user_id}"
    async with with_user_session(UUID(user_id)) as session:
        older = await messages_to_digest(session, session_id=session_id)
        if older is None:
            logger.debug("session_digest_skipped", user_id=user_id, reason="below_threshold")
            return {"skipped": True}
        digest = await _llm_digest(older)
        await store_digest(
            session, user_id=user_id, session_id=session_id, digest=digest
        )
        logger.info("session_digest_stored", user_id=user_id, messages=len(older))
        return digest


async def session_digest_task(ctx: dict[str, Any], *, user_id: str) -> None:
    """Arq task entry point."""
    await run_session_digest(user_id=user_id)


async def session_digest_cron(ctx: dict[str, Any]) -> None:
    """Arq cron — fan out a digest refresh per active user.

    The workflow self-guards (no-op below DIGEST_THRESHOLD messages), so
    enqueuing for every active user is cheap. Mirrors `curator_cron`.
    """
    from src.agents.workflows.curator import _active_user_ids

    user_ids = await _active_user_ids()
    redis = ctx.get("redis")
    if redis is None:
        for uid in user_ids:
            try:
                await run_session_digest(user_id=uid)
            except Exception as exc:
                logger.error("session_digest_failed", user_id=uid, error=str(exc))
        return
    for uid in user_ids:
        try:
            await redis.enqueue_job("session_digest_task", user_id=uid)
        except Exception as exc:
            logger.error("session_digest_enqueue_failed", user_id=uid, error=str(exc))
    logger.info("session_digest_cron_dispatched", users=len(user_ids))
