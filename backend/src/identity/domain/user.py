"""User aggregate root."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from src.shared.events import DomainEvent
from src.shared.value_objects import Email


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    event_type: ClassVar[str] = "identity.user_registered"
    email: str = ""
    user_id_str: str = ""


@dataclass(frozen=True, kw_only=True)
class EmailVerified(DomainEvent):
    event_type: ClassVar[str] = "identity.email_verified"


@dataclass(frozen=True, kw_only=True)
class PasswordChanged(DomainEvent):
    event_type: ClassVar[str] = "identity.password_changed"


@dataclass(frozen=True, kw_only=True)
class AccountSoftDeleted(DomainEvent):
    event_type: ClassVar[str] = "identity.account_soft_deleted"


@dataclass(frozen=True, kw_only=True)
class TierChanged(DomainEvent):
    event_type: ClassVar[str] = "identity.tier_changed"
    previous_tier: str = "free"
    new_tier: str = "free"


@dataclass
class User:
    """User aggregate root.

    Identity-specific invariants live here:
      * Email is required at construction.
      * Either a password_hash or external OAuth identity is required (enforced
        at use case layer, not here, since OAuth is not in MVP).
      * Email verification is required before login (use case enforces).
    """

    id: UUID
    email: Email
    password_hash: str | None
    display_name: str | None
    locale: str
    email_verified_at: datetime | None
    mfa_secret: str | None
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    last_login_at: datetime | None
    tier: str = "free"
    tier_updated_at: datetime | None = None
    _events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    @classmethod
    def register(
        cls,
        *,
        email: Email,
        password_hash: str | None,
        display_name: str | None,
        locale: str,
        now: datetime,
    ) -> User:
        user_id = uuid4()
        user = cls(
            id=user_id,
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            locale=locale,
            email_verified_at=None,
            mfa_secret=None,
            mfa_enabled=False,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            last_login_at=None,
        )
        user._events.append(
            UserRegistered(
                user_id=user_id,
                email=str(email),
                user_id_str=str(user_id),
            )
        )
        return user

    @property
    def is_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def mark_verified(self, *, now: datetime) -> None:
        if self.is_verified:
            return
        self.email_verified_at = now
        self.updated_at = now
        self._events.append(EmailVerified(user_id=self.id))

    def change_password(self, new_hash: str, *, now: datetime) -> None:
        self.password_hash = new_hash
        self.updated_at = now
        self._events.append(PasswordChanged(user_id=self.id))

    def record_login(self, *, now: datetime) -> None:
        self.last_login_at = now
        self.updated_at = now

    def soft_delete(self, *, now: datetime) -> None:
        if self.is_deleted:
            return
        self.deleted_at = now
        self.updated_at = now
        self._events.append(AccountSoftDeleted(user_id=self.id))

    @property
    def is_pro(self) -> bool:
        return self.tier == "pro"

    @property
    def is_paying(self) -> bool:
        """Canonical paid-entitlement gate. Covers every paid tier so a
        `premium` subscriber is not denied Pro features (the bug where
        entitlement checks used `is_pro` and locked premium users out)."""
        return self.tier in PAID_TIERS

    def set_tier(self, tier: str, *, now: datetime) -> None:
        if tier not in VALID_TIERS:
            raise ValueError(f"Unsupported tier: {tier}")
        if self.tier == tier:
            return
        previous = self.tier
        self.tier = tier
        self.tier_updated_at = now
        self.updated_at = now
        self._events.append(
            TierChanged(user_id=self.id, previous_tier=previous, new_tier=tier)
        )

    def pop_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events
