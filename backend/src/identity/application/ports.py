"""Application-layer ports (interfaces). Implementations live in infrastructure/."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.identity.domain.user import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def save(self, user: User) -> None: ...
    async def hard_delete_expired(self, before: datetime) -> int: ...
    async def count_activation_signals(self, user_id: UUID) -> dict[str, int]:
        """Counts that define activation: experiences, skills, CV documents."""
        ...


class EmailTokenRepository(Protocol):
    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        purpose: str,
        expires_at: datetime,
    ) -> None: ...
    async def consume(
        self,
        *,
        token_hash: str,
        purpose: str,
        now: datetime,
    ) -> UUID | None:
        """Return user_id if token valid + unused + not expired, then mark consumed."""
        ...


class RefreshTokenRepository(Protocol):
    async def store(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> None: ...
    async def rotate(
        self,
        *,
        old_token_hash: str,
        new_token_hash: str,
        new_expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> UUID | None: ...
    async def revoke(self, token_hash: str) -> None: ...
    async def revoke_all_for_user(self, user_id: UUID) -> None: ...


class EmailSendError(Exception):
    """Raised when an email transport fails permanently or transiently.

    Transient errors (network, 5xx from provider) should be retryable; the
    `tasks.send_email` wrapper applies tenacity backoff. Permanent errors
    (invalid recipient, suspended account) should NOT be retried — providers
    typically respond with 4xx for these and we let the failure bubble up.
    """


class EmailSender(Protocol):
    async def send(
        self,
        *,
        to: str,
        subject: str,
        body_text: str,
        body_html: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Send a single email. Raise `EmailSendError` on failure."""
        ...

    # Legacy helpers — implemented in terms of `send` by all real senders.
    async def send_verification(self, *, to: str, link: str, locale: str) -> None: ...
    async def send_password_reset(self, *, to: str, link: str, locale: str) -> None: ...


class UserDataExporter(Protocol):
    async def export_all(self, user_id: UUID) -> dict[str, Any]:
        """Return a JSON-serializable dump of every row owned by the user."""
        ...
