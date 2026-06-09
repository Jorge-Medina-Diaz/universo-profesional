"""AgentOS runtime mounted as an isolated sub-app (flag: agentos_enabled).

Architecture decision (transformation plan P1.B): our CopilotKit-facing
transport at /agui/* implements behaviors the stock AgentOS AGUI interface
does not (passive connect channel, single-thread enforcement, proposal-id
injection, stream cleaning, rate limits) — so AgentOS is adopted UNDERNEATH
as the runtime/ops substrate, not as a router swap:

- mounted at /os as a Starlette sub-app → its JWT middleware applies ONLY to
  AgentOS routes by construction (no excluded-path lists), zero route
  conflicts with /agui or the REST API, rollback = flip the flag off.
- gives us the ops surface (sessions/memories/config/control-plane) and the
  stock AG-UI endpoint at /os/agui for A/B against our bridge.
- the platform Team object is THE SAME cached instance the bridge uses
  (get_universe_team), so sessions/memory inspected via /os are the live
  ones. BYOK per-user teams intentionally stay outside AgentOS — they are
  resolved per-request in build_team_for_user and never registered.

Known caveats (documented, accepted):
- Starlette does NOT run a mounted sub-app's lifespan; AgentOS must not rely
  on startup hooks here → auto_provision_dbs=False (tables already exist;
  the runtime role cvs_app is a non-owner and must not run DDL anyway).
- telemetry off (AGNO_TELEMETRY policy).
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI

logger = structlog.get_logger(__name__)


def build_agentos_subapp() -> FastAPI:
    from agno.os import AgentOS
    from agno.os.interfaces.agui import AGUI
    from agno.os.middleware import JWTMiddleware

    from src.agents.factory import get_universe_team
    from src.shared.security import get_public_key

    team = get_universe_team()
    agent_os = AgentOS(
        id="cvs-saas",
        name="Universo Profesional",
        description="Professional digital-twin agent runtime",
        teams=[team],
        # The TEAM's db instance, not a fresh _build_db(): two AsyncPostgresDb
        # objects register as two database ids and every ops route then
        # demands an explicit db_id query param.
        db=team.db,
        interfaces=[AGUI(team=team)],
        telemetry=False,
        auto_provision_dbs=False,
    )
    os_app = agent_os.get_app()
    # Same RS256 keypair + audience as the REST API: one JWT verifier story.
    os_app.add_middleware(
        JWTMiddleware,
        verification_keys=[get_public_key().decode("utf-8")],
        algorithm="RS256",
        audience="cvs-saas-api",
        verify_audience=True,
        user_id_claim="sub",
        # Per-user resource isolation on the ops routes (/sessions, /memories):
        # a user's token only reaches that user's rows.
        user_isolation=True,
    )
    logger.info("agentos_mounted", routes=len(os_app.routes))
    return os_app
