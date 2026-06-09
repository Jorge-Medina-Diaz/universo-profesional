"""20-turn chat latency baseline against the AG-UI bridge.

Measures the CLIENT-side view (TT-first-byte, TT-first-visible-frame, total)
of N representative turns; the server logs the per-stage breakdown via
`agent_run_stages` (stream_metrics.RunTimer) and the
`cvs_agent_stage_seconds` histogram. Run BEFORE and AFTER each Phase 1
optimization — the phase gate is judged against this script's output.

Usage (in-container, real LLM key configured):
    docker exec cvs-backend python -m scripts.latency_baseline \
        --base-url http://localhost:8000 --turns 20

Creates/reuses a dedicated baseline user. Sequential turns (respects the
per-user concurrency guard and the 60/min rate limit).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import uuid

import httpx

EMAIL = "latency-baseline@example.com"
PASSWORD = "LatencyBaseline123!"

# Representative mix: routine chat, capture, retrieval, analysis, documents.
TURNS = [
    "Hola, ¿qué puedes hacer por mí?",
    "Esta semana estuve trabajando en una migración de Postgres a la nube",
    "Aprendí bastante de Terraform en el proceso",
    "¿Qué skills tengo registradas hasta ahora?",
    "Añade que tengo experiencia con Apache AGE",
    "¿Cómo está mi perfil para un puesto de backend senior?",
    "Cuéntame algo interesante sobre mi trayectoria",
    "¿Qué me falta para mejorar mi perfil de datos?",
    "Hice un side project: un bot de Telegram con LLMs",
    "¿Qué certificaciones me recomendarías?",
    "Resume mi experiencia más reciente",
    "¿Tengo algo de frontend en mi universo?",
    "Estuve practicando Kubernetes este mes",
    "¿Qué proyectos tengo registrados?",
    "Dame ideas para mi portfolio",
    "¿Cómo se relacionan mis skills de cloud con mis proyectos?",
    "Apunta que di una charla interna sobre RAG",
    "¿Qué idiomas tengo en el perfil?",
    "¿Qué debería preparar para una entrevista técnica?",
    "Gracias, ¿algo más que deba completar?",
]


async def _ensure_user(client: httpx.AsyncClient) -> str:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": EMAIL, "password": PASSWORD, "display_name": "Latency Baseline"},
    )
    if reg.status_code not in (201, 409):
        print(f"register unexpected: {reg.status_code} {reg.text[:200]}")
    login = await client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    login.raise_for_status()
    return login.json()["access_token"]


def _run_body(text: str, user_msg_id: str) -> dict:
    return {
        "threadId": "baseline",  # server enforces main-<uid> anyway
        "runId": str(uuid.uuid4()),
        "messages": [{"id": user_msg_id, "role": "user", "content": text}],
        "state": {},
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }


async def _one_turn(
    client: httpx.AsyncClient, token: str, text: str
) -> dict[str, float]:
    t0 = time.monotonic()
    ttfb = ttft = None
    async with client.stream(
        "POST",
        "/agui/agent/universe_coordinator/run",
        json=_run_body(text, str(uuid.uuid4())),
        headers={"Authorization": f"Bearer {token}"},
        timeout=180.0,
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            now = time.monotonic() - t0
            if ttfb is None and line:
                ttfb = now
            if ttft is None and line.startswith("data:"):
                try:
                    payload = json.loads(line[5:])
                except ValueError:
                    continue
                if payload.get("type") in (
                    "TEXT_MESSAGE_CONTENT",
                    "TOOL_CALL_START",
                ):
                    ttft = now
    total = time.monotonic() - t0
    return {"ttfb": ttfb or total, "ttft": ttft or total, "total": total}


def _pct(values: list[float], q: float) -> float:
    return statistics.quantiles(values, n=100)[int(q) - 1] if len(values) > 1 else values[0]


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--turns", type=int, default=len(TURNS))
    args = ap.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url) as client:
        token = await _ensure_user(client)
        results: list[dict[str, float]] = []
        for i, text in enumerate(TURNS[: args.turns], 1):
            try:
                r = await _one_turn(client, token, text)
            except Exception as exc:  # keep the baseline honest: record failures
                print(f"[{i:02d}] FAILED: {exc}")
                continue
            results.append(r)
            print(
                f"[{i:02d}] ttfb={r['ttfb']:.2f}s ttft={r['ttft']:.2f}s "
                f"total={r['total']:.2f}s  {text[:48]!r}"
            )
            await asyncio.sleep(1.0)  # stay under the per-minute rate limit

        if not results:
            print("no successful turns")
            sys.exit(1)
        print("\n=== BASELINE SUMMARY ===")
        for key in ("ttfb", "ttft", "total"):
            vals = sorted(r[key] for r in results)
            print(
                f"{key:>5}: p50={_pct(vals, 50):.2f}s "
                f"p95={_pct(vals, 95):.2f}s "
                f"min={vals[0]:.2f}s max={vals[-1]:.2f}s n={len(vals)}"
            )
        print(
            "\nServer-side stage breakdown: docker logs cvs-backend | "
            "grep agent_run_stages  (or /metrics: cvs_agent_stage_seconds)"
        )


if __name__ == "__main__":
    asyncio.run(main())
