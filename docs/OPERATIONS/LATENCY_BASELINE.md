# Chat latency baseline — pre-optimization record (2026-06-10)

Recorded with `backend/scripts/latency_baseline.py` (20 Spanish turns, real
Anthropic, dev docker stack, warm team cache) at commit `5fa6624`.
**Every Phase-1 optimization is judged against these numbers.**

## Client-side (what the user feels)

| metric | p50 | p95 | min | max |
|---|---|---|---|---|
| ttfb (first SSE byte) | 0.01s | 0.01s | 0.01s | 0.01s |
| **ttft (first visible text/tool)** | **6.63s** | **13.79s** | 3.80s | 13.85s |
| **total (run closed)** | **14.62s** | **23.43s** | 3.80s | 23.48s |

Cold start (first turn after backend boot): ttft 60.9s (team build 1.5s +
first-run memory/session bootstrap + uncached prompt writes).

## Server-side stage means (23 runs, `cvs_agent_stage_seconds`)

| stage | mean elapsed | delta from previous |
|---|---|---|
| auth_done / validated | ~0.000s | — |
| team_resolved | 0.07s | cache hit ≈ 0 (cold: 1.55s) |
| intent_done | 1.51s | **+1.51s — IntentRouter LLM classify + provider context, ON the hot path** |
| run_started | 1.51s | +0.00s |
| ttft | 9.89s | **+8.4s — coordinator route hop + member first token** |
| stream_done | 17.29s | **+7.4s — generation tail + agno post-run memory/summary passes holding the run open** |

## Ranked attack list (plan mapping)

1. **Coordinator hop (~8.4s)** → P1.D consolidation (27→7 members shrinks
   the routing prompt + misroutes) + P1.E tier routing & multi-block 1h cache.
2. **Post-response overhang (~7.4s)** → P1.C kill the redundant memory layer;
   evaluate moving agno memory consolidation off-run.
3. **Intent router (~1.5s, up to 5.1s)** → P1.E: hard timeout + keyword
   fast-path first + cheaper model; run concurrently with team start if the
   session_state injection can tolerate it.

Phase gate: ttft p50 < 0.8s · total p50 < 2.5s · input tokens/turn −40%.

## How to re-run

```bash
docker exec cvs-backend python -m scripts.latency_baseline --turns 20
docker logs cvs-backend | grep agent_run_stages   # per-run stage breakdown
curl -s localhost:8000/metrics | grep cvs_agent_stage_seconds
```
