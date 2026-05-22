"""Grounding invariants for AiLlmClient (pure — no DB, no real LLM).

The product promise is "el agente adapta tu universo, no inventa nada que no
tengas". AiLlmClient enforces that by construction: the *structure* always
comes from the grounded MockLlmClient (real entities), and the LLM pass only
rephrases prose, merged back by index. These tests lock that in:

  • tailored summary + per-work highlights are merged onto the grounded base
  • an out-of-range work index from the model is ignored (can't inject a job)
  • an LLM failure degrades to the grounded base untouched
  • an empty profile skips the LLM entirely
"""
from __future__ import annotations

from typing import Any

import pytest

from src.documents.infrastructure.llm_client import (
    AiLlmClient,
    _TailoredCoverLetter,
    _TailoredCv,
    _TailoredWorkEntry,
)


class _FakeGrounded:
    """Stand-in for the MockLlmClient grounded base."""

    def __init__(self, resume: dict[str, Any], cover: dict[str, Any] | None = None) -> None:
        self._resume = resume
        self._cover = cover or {"basics": {"summary": "base"}, "cover_letter_body": "base", "meta": {}}

    async def generate_cv_bullets(self, **_: Any) -> dict[str, Any]:
        # Deep-ish copy so the client mutating the result can't leak across calls.
        import copy

        return copy.deepcopy(self._resume)

    async def generate_cover_letter(self, **_: Any) -> dict[str, Any]:
        import copy

        return copy.deepcopy(self._cover)


class _FakeLlm:
    def __init__(self, *, result: Any = None, exc: Exception | None = None) -> None:
        self._result = result
        self._exc = exc
        self.calls = 0

    async def structured(self, **_: Any) -> Any:
        self.calls += 1
        if self._exc is not None:
            raise self._exc
        return self._result


def _client(grounded: _FakeGrounded, llm: _FakeLlm) -> AiLlmClient:
    # Bypass __init__ so the test never touches a real session or provider.
    c = AiLlmClient.__new__(AiLlmClient)
    c._session = None  # type: ignore[attr-defined]
    c._grounded = grounded  # type: ignore[attr-defined]
    c._llm = llm  # type: ignore[attr-defined]
    return c


_JOB = {"title": "Engineer", "company": "Acme", "ats_keywords": ["FastAPI"]}


@pytest.mark.asyncio
async def test_summary_and_highlights_merged() -> None:
    grounded = _FakeGrounded(
        {
            "basics": {"name": "Ada", "summary": "old summary"},
            "work": [{"name": "Acme", "position": "Dev", "highlights": ["old bullet"]}],
            "skills": [{"name": "FastAPI"}],
            "meta": {"generated_by": "cvs-saas MockLlmClient"},
        }
    )
    llm = _FakeLlm(
        result=_TailoredCv(
            summary="tailored summary",
            work=[_TailoredWorkEntry(index=0, summary="new role", highlights=["new bullet"])],
        )
    )
    out = await _client(grounded, llm).generate_cv_bullets(
        job_summary=_JOB, retrieved=[], language="es", tone="professional"
    )
    assert out["basics"]["summary"] == "tailored summary"
    assert out["work"][0]["highlights"] == ["new bullet"]
    assert out["work"][0]["summary"] == "new role"
    assert out["meta"]["generated_by"].startswith("cvs-saas AiLlmClient")


@pytest.mark.asyncio
async def test_out_of_range_work_index_ignored() -> None:
    """The model cannot inject a job: an index past the real entries is dropped."""
    grounded = _FakeGrounded(
        {
            "basics": {"summary": "s"},
            "work": [{"name": "Acme", "highlights": ["real"]}],
            "skills": [{"name": "Go"}],
            "meta": {},
        }
    )
    llm = _FakeLlm(
        result=_TailoredCv(
            summary="ok",
            work=[_TailoredWorkEntry(index=5, highlights=["fabricated job bullet"])],
        )
    )
    out = await _client(grounded, llm).generate_cv_bullets(
        job_summary=_JOB, retrieved=[], language="es", tone=None
    )
    assert len(out["work"]) == 1  # no entry injected
    assert out["work"][0]["highlights"] == ["real"]  # untouched


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_grounded() -> None:
    grounded = _FakeGrounded(
        {
            "basics": {"summary": "grounded summary"},
            "work": [],
            "skills": [{"name": "FastAPI"}],
            "meta": {"generated_by": "cvs-saas MockLlmClient"},
        }
    )
    llm = _FakeLlm(exc=RuntimeError("provider down"))
    out = await _client(grounded, llm).generate_cv_bullets(
        job_summary=_JOB, retrieved=[], language="es", tone=None
    )
    assert out["basics"]["summary"] == "grounded summary"
    assert out["meta"]["generated_by"] == "cvs-saas MockLlmClient"


@pytest.mark.asyncio
async def test_empty_profile_skips_llm() -> None:
    grounded = _FakeGrounded(
        {"basics": {}, "work": [], "skills": [], "projects": [], "meta": {}}
    )
    llm = _FakeLlm(result=_TailoredCv(summary="should not be used"))
    out = await _client(grounded, llm).generate_cv_bullets(
        job_summary=_JOB, retrieved=[], language="es", tone=None
    )
    assert llm.calls == 0
    assert out["skills"] == []


@pytest.mark.asyncio
async def test_cover_letter_uses_tailored_body() -> None:
    grounded = _FakeGrounded(
        resume={
            "basics": {"summary": "s"},
            "work": [],
            "skills": [{"name": "FastAPI"}],
            "meta": {},
        },
        cover={"basics": {"summary": "base body"}, "cover_letter_body": "base body", "meta": {}},
    )
    llm = _FakeLlm(result=_TailoredCoverLetter(body="Dear Acme, ...grounded body..."))
    out = await _client(grounded, llm).generate_cover_letter(
        job_summary=_JOB, retrieved=[], language="es", tone="professional"
    )
    assert out["cover_letter_body"] == "Dear Acme, ...grounded body..."
    assert out["basics"]["summary"] == "Dear Acme, ...grounded body..."
    assert out["meta"]["generated_by"].startswith("cvs-saas AiLlmClient")


@pytest.mark.asyncio
async def test_cover_letter_empty_profile_returns_base() -> None:
    grounded = _FakeGrounded(
        resume={"basics": {}, "work": [], "skills": [], "projects": [], "meta": {}},
        cover={"basics": {"summary": "base"}, "cover_letter_body": "base", "meta": {}},
    )
    llm = _FakeLlm(result=_TailoredCoverLetter(body="unused"))
    out = await _client(grounded, llm).generate_cover_letter(
        job_summary=_JOB, retrieved=[], language="es", tone=None
    )
    assert llm.calls == 0
    assert out["cover_letter_body"] == "base"
