"""Domain error hierarchy.

Errors are part of the domain model — they signal business rule violations.
Each error has a stable `code` consumed by the HTTP layer to produce RFC 7807
Problem Details responses.
"""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for every business-rule violation."""

    code: str = "domain.error"
    http_status: int = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_problem(self) -> dict[str, Any]:
        return {
            "type": f"https://errors.cvs-saas.local/{self.code}",
            "title": self.message,
            "status": self.http_status,
            "code": self.code,
            "details": self.details,
        }


class ValidationError(DomainError):
    code = "validation.failed"
    http_status = 422


class NotFoundError(DomainError):
    code = "resource.not_found"
    http_status = 404


class ConflictError(DomainError):
    code = "resource.conflict"
    http_status = 409


class UnauthorizedError(DomainError):
    code = "auth.unauthorized"
    http_status = 401


class ForbiddenError(DomainError):
    code = "auth.forbidden"
    http_status = 403


class QuotaExceededError(DomainError):
    code = "billing.quota_exceeded"
    http_status = 402


class IntegrationError(DomainError):
    """External service failed (LLM, Stripe, Affinda, etc.)."""

    code = "integration.failed"
    http_status = 502


class RateLimitedError(DomainError):
    code = "rate_limit.exceeded"
    http_status = 429
