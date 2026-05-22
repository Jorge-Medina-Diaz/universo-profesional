# Secrets rotation

| Secret                       | Rotation cadence | Procedure                                  |
|------------------------------|------------------|--------------------------------------------|
| `TOKEN_ENCRYPTION_KEY`       | yearly           | Multi-key rotation (see below)             |
| JWT signing keys             | yearly           | Generate new pair, deploy, wait, kill old  |
| `ANTHROPIC_API_KEY`          | quarterly        | Generate new, swap, revoke old             |
| `STRIPE_API_KEY` (live)      | only on leak     | Rotate from Stripe dashboard               |
| `STRIPE_WEBHOOK_SECRET`      | only on leak     | Rotate, update Fly secret, replay events   |
| `BREVO_API_KEY`              | quarterly        | Generate new, swap, revoke old             |
| `POSTGRES_PASSWORD`          | yearly           | Fly Postgres rotate password               |
| DB user passwords            | yearly           | Update connection string secret            |

## TOKEN_ENCRYPTION_KEY (Fernet) — multi-key rotation

The current Fernet code uses a single key. For zero-downtime rotation we
need `MultiFernet([new_key, old_key])` so old tokens still decrypt while
new writes use the new key. Plan:

1. Add `TOKEN_ENCRYPTION_KEY_NEXT` env var with the freshly-generated key.
2. Bump the code to `MultiFernet([next, current])` (new key first).
3. Deploy. All new encryptions use `next`; old ciphertexts still decrypt
   with `current`.
4. Run a one-shot migration that re-encrypts all stored OAuth tokens
   (touch-on-decrypt is the cheapest approach — we already log access).
5. After 7 days, swap: `current = next`, drop `next`. Deploy.

## JWT keys

```bash
# 1. Generate new key pair.
flyctl ssh console --app cvs-saas-backend
openssl genrsa -out /app/var/keys/jwt_private.pem.new 2048
openssl rsa -in /app/var/keys/jwt_private.pem.new -pubout -out /app/var/keys/jwt_public.pem.new

# 2. Update `security.py` to accept BOTH old + new public keys for verification.
#    (Single-key today; add multi-key support before the first rotation.)

# 3. Swap files and restart.
mv /app/var/keys/jwt_private.pem /app/var/keys/jwt_private.pem.old
mv /app/var/keys/jwt_private.pem.new /app/var/keys/jwt_private.pem
# Same for the public key.

# 4. Wait > jwt_access_ttl_minutes (15 min) so all old tokens expire.

# 5. Remove the old public key from the verifier list and the .old files.
```

## API keys (Anthropic, Brevo, etc.)

```bash
# 1. Generate the new key in the provider dashboard.
# 2. Update Fly:
flyctl secrets set --app cvs-saas-backend ANTHROPIC_API_KEY='sk-ant-...'
# 3. Backend reloads. Verify no errors in Sentry.
# 4. Revoke the OLD key from the provider dashboard.
```

## Stripe webhook secret

```bash
# In Stripe dashboard → Developers → Webhooks → Roll signing secret.
flyctl secrets set --app cvs-saas-backend STRIPE_WEBHOOK_SECRET='whsec_NEW'
# Replay any failed deliveries from the Stripe dashboard.
```

## Audit log

Keep a private record of rotations in your password manager or a private
notes repo:

```
2026-05-20  ANTHROPIC_API_KEY  rotated, old=sk-ant-abc..., new=sk-ant-xyz...
2026-05-20  TOKEN_ENCRYPTION_KEY  scheduled for 2026-09-01
```
