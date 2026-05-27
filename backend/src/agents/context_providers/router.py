"""Intent Router — classifies user intent and selects the right Context Provider.

The router is the front door of the agent architecture.  It is intentionally
lightweight (cheap model, fast inference) because it runs on EVERY user
message.  Its only job is: "¿qué dominio toca esta conversación?"

Intents (Universo Profesional only — career/jobs/social are deferred):
  • expand_universe    — add/update experiences, skills, projects, etc.
  • generate_document  — CV, cover letter, portfolio
  • discover_profile   — agent asks natural questions to reveal experiences/skills/gaps
  • explore_graph      — traverse the graph: trajectory, gaps, related skills
  • general_chat       — greeting, small talk, meta questions

Architecture:
  1. Fast-path keyword heuristic (zero LLM cost for obvious cases).
  2. LLM classifier fallback for ambiguous input.
  3. Provider instantiation with injected memory context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.agents.context_providers.base import BaseContextProvider

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Intent definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    provider_name: str


_INTENT_REGISTRY: dict[str, str] = {
    "expand_universe": "universe_curator",
    "generate_document": "document_engineer",
    "discover_profile": "universe_curator",
    "explore_graph": "universe_curator",
    "general_chat": "universe_curator",
}


# ---------------------------------------------------------------------------
# LLM fallback prompt
# ---------------------------------------------------------------------------

_INTENT_CLASSIFICATION_PROMPT = """Classify the user's message into ONE intent.

Available intents:
  expand_universe    — user wants to add or update experiences, skills, projects, etc.
  generate_document  — user wants a CV, cover letter, or portfolio document.
  discover_profile   — user wants to explore what's missing or be asked about their background.
  explore_graph      — user wants to see connections, trajectory, or graph insights.
  general_chat       — greeting, small talk, or meta question about the system.

Respond with ONLY a JSON object: {"intent": "...", "confidence": 0.0-1.0, "reason": "..."}
"""


# ---------------------------------------------------------------------------
# Keyword heuristics (fast path, no LLM)
# ---------------------------------------------------------------------------

_KEYWORD_PATTERNS: list[tuple[str, list[str], float]] = [
    (
        "generate_document",
        [
            r"\bcv\b",
            r"\bcurrículum\b",
            r"\bcurriculum\b",
            r"\bcarta de presentaci",
            r"\bcover letter\b",
            r"\bgenera\s+(un|mi)\s+(cv|documento|pdf)\b",
            r"\bplantilla\b",
            r"\btemplate\b",
            r"\bportfolio\b",
        ],
        0.9,
    ),
    (
        "explore_graph",
        [
            r"\bmi\s+grafo\b",
            r"\btrayectoria\b",
            r"\bcarrera\b.*\bpaso\b",
            r"\bcamino\b.*\bprofesional\b",
            r"\bc[oó]mo\s+est[aá]\s+relacionad\w*\b",
            r"\bqu[eé]\s+skill\b.*\bfalta\b",
            r"\bqu[eé]\s+deber[ií]a\s+aprender\b",
            r"\bexplora\b.*\buniverso\b",
        ],
        0.85,
    ),
    (
        "discover_profile",
        [
            r"\bDescubre\b.*\bperfil\b",
            r"\bqu[eé]\s+m[eé]\s+falta\b",
            r"\bcompleta\b.*\bperfil\b",
            r"\bhuecos\b.*\buniverso\b",
            r"\bvalida\b.*\bmi\s+perfil\b",
            r"\brevisa\b.*\bmi\s+universo\b",
            r"\banaliza\b.*\bmi\s+trayectoria\b",
        ],
        0.85,
    ),
    (
        "expand_universe",
        [
            r"\bañade\b",
            r"\bagrega\b",
            r"\bnueva\s+(experiencia|skill|habilidad|proyecto|educaci[oó]n)\b",
            r"\btrabaj[eé]\s+en\b",
            r"\bestudi[eé]\b",
            r"\bhe\s+hecho\b",
            r"\bproyecto\b",
            r"\bexperiencia\s+laboral\b",
        ],
        0.85,
    ),
]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class IntentRouter:
    """Classify user messages and return the appropriate provider."""

    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self._session = session
        self._user_id = user_id

    async def classify(self, message: str) -> Intent:
        """Return the most likely intent + provider for *message*."""
        text_lower = message.lower()

        # 1. Fast path: keyword matching (zero LLM cost for obvious cases)
        for intent_name, patterns, confidence in _KEYWORD_PATTERNS:
            for pat in patterns:
                if re.search(pat, text_lower, re.IGNORECASE):
                    provider = _INTENT_REGISTRY.get(intent_name, "universe_curator")
                    logger.info(
                        "intent_classified_fast",
                        intent=intent_name,
                        provider=provider,
                        pattern=pat,
                    )
                    return Intent(
                        name=intent_name,
                        confidence=confidence,
                        provider_name=provider,
                    )

        # 2. Fallback: heuristic length / structure
        if len(message.strip()) < 15:
            return Intent(name="general_chat", confidence=0.7, provider_name="universe_curator")

        # 3. LLM fallback for ambiguous input (only when fast-path misses)
        try:
            from src.shared.config import get_settings

            settings = get_settings()
            provider = settings.agents_provider_resolved
            if provider == "anthropic":
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=settings.anthropic_api_key)
                response = await client.messages.create(
                    model=settings.agents_specialist_model or "claude-haiku-4-5-20251001",
                    max_tokens=256,
                    system=_INTENT_CLASSIFICATION_PROMPT,
                    messages=[{"role": "user", "content": message}],
                )
                raw = str(response.content[0].text)
            elif provider == "openai":
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=settings.openai_api_key)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": _INTENT_CLASSIFICATION_PROMPT},
                        {"role": "user", "content": message},
                    ],
                    max_tokens=256,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
                raw = str(response.choices[0].message.content)
            else:
                raw = '{"intent": "expand_universe", "confidence": 0.5}'

            import json

            parsed = json.loads(raw)
            intent_name = parsed.get("intent", "expand_universe")
            confidence = float(parsed.get("confidence", 0.7))
            provider = _INTENT_REGISTRY.get(intent_name, "universe_curator")
            logger.info(
                "intent_classified_llm",
                intent=intent_name,
                provider=provider,
                confidence=confidence,
            )
            return Intent(
                name=intent_name,
                confidence=min(1.0, max(0.0, confidence)),
                provider_name=provider,
            )
        except Exception as exc:
            logger.warning("intent_router_llm_failed", error=str(exc), message=message[:100])

        # 4. Ultimate fallback
        return Intent(name="expand_universe", confidence=0.5, provider_name="universe_curator")

    async def get_provider(self, intent: Intent) -> BaseContextProvider:
        """Instantiate the provider selected by the intent."""
        from src.agents.context_providers.document_provider import DocumentContextProvider
        from src.agents.context_providers.universe_provider import UniverseContextProvider

        mapping: dict[str, type[BaseContextProvider]] = {
            "universe_curator": UniverseContextProvider,
            "document_engineer": DocumentContextProvider,
        }
        cls = mapping.get(intent.provider_name, UniverseContextProvider)
        return cls(self._session, self._user_id)
