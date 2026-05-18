"""Mock JD parser. In v1 this scrapes the URL and calls a small LLM.

The mock detects a few well-known ATS strings + extracts simple keywords with
regex. It returns a `description_raw` field and the parsed payload conforming
to the schema in §J.2 of the spec.
"""
from __future__ import annotations

import re
from typing import Any

from src.documents.application.ports import JobParser

ATS_HINTS = {
    "workday": "Workday",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "smartrecruiters": "SmartRecruiters",
    "bizneo": "Bizneo",
    "successfactors": "SAP SuccessFactors",
    "talent clue": "Talent Clue",
    "factorial": "Factorial",
    "personio": "Personio",
    "ashby": "Ashby",
    "taleo": "Taleo",
}

# Naive keyword bank — good enough for the deterministic demo
HARD_KEYWORDS = {
    "Python", "TypeScript", "JavaScript", "Go", "Rust", "Java", "C++", "C#",
    "FastAPI", "Django", "Flask", "Node.js", "React", "Vue", "Svelte",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
    "REST", "GraphQL", "gRPC", "Kafka", "RabbitMQ", "Celery", "Arq",
    "Pandas", "Numpy", "PyTorch", "TensorFlow", "MCP", "OAuth",
}

SOFT_KEYWORDS = {
    "comunicación", "liderazgo", "trabajo en equipo", "autonomía",
    "leadership", "communication", "ownership", "mentoring",
}


class MockJobParser(JobParser):
    async def parse(
        self, *, url: str | None, description: str | None
    ) -> dict[str, Any]:
        text = description or ""
        if not text and url:
            # In MVP we don't fetch — we ship a fixture-like response
            text = f"Job listed at {url}"
        lower = text.lower()

        ats = None
        for needle, label in ATS_HINTS.items():
            if needle in lower:
                ats = label
                break

        hard = sorted({k for k in HARD_KEYWORDS if k.lower() in lower})
        soft = sorted({k for k in SOFT_KEYWORDS if k.lower() in lower})

        title_match = re.search(
            r"(?:senior|junior|mid|lead|principal|staff)?\s*"
            r"(developer|engineer|architect|manager|designer|analyst|scientist|consultor|director)",
            lower,
        )
        title = (title_match.group(0).strip().title() if title_match else None)

        company_match = re.search(r"(?:at|en|@)\s+([A-Z][\w&\-]+)", text)
        company = company_match.group(1) if company_match else None

        return {
            "title": title,
            "company": company,
            "ats": ats,
            "hard_skills": hard,
            "soft_skills": soft,
            "ats_keywords": hard,
            "must_haves": hard[:5],
            "nice_to_haves": hard[5:10],
            "description_raw": text,
            "language": _guess_language(text),
        }


def _guess_language(text: str) -> str:
    if not text:
        return "es"
    es_markers = ("para", "experiencia", "conocimientos", "imprescindible", "valorable")
    score_es = sum(1 for m in es_markers if m in text.lower())
    return "es" if score_es >= 2 else "en"
