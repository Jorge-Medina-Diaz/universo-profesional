"""Discovery tools — help the agent ask natural questions to fill profile gaps.

These tools power the `discover_profile` intent.  They analyse what the user
already has in their universe and suggest targeted, conversational questions
that reveal hidden experiences, skills, projects, and education.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from agno.tools import tool

from src.agents.tools._deps import require_user_id
from src.graph.application.universe_graph import universe_graph_service
from src.graph.domain import schema as graph_schema

logger = structlog.get_logger(__name__)


@require_user_id
@tool(description="Get a completeness score for each dimension of the user's profile.")
async def get_profile_completeness(run_context: Any) -> dict[str, Any]:
    """Return counts and coverage % for every entity kind in the user's graph.

    This helps the agent know which areas are well-documented and which are
    sparse, so it can ask targeted discovery questions.
    """
    from uuid import UUID

    user_id = UUID(str(run_context.user_id))
    session = run_context.session

    counts: dict[str, int] = {}
    for label in graph_schema.KIND_TO_LABEL.values():
        result = await universe_graph_service._execute_cypher(
            session,
            f"""
            SELECT count(*)::int AS n
            FROM {graph_schema.GRAPH_PERSONAL}.{label}
            WHERE v.user_id = $uid
            """,
            {"uid": str(user_id)},
        )
        counts[label] = result[0]["n"] if result else 0

    # Heuristic coverage scores
    total = sum(counts.values())
    coverage = {
        "experience": min(1.0, counts.get("experience", 0) / 3.0),
        "education": min(1.0, counts.get("education", 0) / 2.0),
        "skill": min(1.0, counts.get("skill", 0) / 10.0),
        "project": min(1.0, counts.get("project", 0) / 3.0),
        "certification": min(1.0, counts.get("certification", 0) / 2.0),
        "course": min(1.0, counts.get("course", 0) / 3.0),
        "language": min(1.0, counts.get("language", 0) / 2.0),
        "achievement": min(1.0, counts.get("achievement", 0) / 2.0),
    }

    # Find the most sparse dimensions
    sparse = sorted(
        [(dim, score) for dim, score in coverage.items() if score < 0.5],
        key=lambda x: x[1],
    )

    return {
        "counts": counts,
        "coverage": coverage,
        "sparse_dimensions": [dim for dim, _ in sparse],
        "total_entities": total,
    }


_DISCOVERY_QUESTION_PROMPT = """You are a conversational career coach. Given the user's
professional profile summary, generate 1-3 natural, contextual questions that
help the user reveal experiences, skills, projects, or education they haven't
documented yet.

Rules:
  • Questions must feel like conversation, NOT an exam or quiz.
  • Connect each question to something the user ALREADY has ("Veo que…", "Como has trabajado en…").
  • Ask ONE thing per question. Avoid compound questions.
  • Tailor to the gaps: if they have backend experience but no projects, ask about projects.
  • If the profile is empty, ask an open, inviting starter question.
  • Return ONLY a JSON array of objects:
    [{"question": "...", "target_dimension": "skill|experience|project|education|certification|course|language|achievement", "rationale": "...", "expected_entities": ["skill", ...]}, ...]

Profile summary:
{profile_summary}
"""


@require_user_id
@tool(description="Suggest natural discovery questions based on profile gaps.")
async def suggest_discovery_questions(run_context: Any) -> dict[str, Any]:
    """Return conversational questions tailored to the user's actual profile gaps.

    Uses an LLM to generate contextual, natural questions rather than static
    templates. Each question references what the user already has and probes
    a specific gap.
    """
    from uuid import UUID

    from src.shared.config import get_settings

    user_id = UUID(str(run_context.user_id))
    settings = get_settings()

    completeness = await get_profile_completeness(run_context)
    sparse = completeness.get("sparse_dimensions", [])
    counts = completeness.get("counts", {})

    # Build a concise profile summary for the LLM prompt
    profile_lines = ["Profile dimensions:"]
    for dim, n in counts.items():
        profile_lines.append(f"  {dim}: {n}")
    if sparse:
        profile_lines.append(f"Sparse dimensions (need attention): {', '.join(sparse)}")
    else:
        profile_lines.append("Profile is fairly complete. Ask about recent or emerging experiences.")
    profile_summary = "\n".join(profile_lines)

    # Call LLM for personalized questions
    provider = settings.agents_provider_resolved
    questions: list[dict[str, Any]] = []
    try:
        if provider == "anthropic":
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model=settings.agents_specialist_model or "claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=_DISCOVERY_QUESTION_PROMPT.format(profile_summary=profile_summary),
                messages=[{"role": "user", "content": "Genera las preguntas."}],
            )
            raw = str(response.content[0].text)
        elif provider == "openai":
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _DISCOVERY_QUESTION_PROMPT.format(profile_summary=profile_summary)},
                    {"role": "user", "content": "Genera las preguntas."},
                ],
                max_tokens=1024,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = str(response.choices[0].message.content)
        else:
            raw = "[]"

        parsed = json.loads(raw)
        if isinstance(parsed, list):
            questions = parsed
        elif isinstance(parsed, dict) and "questions" in parsed:
            questions = parsed["questions"]
    except Exception as exc:
        logger.warning("discovery_questions_llm_failed", error=str(exc), user_id=str(user_id))
        # Fallback to a safe generic question
        questions = [
            {
                "question": (
                    "Cuéntame algo sobre tu trayectoria que aún no hayamos "
                    "documentado. Puede ser una experiencia, un proyecto o una habilidad."
                ),
                "target_dimension": "any",
                "rationale": "Fallback when LLM generation fails.",
                "expected_entities": ["experience", "skill", "project"],
            }
        ]

    logger.info(
        "discovery_questions_suggested",
        user_id=str(user_id),
        sparse=sparse,
        n_questions=len(questions),
    )
    return {
        "profile_completeness": completeness,
        "suggested_questions": questions,
        "focus_dimensions": sparse,
    }
