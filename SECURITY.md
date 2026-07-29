# Security Policy

## Status

This project is **not deployed**. There is no production instance and no user
data at risk. It is published as a portfolio piece.

## Reporting

If you find a vulnerability in the code, please open a
[GitHub security advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
rather than a public issue.

## Known and documented

These are stated plainly in the README's *Honest status* section and are not
considered undisclosed vulnerabilities:

- **RLS does not cover the Apache AGE label tables.** Tenant isolation for graph
  reads is a `user_id` property filter inside Cypher, plus label and edge
  allowlists enforced at the text2cypher validator and the edge-write
  chokepoint. Defense in depth, but not the database enforcing it.
- **Default providers are mocks.** A fresh `docker compose up` runs with no real
  credentials by design.
- **`TOKEN_ENCRYPTION_KEY` has a deterministic dev fallback** so the stack boots
  offline. It hard-fails when `ENV=production`.

## What is enforced

- Postgres RLS with `FORCE`, app running as a non-superuser role, GUCs re-armed
  on every transaction — see [docs/SECURITY_RLS_STATUS.md](docs/SECURITY_RLS_STATUS.md).
- RS256 JWTs, TOTP MFA, Fernet-encrypted OAuth tokens / MFA secrets / BYOK keys.
- OAuth 2.1 + PKCE + Dynamic Client Registration for the MCP server, 21 scopes.
- CI gates on `ruff` (including bandit rules) and Trivy filesystem and image scans.
