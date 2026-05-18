"""Symmetric encryption for third-party OAuth tokens.

Tokens for external providers (GitHub, LinkedIn) are highly sensitive and
must never sit in plaintext at rest. We use Fernet (AES-128-CBC + HMAC-SHA-256)
with a master key from the `TOKEN_ENCRYPTION_KEY` env var.

Key rotation strategy (out of scope for sprint 2):
  - Maintain a `MultiFernet([new_key, old_key])` so old tokens still decrypt
    while new ones use the new key.
  - Re-encrypt on access ("touch on use") to migrate gradually.
"""
from __future__ import annotations

import base64
import os
from functools import lru_cache

from cryptography.fernet import Fernet


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    key = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not key:
        # Dev fallback: derive a stable key from a known constant so restarts
        # don't invalidate previously-stored tokens. NOT acceptable in prod.
        seed = b"cvs-saas-dev-token-encryption-key-do-not-use-in-prod-aaaaa"[:32]
        key = base64.urlsafe_b64encode(seed).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(value: str) -> bytes:
    return _get_fernet().encrypt(value.encode("utf-8"))


def decrypt(token: bytes | memoryview) -> str:
    if isinstance(token, memoryview):
        token = bytes(token)
    return _get_fernet().decrypt(token).decode("utf-8")


def generate_key() -> str:
    """Helper to print a fresh key — useful for ops."""
    return Fernet.generate_key().decode()
