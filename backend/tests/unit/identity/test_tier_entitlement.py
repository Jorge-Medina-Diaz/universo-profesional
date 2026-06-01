"""Regression tests for tier entitlement (R1).

The bug: users.tier only accepted ('free','pro') — domain AND a DB CHECK — so a
Stripe-driven 'premium' subscriber could not be stored, and every is_pro / !=
'pro' gate locked them out. Fix: premium is a valid, paying tier; entitlement
gates use is_paying.
"""
from __future__ import annotations

import datetime as dt

import pytest

from src.identity.domain.user import PAID_TIERS, VALID_TIERS, User
from src.shared.value_objects import Email

_NOW = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)


def _user(tier: str) -> User:
    u = User.register(
        email=Email("a@b.com"),
        password_hash="x",
        display_name=None,
        locale="es-ES",
        now=_NOW,
    )
    u.tier = tier
    return u


def test_constants() -> None:
    assert PAID_TIERS == frozenset({"pro", "premium"})
    assert VALID_TIERS == frozenset({"free", "pro", "premium"})


@pytest.mark.parametrize(
    "tier,paying", [("free", False), ("pro", True), ("premium", True)]
)
def test_is_paying_covers_premium(tier: str, paying: bool) -> None:
    assert _user(tier).is_paying is paying


def test_set_tier_accepts_premium() -> None:
    u = _user("free")
    u.set_tier("premium", now=_NOW)
    assert u.tier == "premium"
    assert u.is_paying is True


def test_set_tier_rejects_unknown() -> None:
    u = _user("free")
    with pytest.raises(ValueError):
        u.set_tier("platinum", now=_NOW)


def test_is_pro_strict_but_is_paying_inclusive() -> None:
    prem = _user("premium")
    assert prem.is_pro is False
    assert prem.is_paying is True
