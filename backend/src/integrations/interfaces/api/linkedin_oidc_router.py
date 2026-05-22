"""LinkedIn OIDC sign-in router: /api/v1/auth/linkedin/{authorize,callback}.

Why a separate router (vs sticking it inside `integrations/router.py`)?
OIDC sign-in is an *authentication* surface — it ends up issuing our own
JWT/refresh tokens, exactly like /auth/login. Keeping it under /api/v1/auth/
makes the security-relevant surface obvious to anyone auditing routes.

Two entry points:
  GET /api/v1/auth/linkedin/authorize           — fresh sign-in (no user yet)
  GET /api/v1/auth/linkedin/authorize?link=true — link to currently authed user

Both build the LinkedIn URL with a signed state token. The callback shape is
the same regardless of which path issued the state.
"""
from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from src.identity.infrastructure.repositories import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)
from src.identity.interfaces.api.deps import SessionDep, get_request_meta
from src.identity.interfaces.api.schemas import TokenResponse
from src.integrations.application.linkedin_oidc import (
    LinkedInOidcSignIn,
    issue_state,
    parse_state,
)
from src.integrations.infrastructure.linkedin_oidc_client import (
    build_authorize_url,
    exchange_code_for_token,
    fetch_userinfo,
)
from src.integrations.infrastructure.repositories import SqlExternalAccountRepository
from src.shared.config import get_settings
from src.shared.errors import ValidationError
from src.shared.uow import unit_of_work

router = APIRouter()


def _linkedin_redirect_uri() -> str:
    s = get_settings()
    return f"{s.canonical_base_url}/api/v1/auth/linkedin/callback"


@router.get("/authorize")
async def linkedin_authorize(
    link_to_user_id: str | None = Query(default=None, alias="link"),
) -> dict[str, str | bool]:
    """Return the LinkedIn OIDC authorize URL.

    Always returns 200 — when LinkedIn isn't configured we return an empty
    `authorize_url` plus `configured: false`, so the frontend can hide the
    button gracefully instead of seeing a noisy 503. The frontend is
    responsible for not redirecting when `configured=false`.
    """
    s = get_settings()
    if not s.linkedin_client_id:
        return {"authorize_url": "", "state": "", "configured": False}
    state = issue_state(link_user_id=link_to_user_id)
    url = build_authorize_url(
        client_id=s.linkedin_client_id,
        redirect_uri=_linkedin_redirect_uri(),
        state=state,
    )
    return {"authorize_url": url, "state": state, "configured": True}


@router.get("/callback")
async def linkedin_callback(
    request: Request,
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> Any:
    """LinkedIn redirects here after consent.

    On success: we exchange the code, fetch userinfo, sign in / sign up the user,
    and redirect back to the frontend with the JWT in the URL fragment so the
    SPA can pick it up without server-side session. (Fragment ⇒ never sent
    to the server, kept client-side only.)
    """
    s = get_settings()
    front = s.frontend_base_url

    if error:
        return RedirectResponse(
            url=f"{front}/#/login?oauth_error={error}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    if not s.linkedin_client_id or not s.linkedin_client_secret:
        raise HTTPException(status_code=503, detail="LinkedIn OAuth not configured")

    try:
        parsed_state = parse_state(state)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        token_bundle = await exchange_code_for_token(
            client_id=s.linkedin_client_id,
            client_secret=s.linkedin_client_secret,
            code=code,
            redirect_uri=_linkedin_redirect_uri(),
        )
        access_token = token_bundle["access_token"]
        userinfo = await fetch_userinfo(access_token)
    except httpx.HTTPStatusError as exc:
        return RedirectResponse(
            url=f"{front}/#/login?oauth_error={exc.response.status_code}",
            status_code=302,
        )

    meta = get_request_meta(request)
    uc = LinkedInOidcSignIn(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        accounts=SqlExternalAccountRepository(session),
    )
    async with unit_of_work(session) as uow:
        result = await uc.execute(
            userinfo=userinfo,
            access_token=access_token,
            expires_in=token_bundle.get("expires_in"),
            user_agent=meta["user_agent"],
            ip_address=meta["ip_address"],
            state=parsed_state,
            uow=uow,
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        payload = result.value  # type: ignore[union-attr]

    # SPA picks up tokens from the fragment (#access_token=…)
    fragment = (
        f"access_token={payload.tokens.access_token}"
        f"&refresh_token={payload.tokens.refresh_token}"
        f"&user_id={payload.tokens.user_id}"
        f"&email={payload.tokens.email}"
        f"&created={int(payload.created)}"
        f"&linked={int(payload.linked)}"
    )
    return RedirectResponse(
        url=f"{front}/#/auth/linkedin/callback?{fragment}",
        status_code=302,
    )


# Optional JSON-style callback for non-browser clients (CLI / MCP)
@router.post("/exchange", response_model=TokenResponse)
async def linkedin_exchange(
    request: Request,
    session: SessionDep,
    body: dict[str, Any],
) -> TokenResponse:
    """Server-side code exchange — for clients that don't want a redirect.

    Body: { "code": "...", "state": "..." }
    """
    s = get_settings()
    if not s.linkedin_client_id or not s.linkedin_client_secret:
        raise HTTPException(status_code=503, detail="LinkedIn OAuth not configured")

    code = body.get("code")
    state = body.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="code and state are required")
    parsed_state = parse_state(state)

    token_bundle = await exchange_code_for_token(
        client_id=s.linkedin_client_id,
        client_secret=s.linkedin_client_secret,
        code=code,
        redirect_uri=_linkedin_redirect_uri(),
    )
    access_token = token_bundle["access_token"]
    userinfo = await fetch_userinfo(access_token)

    meta = get_request_meta(request)
    uc = LinkedInOidcSignIn(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        accounts=SqlExternalAccountRepository(session),
    )
    async with unit_of_work(session) as uow:
        result = await uc.execute(
            userinfo=userinfo,
            access_token=access_token,
            expires_in=token_bundle.get("expires_in"),
            user_agent=meta["user_agent"],
            ip_address=meta["ip_address"],
            state=parsed_state,
            uow=uow,
        )
        if result.is_failure:
            raise result.error  # type: ignore[union-attr]
        await uow.commit()
        payload = result.value  # type: ignore[union-attr]
    return TokenResponse(
        access_token=payload.tokens.access_token,
        refresh_token=payload.tokens.refresh_token,
        user_id=payload.tokens.user_id,
        email=payload.tokens.email,
    )
