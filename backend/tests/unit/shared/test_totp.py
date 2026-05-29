"""Unit tests for the dependency-free TOTP implementation (RFC 6238 vectors)."""
from __future__ import annotations

import base64

from src.shared import totp

# RFC 6238 uses the ASCII secret "12345678901234567890" (SHA1).
_SECRET = base64.b32encode(b"12345678901234567890").decode().rstrip("=")


class TestTotp:
    def test_rfc6238_vectors(self):
        # 8-digit RFC values truncated to the 6 low digits.
        assert totp.totp_now(_SECRET, at=59) == "287082"
        assert totp.totp_now(_SECRET, at=1111111109) == "081804"
        assert totp.totp_now(_SECRET, at=1111111111) == "050471"

    def test_verify_accepts_current_code(self):
        code = totp.totp_now(_SECRET, at=59)
        assert totp.verify(_SECRET, code, at=59)

    def test_verify_drift_window(self):
        code = totp.totp_now(_SECRET, at=59)
        # one step earlier/later still accepted (±30s tolerance)
        assert totp.verify(_SECRET, code, at=59 + 30)
        assert totp.verify(_SECRET, code, at=59 - 30)
        # two steps away rejected
        assert not totp.verify(_SECRET, code, at=59 + 90)

    def test_verify_rejects_garbage(self):
        assert not totp.verify(_SECRET, "000000", at=59)
        assert not totp.verify(_SECRET, "abcdef", at=59)
        assert not totp.verify(_SECRET, "", at=59)
        assert not totp.verify(_SECRET, "12345", at=59)  # wrong length

    def test_generate_secret_is_valid_base32(self):
        s = totp.generate_secret()
        assert len(s) >= 32
        # decodes without error (padding re-added internally by _b32decode)
        assert totp.totp_now(s).isdigit()

    def test_provisioning_uri_shape(self):
        uri = totp.provisioning_uri("ABCDEF", account_name="ana@example.com")
        assert uri.startswith("otpauth://totp/")
        assert "secret=ABCDEF" in uri
        assert "issuer=" in uri and "period=30" in uri
