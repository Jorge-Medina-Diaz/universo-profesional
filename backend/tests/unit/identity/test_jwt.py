"""Unit tests: JWT encode / decode and key management."""
from __future__ import annotations

import pytest
from jose.exceptions import JWTError
from src.shared.security import decode_jwt, encode_jwt, ensure_jwt_keys


class TestJwtEncodeDecode:
    def test_roundtrip(self) -> None:
        ensure_jwt_keys()
        claims = {
            "sub": "user-123",
            "email": "test@x.com",
            "scope": "user",
        }
        token = encode_jwt(claims)
        decoded = decode_jwt(token)
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "test@x.com"

    def test_tampered_token_fails(self) -> None:
        ensure_jwt_keys()
        token = encode_jwt({"sub": "user-123"})
        tampered = token[:-5] + "xxxxx"
        with pytest.raises(JWTError):
            decode_jwt(tampered)

    def test_audience_verification(self) -> None:
        ensure_jwt_keys()
        token = encode_jwt({"sub": "user-123", "aud": "cvs-saas-api"})
        decoded = decode_jwt(token, audience="cvs-saas-api")
        assert decoded["sub"] == "user-123"

        with pytest.raises(JWTError):
            decode_jwt(token, audience="wrong-aud")

    def test_issuer_verification(self) -> None:
        ensure_jwt_keys()
        token = encode_jwt({"sub": "user-123", "iss": "https://api.test"})
        decoded = decode_jwt(token, issuer="https://api.test")
        assert decoded["sub"] == "user-123"

        with pytest.raises(JWTError):
            decode_jwt(token, issuer="https://other.test")


class TestJwks:
    def test_jwks_has_rsa_key(self) -> None:
        from src.shared.security import get_jwks

        ensure_jwt_keys()
        jwks = get_jwks()
        assert "keys" in jwks
        assert len(jwks["keys"]) == 1
        key = jwks["keys"][0]
        assert key["kty"] == "RSA"
        assert key["alg"] == "RS256"
        assert "n" in key
        assert "e" in key
