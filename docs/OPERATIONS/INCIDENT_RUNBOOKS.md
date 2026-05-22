# Incident runbooks

One section per scenario. Each runbook follows: **Symptom → Triage → Fix → Postmortem template**.

## LLM provider outage

**Symptom**: chat requests return 500; Sentry shows `anthropic.AnthropicError`
or persistent 5xx from `api.anthropic.com`.

**Triage**:
1. Check Anthropic status page.
2. `flyctl logs --app cvs-saas-backend` — confirm the error is upstream.

**Fix (graceful degrade)**: switch `AGENTS_PROVIDER` to `openai` if you
have a key configured:

```bash
flyctl secrets set --app cvs-saas-backend AGENTS_PROVIDER=openai
```

Backend reloads automatically. Chat continues with OpenAI; users won't
notice (slight quality difference).

If neither provider is available, set `AGENTS_PROVIDER=mock` to keep the
app reachable (forms, billing, integrations all keep working — chat
returns an explicit "no LLM configured" message).

## Database down

**Symptom**: `/readyz` returns 503; users see "Sin conexión al backend".

**Triage**:
1. `flyctl status --app cvs-saas-db`
2. `flyctl logs --app cvs-saas-db`

**Fix**: restart the DB machine if Fly didn't already (`flyctl machine restart`).
If the DB is gone, see `BACKUP_RESTORE.md` to restore from the latest dump.

## Stripe webhook backlog

**Symptom**: users upgrade in Stripe but the local subscription stays at "free".

**Triage**: Stripe dashboard → Developers → Webhooks → check delivery
attempts and the last response from `/api/v1/billing/webhook`.

**Common causes**:
- `STRIPE_WEBHOOK_SECRET` mismatch (rotated and forgot to update Fly).
- Backend was down during the delivery window.

**Fix**:
1. Update the secret in Fly:
   ```bash
   flyctl secrets set --app cvs-saas-backend STRIPE_WEBHOOK_SECRET='whsec_NEW'
   ```
2. Replay the missing events from the Stripe dashboard (Resend button per event).
3. Confirm the subscription row got updated:
   ```sql
   SELECT user_id, plan, status, stripe_customer_id, updated_at
   FROM subscriptions
   ORDER BY updated_at DESC LIMIT 20;
   ```

## OAuth token compromise (suspicion)

**Symptom**: Sentry shows hundreds of `Unauthorized` 401s for one user_id
within minutes (token-reuse detection fired).

**Action**:
1. Revoke all refresh tokens for that user:
   ```sql
   UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = '<uid>';
   ```
2. Force them to log in again. Email them out-of-band if you can.
3. Consider rotating the JWT signing keys (see `SECRETS_ROTATION.md`).

## Email deliverability tanked

**Symptom**: users report not receiving the verification email; Brevo
dashboard shows bounces or spam complaints.

**Fix checklist**:
- DKIM / SPF / DMARC records on the sending domain.
- Check Brevo's "Senders & IPs" → reputation.
- If reputation is shot, switch to Postmark temporarily by setting
  `EMAIL_PROVIDER=postmark` + `POSTMARK_SERVER_TOKEN`.

## Memory leak / OOM

**Symptom**: Fly machine restarts every ~30 min with `OOM killed`.

**Fix**:
1. Bump memory: `flyctl scale memory 2048 --app cvs-saas-backend`.
2. Inspect Sentry for unusual exception patterns (often a runaway loop in
   a tool / streaming response).

## Postmortem template

After resolving an incident, drop a markdown file in `docs/postmortems/`:

```markdown
# YYYY-MM-DD — Short title

## Impact
- Users affected, duration, what they couldn't do.

## Timeline
- 10:03 UTC — first error in Sentry
- 10:07 UTC — alert fired
- 10:18 UTC — fix deployed
- 10:24 UTC — confirmed recovery

## Root cause

## Fix

## Prevention
- What we'll change to make this not happen again.
```
