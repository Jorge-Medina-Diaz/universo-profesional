"""Pydantic schemas for Identity endpoints."""
from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

# --- Password policy ---------------------------------------------------------
# Enforced on register + password reset confirm. We deliberately keep the
# minimum requirements modest (length + 1 digit + 1 uppercase + not a top-N
# common password) — NIST 800-63B advises against complex policies because
# they push users towards predictable patterns. Length + dictionary check
# beat character classes in practice.

_PWD_MIN_LENGTH = 10
_PWD_MAX_LENGTH = 256
_PWD_DIGIT_RE = re.compile(r"\d")
_PWD_UPPER_RE = re.compile(r"[A-Z]")


def _validate_password(pwd: str) -> str:
    if len(pwd) < _PWD_MIN_LENGTH:
        raise ValueError(f"password must be at least {_PWD_MIN_LENGTH} characters")
    if len(pwd) > _PWD_MAX_LENGTH:
        raise ValueError(f"password must be at most {_PWD_MAX_LENGTH} characters")
    if not _PWD_DIGIT_RE.search(pwd):
        raise ValueError("password must contain at least one digit")
    if not _PWD_UPPER_RE.search(pwd):
        raise ValueError("password must contain at least one uppercase letter")
    # Local import keeps the common-password list out of the module import
    # graph during static analysis / IDE indexing.
    from src.shared.common_passwords import is_common_password

    if is_common_password(pwd):
        raise ValueError("password is too common; pick something less guessable")
    return pwd


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_PWD_MIN_LENGTH, max_length=_PWD_MAX_LENGTH)
    display_name: str | None = Field(default=None, max_length=120)
    locale: str = Field(default="es-ES", max_length=10)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    verification_link: str | None = None  # only in dev / test


class VerifyEmailRequest(BaseModel):
    token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    # Set when the account has MFA enabled: the client must call /auth/mfa with
    # mfa_token + the TOTP code to obtain real tokens. access/refresh are empty
    # in that case.
    mfa_required: bool = False
    mfa_token: str | None = None


class MfaLoginRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=10)


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MfaStatusResponse(BaseModel):
    mfa_enabled: bool


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=_PWD_MIN_LENGTH, max_length=_PWD_MAX_LENGTH)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return _validate_password(v)


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    locale: str
    email_verified: bool
    mfa_enabled: bool
    created_at: str
    tier: str = "free"
    tier_updated_at: str | None = None


class SetTierRequest(BaseModel):
    tier: str = Field(pattern="^(free|pro)$")


class NotificationPrefsResponse(BaseModel):
    email_reminders: bool


class NotificationPrefsRequest(BaseModel):
    email_reminders: bool


class GenericOkResponse(BaseModel):
    ok: bool = True
