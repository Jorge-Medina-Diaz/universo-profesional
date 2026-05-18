"""Cryptographic primitives: password hashing, JWT keys, token hashing."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from .config import get_settings

_password_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _password_hasher.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False


def password_needs_rehash(hashed: str) -> bool:
    return _password_hasher.check_needs_rehash(hashed)


def generate_token(byte_length: int = 32) -> str:
    """URL-safe random token for email verification, password reset, share, etc."""
    return secrets.token_urlsafe(byte_length)


def hash_token(token: str) -> str:
    """SHA-256 hex digest. Tokens are stored hashed; we compare digests in lookups."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --- JWT key management -----------------------------------------------------

_private_pem: bytes | None = None
_public_pem: bytes | None = None


def ensure_jwt_keys() -> None:
    """Generate RSA keypair on first run; persist to volume so they survive restarts."""
    global _private_pem, _public_pem
    settings = get_settings()
    priv_path = settings.jwt_private_key_path
    pub_path = settings.jwt_public_key_path

    if priv_path.exists() and pub_path.exists():
        _private_pem = priv_path.read_bytes()
        _public_pem = pub_path.read_bytes()
        return

    priv_path.parent.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    _public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_path.write_bytes(_private_pem)
    pub_path.write_bytes(_public_pem)


def get_private_key() -> bytes:
    if _private_pem is None:
        ensure_jwt_keys()
    assert _private_pem is not None
    return _private_pem


def get_public_key() -> bytes:
    if _public_pem is None:
        ensure_jwt_keys()
    assert _public_pem is not None
    return _public_pem


def encode_jwt(claims: dict[str, Any]) -> str:
    settings = get_settings()
    return jwt.encode(claims, get_private_key(), algorithm=settings.jwt_algorithm)


def decode_jwt(
    token: str,
    *,
    audience: str | None = None,
    issuer: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    options: dict[str, Any] = {"verify_aud": audience is not None, "verify_iss": issuer is not None}
    return jwt.decode(
        token,
        get_public_key(),
        algorithms=[settings.jwt_algorithm],
        audience=audience,
        issuer=issuer,
        options=options,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_in(*, minutes: int = 0, hours: int = 0, days: int = 0) -> datetime:
    return utc_now() + timedelta(minutes=minutes, hours=hours, days=days)


def get_jwks() -> dict[str, Any]:
    """Public key in JWKS format for /.well-known/jwks.json."""
    from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    pem = get_public_key()
    public_key = load_pem_public_key(pem)
    assert isinstance(public_key, _rsa.RSAPublicKey)
    numbers = public_key.public_numbers()

    def _int_to_b64url(n: int) -> str:
        import base64

        byte_length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_length, "big")).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": get_settings().jwt_algorithm,
                "kid": "cvs-saas-1",
                "n": _int_to_b64url(numbers.n),
                "e": _int_to_b64url(numbers.e),
            }
        ]
    }
