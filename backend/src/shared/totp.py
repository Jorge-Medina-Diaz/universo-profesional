"""RFC 6238 TOTP (and RFC 4226 HOTP) — dependency-free.

Implemented in-house rather than pulling `pyotp` so MFA stays verifiable
without a new wheel in the image. Compatible with Google Authenticator, Authy,
1Password, etc. (SHA1, 6 digits, 30s period — the de-facto authenticator
defaults).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

_DEFAULT_PERIOD = 30
_DEFAULT_DIGITS = 6


def generate_secret(num_bytes: int = 20) -> str:
    """A fresh base32 secret (no padding) — 20 bytes = 160 bits, the RFC 4226
    recommended length."""
    return base64.b32encode(secrets.token_bytes(num_bytes)).decode("ascii").rstrip("=")


def _b32decode(secret: str) -> bytes:
    # Authenticator secrets are stored unpadded + may be lowercase.
    s = secret.strip().replace(" ", "").upper()
    pad = "=" * ((8 - len(s) % 8) % 8)
    return base64.b32decode(s + pad)


def _hotp(secret: str, counter: int, digits: int = _DEFAULT_DIGITS) -> str:
    key = _b32decode(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def totp_now(
    secret: str,
    *,
    period: int = _DEFAULT_PERIOD,
    digits: int = _DEFAULT_DIGITS,
    at: float | None = None,
) -> str:
    counter = int((time.time() if at is None else at) // period)
    return _hotp(secret, counter, digits)


def verify(
    secret: str,
    code: str,
    *,
    period: int = _DEFAULT_PERIOD,
    digits: int = _DEFAULT_DIGITS,
    window: int = 1,
    at: float | None = None,
) -> bool:
    """Constant-time verify with a ±`window` step tolerance (clock drift)."""
    if not secret or not code:
        return False
    candidate = code.strip().replace(" ", "")
    if not candidate.isdigit() or len(candidate) != digits:
        return False
    now = time.time() if at is None else at
    counter = int(now // period)
    for step in range(-window, window + 1):
        probe = counter + step
        # A negative counter is unrepresentable as the unsigned 64-bit value RFC
        # 4226 defines, and `struct.pack(">Q", -1)` raises instead of returning
        # False — so verifying within one step of the Unix epoch crashed rather
        # than rejecting. Unreachable with a real clock, but this is the MFA
        # path: it should never raise on input it can simply refuse.
        if probe < 0:
            continue
        if hmac.compare_digest(_hotp(secret, probe, digits), candidate):
            return True
    return False


def provisioning_uri(
    secret: str, *, account_name: str, issuer: str = "Universo Profesional"
) -> str:
    """`otpauth://` URI for QR enrolment in authenticator apps."""
    label = quote(f"{issuer}:{account_name}")
    query = (
        f"secret={secret}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={_DEFAULT_DIGITS}&period={_DEFAULT_PERIOD}"
    )
    return f"otpauth://totp/{label}?{query}"
