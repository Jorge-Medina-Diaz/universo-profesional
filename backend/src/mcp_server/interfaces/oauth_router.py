"""OAuth 2.1 Authorization Server endpoints — RFC 8414 + 7591 + 8707 + 7636.

Endpoints:
  POST /auth/oauth/register   (DCR, RFC 7591)
  GET  /auth/oauth/authorize  (renders consent screen + handles approval)
  POST /auth/oauth/token      (code → token; refresh → token)
  POST /auth/oauth/revoke     (RFC 7009)
"""
from __future__ import annotations

import html
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.identity.infrastructure.repositories import SqlAlchemyUserRepository
from src.identity.interfaces.api.deps import SessionDep
from src.mcp_server.domain.scopes import DEFAULT_SCOPES, SCOPES, validate_scopes
from src.mcp_server.infrastructure.oauth_store import OAuthStore
from src.shared.config import get_settings
from src.shared.rate_limit import limiter
from src.shared.security import (
    encode_jwt,
    generate_token,
    utc_in,
    utc_now,
    verify_password,
)

router = APIRouter()


# --- DCR (RFC 7591) -------------------------------------------------------


class RegisterClientRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)
    redirect_uris: list[str] = Field(default_factory=list)
    grant_types: list[str] | None = None
    scope: str | None = None
    token_endpoint_auth_method: str = "none"
    software_id: str | None = None
    software_version: str | None = None


def _validate_redirect_uri(uri: str) -> None:
    """Enforce a safe redirect_uri policy (RFC 8252) at registration so DCR
    can't be used to register an open redirect for token exfiltration:
      * https required, EXCEPT http on loopback (127.0.0.1/::1/localhost);
      * no wildcards; no URL fragment.
    """
    from urllib.parse import urlsplit

    if "*" in uri:
        raise HTTPException(status_code=400, detail="redirect_uri may not contain wildcards")
    parts = urlsplit(uri)
    if parts.fragment:
        raise HTTPException(status_code=400, detail="redirect_uri may not contain a fragment")
    host = (parts.hostname or "").lower()
    is_loopback = host in ("127.0.0.1", "::1", "localhost")
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and is_loopback:
        return
    raise HTTPException(
        status_code=400,
        detail="redirect_uri must be https (http allowed only for loopback)",
    )


@router.post("/register")
@limiter.limit("10/hour")
async def register_client(
    request: Request,
    body: RegisterClientRequest,
    session: SessionDep,
) -> dict[str, Any]:
    # Open DCR per RFC 7591, but unauthenticated + unthrottled is a table-flood
    # vector — rate-limit by IP (no auth header pre-registration).
    requested = body.scope.split() if body.scope else list(DEFAULT_SCOPES)
    valid_scopes = validate_scopes(requested) or list(DEFAULT_SCOPES)
    valid_methods = ["none"]
    if body.token_endpoint_auth_method not in valid_methods:
        raise HTTPException(status_code=400, detail="Only 'none' (PKCE-only) supported")
    if not body.redirect_uris:
        raise HTTPException(status_code=400, detail="At least one redirect_uri required")
    for uri in body.redirect_uris:
        _validate_redirect_uri(uri)
    store = OAuthStore(session)
    cid = await store.register_client(
        client_name=body.client_name,
        redirect_uris=body.redirect_uris,
        scopes=valid_scopes,
        grant_types=body.grant_types or ["authorization_code", "refresh_token"],
        token_endpoint_auth_method=body.token_endpoint_auth_method,
        software_id=body.software_id,
        software_version=body.software_version,
    )
    await session.commit()
    return {
        "client_id": str(cid),
        "client_name": body.client_name,
        "redirect_uris": body.redirect_uris,
        "grant_types": body.grant_types or ["authorization_code", "refresh_token"],
        "token_endpoint_auth_method": body.token_endpoint_auth_method,
        "scope": " ".join(valid_scopes),
        "client_id_issued_at": int(utc_now().timestamp()),
    }


# --- Authorize -----------------------------------------------------------


@router.get("/authorize", response_class=HTMLResponse)
async def authorize_get(
    request: Request,
    session: SessionDep,
    client_id: str = Query(...),
    response_type: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(""),
    state: str | None = Query(None),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    resource: str | None = Query(None),
) -> HTMLResponse:
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Only response_type=code supported")
    store = OAuthStore(session)
    try:
        cid = UUID(client_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid client_id") from None
    client = await store.get_client(cid)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")
    settings = get_settings()
    resource = resource or settings.mcp_canonical_uri
    requested = validate_scopes(scope.split() if scope else list(DEFAULT_SCOPES))
    scope_details = [
        {"name": s, "description": SCOPES[s].description, "destructive": SCOPES[s].destructive}
        for s in requested
    ]

    # Render consent page server-side. The user logs in with email+password
    # inline (we don't have session cookies in MCP flows yet; this is simpler).
    html = _render_consent(
        client_name=client.client_name,
        scope_details=scope_details,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=" ".join(requested),
        state=state or "",
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    return HTMLResponse(content=html)


@router.post("/authorize")
async def authorize_post(
    request: Request,
    session: SessionDep,
    email: str = Form(...),
    password: str = Form(...),
    consent: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(""),
    state: str = Form(""),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form("S256"),
    resource: str = Form(...),
) -> RedirectResponse:
    # CSRF defence-in-depth: this POST both authenticates (email/password) and
    # grants consent, so a cross-site form could drive a forced login+consent.
    # Reject when an Origin/Referer is present and not same-origin. (Missing
    # header is allowed so the server-rendered same-origin form still works.)
    from urllib.parse import urlsplit

    origin = request.headers.get("origin") or request.headers.get("referer")
    if origin:
        expected = urlsplit(get_settings().canonical_base_url)
        got = urlsplit(origin)
        if (got.scheme, got.netloc) != (expected.scheme, expected.netloc):
            raise HTTPException(status_code=403, detail="cross-origin request rejected")

    if consent != "approve":
        return RedirectResponse(
            url=f"{redirect_uri}?error=access_denied&state={state}",
            status_code=302,
        )

    users = SqlAlchemyUserRepository(session)
    user = await users.get_by_email(email.strip().lower())
    if user is None or user.is_deleted or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    store = OAuthStore(session)
    cid = UUID(client_id)
    code = generate_token(32)
    scopes_list = validate_scopes(scope.split() if scope else list(DEFAULT_SCOPES))
    await store.store_code(
        code=code,
        client_id=cid,
        user_id=user.id,
        redirect_uri=redirect_uri,
        scopes=scopes_list,
        resource=resource,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=utc_in(minutes=10),
    )
    await session.commit()
    sep = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        url=f"{redirect_uri}{sep}code={code}&state={state}",
        status_code=302,
    )


# --- Token ---------------------------------------------------------------


@router.post("/token")
async def token(
    session: SessionDep,
    grant_type: str = Form(...),
    code: str | None = Form(None),
    refresh_token: str | None = Form(None),
    redirect_uri: str | None = Form(None),
    client_id: str = Form(...),
    code_verifier: str | None = Form(None),
    resource: str | None = Form(None),
) -> JSONResponse:
    store = OAuthStore(session)
    settings = get_settings()
    try:
        cid = UUID(client_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid client_id") from None

    if grant_type == "authorization_code":
        if not code or not code_verifier:
            raise HTTPException(status_code=400, detail="code + code_verifier required")
        row = await store.consume_code(code=code, client_id=cid, code_verifier=code_verifier)
        if row is None:
            raise HTTPException(status_code=400, detail="Invalid or expired code")
        if redirect_uri is not None and redirect_uri != row.redirect_uri:
            raise HTTPException(status_code=400, detail="redirect_uri mismatch")
        user_id = row.user_id
        scopes_list = list(row.scopes)
        bound_resource = row.resource
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")
        new_refresh = generate_token(48)
        rotated = await store.rotate_refresh(
            refresh=refresh_token,
            new_refresh=new_refresh,
            client_id=cid,
            new_expires_at=utc_in(days=settings.jwt_oauth_refresh_ttl_days),
        )
        if rotated is None:
            raise HTTPException(status_code=400, detail="Invalid or revoked refresh_token")
        user_id = rotated.user_id
        scopes_list = list(rotated.scopes)
        bound_resource = rotated.resource
        # Issue new refresh + access pair
        # Persist the new refresh (rotation already revoked the old one)
        await store.store_token(
            token=new_refresh,
            kind="refresh",
            user_id=user_id,
            client_id=cid,
            scopes=scopes_list,
            resource=bound_resource,
            expires_at=utc_in(days=settings.jwt_oauth_refresh_ttl_days),
        )
        access = _new_access_token(
            user_id=user_id,
            client_id=cid,
            scopes=scopes_list,
            resource=bound_resource,
        )
        # No code/PKCE for refresh — persist access too for revocation tracking
        await store.store_token(
            token=access,
            kind="access",
            user_id=user_id,
            client_id=cid,
            scopes=scopes_list,
            resource=bound_resource,
            expires_at=utc_in(minutes=settings.jwt_oauth_access_ttl_minutes),
        )
        await session.commit()
        return JSONResponse(
            {
                "access_token": access,
                "token_type": "Bearer",
                "expires_in": settings.jwt_oauth_access_ttl_minutes * 60,
                "refresh_token": new_refresh,
                "scope": " ".join(scopes_list),
            }
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant_type")

    # Issue tokens for authorization_code grant
    if resource is not None and resource != bound_resource:
        raise HTTPException(
            status_code=400, detail="resource indicator does not match authorization"
        )
    access = _new_access_token(
        user_id=user_id, client_id=cid, scopes=scopes_list, resource=bound_resource
    )
    new_refresh = generate_token(48)
    await store.store_token(
        token=access,
        kind="access",
        user_id=user_id,
        client_id=cid,
        scopes=scopes_list,
        resource=bound_resource,
        expires_at=utc_in(minutes=settings.jwt_oauth_access_ttl_minutes),
    )
    await store.store_token(
        token=new_refresh,
        kind="refresh",
        user_id=user_id,
        client_id=cid,
        scopes=scopes_list,
        resource=bound_resource,
        expires_at=utc_in(days=settings.jwt_oauth_refresh_ttl_days),
    )
    await store.touch_client(cid)
    await session.commit()
    return JSONResponse(
        {
            "access_token": access,
            "token_type": "Bearer",
            "expires_in": settings.jwt_oauth_access_ttl_minutes * 60,
            "refresh_token": new_refresh,
            "scope": " ".join(scopes_list),
        }
    )


# --- Revoke (RFC 7009) ---------------------------------------------------


@router.post("/revoke")
async def revoke(
    session: SessionDep,
    token: str = Form(...),
    token_type_hint: str | None = Form(None),
) -> dict[str, bool]:
    store = OAuthStore(session)
    await store.revoke_token(token)
    await session.commit()
    return {"ok": True}


# --- Helpers ------------------------------------------------------------


def _new_access_token(
    *, user_id: UUID, client_id: UUID, scopes: list[str], resource: str
) -> str:
    settings = get_settings()
    now = utc_now()
    claims = {
        "sub": str(user_id),
        "client_id": str(client_id),
        "iss": settings.canonical_base_url,
        "aud": resource,
        "iat": int(now.timestamp()),
        "exp": int(utc_in(minutes=settings.jwt_oauth_access_ttl_minutes).timestamp()),
        "scope": " ".join(scopes),
        "token_type": "access",
    }
    return encode_jwt(claims)


def _render_consent(
    *,
    client_name: str,
    scope_details: list[dict[str, Any]],
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    resource: str,
) -> str:
    # Escape every externally-supplied value before HTML interpolation. The DCR
    # client_name, redirect_uri, scope, state and PKCE challenge are all
    # attacker-controlled, so raw f-string interpolation is a stored-XSS vector.
    client_name = html.escape(client_name)
    client_id = html.escape(client_id)
    redirect_uri = html.escape(redirect_uri)
    scope = html.escape(scope)
    state = html.escape(state)
    code_challenge = html.escape(code_challenge)
    code_challenge_method = html.escape(code_challenge_method)
    resource = html.escape(resource)
    rows = "".join(
        f"<li><strong>{html.escape(str(s['name']))}</strong>"
        f"{' (destructivo)' if s['destructive'] else ''}: "
        f"{html.escape(str(s['description']))}</li>"
        for s in scope_details
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Autorizar {client_name}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 4rem auto; padding: 0 1rem; }}
    h1 {{ font-size: 1.4rem; }}
    .scopes {{ background: #f6f6f8; padding: 12px 18px; border-radius: 8px; }}
    label {{ display: block; margin: .5rem 0; }}
    input[type=text], input[type=email], input[type=password] {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }}
    .actions {{ margin-top: 1rem; display: flex; gap: 1rem; }}
    button {{ padding: .6rem 1rem; border-radius: 6px; border: none; cursor: pointer; font-size: 1rem; }}
    button.primary {{ background: #1f6feb; color: white; }}
    button.secondary {{ background: #eee; }}
    .resource {{ font-size: .8rem; color: #666; margin-top: 1rem; }}
  </style>
</head>
<body>
  <h1>«{client_name}» pide acceso a tu Universo Profesional</h1>
  <p>Para concederlo, inicia sesión y acepta los permisos:</p>
  <div class="scopes"><ul>{rows}</ul></div>
  <form method="post" action="/auth/oauth/authorize">
    <label>Email <input type="email" name="email" required autocomplete="email"></label>
    <label>Contraseña <input type="password" name="password" required autocomplete="current-password"></label>
    <input type="hidden" name="client_id" value="{client_id}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
    <input type="hidden" name="scope" value="{scope}">
    <input type="hidden" name="state" value="{state}">
    <input type="hidden" name="code_challenge" value="{code_challenge}">
    <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
    <input type="hidden" name="resource" value="{resource}">
    <div class="actions">
      <button class="primary" name="consent" value="approve" type="submit">Permitir</button>
      <button class="secondary" name="consent" value="deny" type="submit">Denegar</button>
    </div>
  </form>
  <p class="resource">Recurso: <code>{resource}</code></p>
</body>
</html>"""
