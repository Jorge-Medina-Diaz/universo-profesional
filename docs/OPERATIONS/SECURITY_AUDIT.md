# Security Audit — Universo Profesional

**Date:** 2026-05-26
**Auditor:** Agent (automated focused audit)
**Scope:** Backend JWT/auth layer, MCP OAuth validation, identity API endpoints, security headers middleware

---

## 1. Trivy Scan

**Status:** Skipped — Trivy is not installed in the local environment.

> Recommendation: Install Trivy (`https://aquasecurity.github.io/trivy/`) and re-run `trivy fs --severity HIGH,CRITICAL backend/` in CI and before each release.

---

## 2. Files Reviewed

| File | Purpose |
|------|---------|
| `backend/src/shared/security.py` | Password hashing (Argon2), JWT key generation (RSA 2048), JWT encode/decode |
| `backend/src/mcp_server/server.py` | MCP server OAuth 2.1 Bearer token validation, scope checks |
| `backend/src/identity/interfaces/api/router.py` | Auth endpoints: register, login, refresh, verify, password reset |
| `backend/src/shared/config.py` | Environment config, production-ready validation |
| `backend/src/shared/middleware.py` | Security headers middleware |
| `.env.example` | Dev defaults and production override documentation |

---

## 3. Findings

### 🔶 Medium — Missing rate limiting on sensitive endpoints

**Location:** `backend/src/identity/interfaces/api/router.py`

Three auth endpoints do **not** have `@limiter.limit(...)` decorators:

- `POST /api/v1/auth/refresh` — refresh token can be submitted repeatedly (rotation helps, but endpoint is still hammerable)
- `POST /api/v1/auth/verify` — email verification token can be brute-forced (short 32-byte token, but no rate cap)
- `POST /api/v1/auth/password-reset/confirm` — password reset token can be brute-forced

**Currently protected endpoints (for comparison):**
- `/register` → 10/hour
- `/login` → 10/15minutes
- `/password-reset` → 3/hour

> **Recommendation:** Add `@limiter.limit("10/minute")` or stricter limits to `/refresh`, `/verify`, and `/password-reset/confirm`.

---

### 🔶 Low — JWT encoder does not enforce `exp` claim

**Location:** `backend/src/shared/security.py` (`encode_jwt`)

`encode_jwt` is a thin wrapper around `jose.jwt.encode`. It does **not** automatically inject an `exp` claim; callers must provide it. All current callers *do* add `exp` (access tokens = 15 min, LinkedIn OIDC state = 5 min, MCP OAuth tokens = configurable TTL), but a future developer could accidentally create a non-expiring token.

> **Recommendation:** Add an optional `exp` guard in `encode_jwt` that warns or raises when `exp` is missing (defense in depth). Do not change existing call sites.

---

### 🔶 Low — DNS rebinding protection disabled in MCP SSE transport

**Location:** `backend/src/mcp_server/server.py:204`

```python
transport = SseServerTransport(
    "/messages/",
    security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)
```

This is likely intentional for local Docker networking, but should be revisited for production.

> **Recommendation:** Make `enable_dns_rebinding_protection` conditional on `settings.is_prod` (or remove the override and default to `True` in production).

---

### ✅ Positive findings

| Area | Observation |
|------|-------------|
| **Passwords** | Argon2 with default parameters (via `argon2-cffi`) |
| **JWT algorithm** | RS256 only; RSA 2048 auto-generated and persisted to volume |
| **JWT TTL** | Access = 15 min, Refresh = 30 days, MCP access = 60 min |
| **Secrets in source** | No hardcoded passwords, API keys, or JWT secrets found |
| **Production validation** | `validate_production_ready()` blocks dev DB URLs, localhost CORS, mock email, missing Fernet key, etc. |
| **Token storage** | Refresh tokens and email tokens are SHA-256 hashed before storage |
| **OAuth validation** | MCP server checks `revoked_at`, `expires_at`, `audience`, and `scope` |
| **Email verification** | Disabled by default in dev (`AUTO_VERIFY_EMAILS_IN_DEV=false`); explicitly blocked in prod if enabled |
| **Password policy** | Minimum 10 characters enforced in use-case layer |
| **CSP & headers** | Already present (see §4) |

---

## 4. Fixes Applied

### Security headers middleware

**Status:** Already implemented and verified working.

The `SecurityHeadersMiddleware` in `backend/src/shared/middleware.py` was already active in `backend/src/main.py` (line 202). It sets:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` (comprehensive, Stripe/Sentry-aware)
- `Permissions-Policy` (camera=(), microphone=(), geolocation=(), payment=(self))
- Removes `Server` fingerprint header

**Verification:**

```bash
# Standalone middleware test (TestClient / Starlette)
cd backend && .venv/Scripts/python.exe -c "
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from src.shared.middleware import SecurityHeadersMiddleware

def homepage(request):
    return PlainTextResponse('ok')

app = Starlette(routes=[Route('/', homepage)])
app.add_middleware(SecurityHeadersMiddleware)

client = TestClient(app)
resp = client.get('/')
print('status:', resp.status_code)
for h in ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy', 'Content-Security-Policy']:
    print(f'{h}: {resp.headers.get(h)}')
"
```

**Output:**

```
status: 200
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://js.stripe.com; ...
```

> **Note:** The live Docker backend container (`cvs-backend`) was unavailable for `curl` verification at audit time due to an unrelated missing Python dependency (`jellyfish`) causing a startup crash. The TestClient test above is a faithful proxy because the middleware is a pure ASGI layer with no external dependencies.

**No code changes were required** — the middleware was already present and functional.

---

## 5. Recommendations for Future Audits

1. **Dependency scanning**
   - Install Trivy and run `trivy fs --severity HIGH,CRITICAL backend/` before every release.
   - Consider adding `pip-audit` or `safety` to the CI pipeline for Python dependency vulnerabilities.

2. **Rate-limit hardening**
   - Add limits to `/refresh`, `/verify`, and `/password-reset/confirm`.
   - Review MCP endpoints (`/mcp/sse`, `/mcp/messages/`) for per-client rate limiting.

3. **JWT defense in depth**
   - Consider making `exp` mandatory in `encode_jwt` (e.g. raise `ValueError` if missing) to prevent accidental non-expiring tokens.

4. **Session / refresh token hygiene**
   - Verify that refresh token rotation invalidates the old token atomically (review `RefreshTokenRepository.rotate` implementation).
   - Ensure refresh tokens are bound to `user_agent` + `ip_address` and rotation fails if they mismatch.

5. **OAuth AS hardening**
   - Audit `backend/src/mcp_server/interfaces/oauth_router.py` for PKCE validation, DPoP support, and client secret storage.
   - Ensure consent screen is explicit in production (not auto-consent).

6. **CSP tightening**
   - The current CSP allows `'unsafe-inline'` for scripts. As the frontend build pipeline matures, move to nonce-based or hash-based CSP.

7. **Penetration testing**
   - Run OWASP ZAP or Burp Suite against the running stack before public beta.

---

## 6. Summary

| Category | Result |
|----------|--------|
| Critical issues | 0 |
| Medium issues | 1 (missing rate limits on 3 auth endpoints) |
| Low issues | 2 (JWT `exp` defense-in-depth, DNS rebinding flag) |
| Fixes applied | 0 (security headers middleware already present and verified) |
| Trivy scan | Skipped (not installed) |
