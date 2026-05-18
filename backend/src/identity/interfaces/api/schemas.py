"""Pydantic schemas for Identity endpoints."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)
    display_name: str | None = Field(default=None, max_length=120)
    locale: str = Field(default="es-ES", max_length=10)


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


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=256)


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    locale: str
    email_verified: bool
    mfa_enabled: bool
    created_at: str


class GenericOkResponse(BaseModel):
    ok: bool = True
