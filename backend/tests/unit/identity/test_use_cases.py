"""Unit tests for identity use cases with mocked repositories (no DB)."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.identity.application.use_cases import (
    DeleteAccount,
    GetCurrentUser,
    Login,
    RefreshAccess,
    RegisterUser,
    RequestPasswordReset,
    ResetPassword,
    SetUserTier,
    VerifyEmail,
)
from src.identity.domain.user import User
from src.shared.uow import UnitOfWork
from src.shared.value_objects import Email


def _user(
    *,
    verified: bool = True,
    deleted: bool = False,
    password_hash: str | None = "hashed",
    tier: str = "free",
):
    return User(
        id=uuid4(),
        email=Email.parse("test@example.com"),
        password_hash=password_hash,
        display_name="Test",
        locale="es",
        email_verified_at=datetime.now(UTC) if verified else None,
        mfa_secret=None,
        mfa_enabled=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        deleted_at=datetime.now(UTC) if deleted else None,
        last_login_at=None,
        tier=tier,
    )


class TestRegisterUser:
    async def test_password_too_short(self):
        uc = RegisterUser(MagicMock(), MagicMock(), MagicMock())
        result = await uc.execute(
            email="a@b.com", password="short", display_name=None, locale="es", uow=MagicMock()
        )
        assert result.is_failure

    async def test_email_already_registered(self):
        users = MagicMock()
        users.get_by_email = AsyncMock(return_value=_user())
        uc = RegisterUser(users, MagicMock(), MagicMock())
        result = await uc.execute(
            email="test@example.com", password="password123", display_name=None, locale="es", uow=MagicMock()
        )
        assert result.is_failure

    async def test_success(self):
        users = MagicMock()
        users.get_by_email = AsyncMock(return_value=None)
        users.save = AsyncMock()
        tokens = MagicMock()
        tokens.create = AsyncMock()
        emailer = MagicMock()
        emailer.send_verification = AsyncMock()
        uc = RegisterUser(users, tokens, emailer)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_events = MagicMock()
        result = await uc.execute(
            email="new@example.com", password="password123", display_name=None, locale="es", uow=uow
        )
        assert result.is_success
        users.save.assert_awaited_once()


class TestVerifyEmail:
    async def test_invalid_token(self):
        tokens = MagicMock()
        tokens.consume = AsyncMock(return_value=None)
        uc = VerifyEmail(MagicMock(), tokens)
        result = await uc.execute(token="bad", uow=MagicMock())
        assert result.is_failure

    async def test_success(self):
        user = _user(verified=False)
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=user)
        users.save = AsyncMock()
        tokens = MagicMock()
        tokens.consume = AsyncMock(return_value=user.id)
        uc = VerifyEmail(users, tokens)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_events = MagicMock()
        result = await uc.execute(token="tok", uow=uow)
        assert result.is_success
        assert user.is_verified


class TestLogin:
    async def test_invalid_credentials(self):
        users = MagicMock()
        users.get_by_email = AsyncMock(return_value=None)
        uc = Login(users, MagicMock())
        result = await uc.execute(
            email="a@b.com", password="pw", user_agent=None, ip_address=None, uow=MagicMock()
        )
        assert result.is_failure

    async def test_not_verified(self):

        from src.shared.security import hash_password

        user = _user(verified=False, password_hash=hash_password("password123"))
        users = MagicMock()
        users.get_by_email = AsyncMock(return_value=user)
        uc = Login(users, MagicMock())
        result = await uc.execute(
            email="test@example.com", password="password123", user_agent=None, ip_address=None, uow=MagicMock()
        )
        assert result.is_failure

    async def test_success(self):
        from src.shared.security import hash_password

        user = _user(verified=True, password_hash=hash_password("password123"))
        users = MagicMock()
        users.get_by_email = AsyncMock(return_value=user)
        users.save = AsyncMock()
        refresh = MagicMock()
        refresh.store = AsyncMock()
        uc = Login(users, refresh)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_events = MagicMock()
        result = await uc.execute(
            email="test@example.com",
            password="password123",
            user_agent="agent",
            ip_address="127.0.0.1",
            uow=uow,
        )
        assert result.is_success
        assert result.value.access_token
        assert result.value.refresh_token


class TestRefreshAccess:
    async def test_invalid_token(self):
        tokens = MagicMock()
        tokens.rotate = AsyncMock(return_value=None)
        uc = RefreshAccess(MagicMock(), tokens)
        result = await uc.execute(refresh_token="bad", user_agent=None, ip_address=None)
        assert result.is_failure

    async def test_success(self):
        user = _user()
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=user)
        tokens = MagicMock()
        tokens.rotate = AsyncMock(return_value=user.id)
        uc = RefreshAccess(users, tokens)
        result = await uc.execute(refresh_token="tok", user_agent=None, ip_address=None)
        assert result.is_success
        assert result.value.access_token


class TestRequestPasswordReset:
    async def test_invalid_email_returns_ok(self):
        uc = RequestPasswordReset(MagicMock(), MagicMock(), MagicMock())
        result = await uc.execute(email="not-an-email", uow=MagicMock())
        assert result.is_success

    async def test_unknown_email_returns_ok(self):
        users = MagicMock()
        users.get_by_email = AsyncMock(return_value=None)
        uc = RequestPasswordReset(users, MagicMock(), MagicMock())
        result = await uc.execute(email="unknown@example.com", uow=MagicMock())
        assert result.is_success

    async def test_known_user_sends_email(self):
        user = _user()
        users = MagicMock()
        users.get_by_email = AsyncMock(return_value=user)
        tokens = MagicMock()
        tokens.create = AsyncMock()
        emailer = MagicMock()
        emailer.send_password_reset = AsyncMock()
        uc = RequestPasswordReset(users, tokens, emailer)
        result = await uc.execute(email="test@example.com", uow=MagicMock())
        assert result.is_success
        emailer.send_password_reset.assert_awaited_once()


class TestResetPassword:
    async def test_password_too_short(self):
        uc = ResetPassword(MagicMock(), MagicMock(), MagicMock())
        result = await uc.execute(token="tok", new_password="short", uow=MagicMock())
        assert result.is_failure

    async def test_invalid_token(self):
        tokens = MagicMock()
        tokens.consume = AsyncMock(return_value=None)
        uc = ResetPassword(MagicMock(), tokens, MagicMock())
        result = await uc.execute(token="tok", new_password="password123", uow=MagicMock())
        assert result.is_failure

    async def test_success(self):
        user = _user(verified=False)
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=user)
        users.save = AsyncMock()
        tokens = MagicMock()
        tokens.consume = AsyncMock(return_value=user.id)
        refresh = MagicMock()
        refresh.revoke_all_for_user = AsyncMock()
        uc = ResetPassword(users, tokens, refresh)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_events = MagicMock()
        result = await uc.execute(token="tok", new_password="password123", uow=uow)
        assert result.is_success
        assert user.is_verified
        refresh.revoke_all_for_user.assert_awaited_once()


class TestDeleteAccount:
    async def test_user_not_found(self):
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=None)
        uc = DeleteAccount(users, MagicMock())
        result = await uc.execute(user_id=str(uuid4()), uow=MagicMock())
        assert result.is_failure

    async def test_success(self):
        user = _user()
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=user)
        users.save = AsyncMock()
        refresh = MagicMock()
        refresh.revoke_all_for_user = AsyncMock()
        uc = DeleteAccount(users, refresh)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_events = MagicMock()
        result = await uc.execute(user_id=str(user.id), uow=uow)
        assert result.is_success
        assert user.is_deleted


class TestGetCurrentUser:
    async def test_not_found(self):
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=None)
        uc = GetCurrentUser(users)
        result = await uc.execute(user_id=str(uuid4()))
        assert result.is_failure

    async def test_deleted(self):
        user = _user(deleted=True)
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=user)
        uc = GetCurrentUser(users)
        result = await uc.execute(user_id=str(user.id))
        assert result.is_failure

    async def test_success(self):
        user = _user()
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=user)
        uc = GetCurrentUser(users)
        result = await uc.execute(user_id=str(user.id))
        assert result.is_success
        assert result.value.email == "test@example.com"


class TestSetUserTier:
    async def test_invalid_tier(self):
        users = MagicMock()
        uc = SetUserTier(users)
        result = await uc.execute(user_id=str(uuid4()), tier="enterprise", uow=MagicMock())
        assert result.is_failure

    async def test_user_not_found(self):
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=None)
        uc = SetUserTier(users)
        result = await uc.execute(user_id=str(uuid4()), tier="pro", uow=MagicMock())
        assert result.is_failure

    async def test_success(self):
        user = _user()
        users = MagicMock()
        users.get_by_id = AsyncMock(return_value=user)
        users.save = AsyncMock()
        uc = SetUserTier(users)
        uow = MagicMock(spec=UnitOfWork)
        uow.add_events = MagicMock()
        result = await uc.execute(user_id=str(user.id), tier="pro", uow=uow)
        assert result.is_success
        assert user.tier == "pro"
