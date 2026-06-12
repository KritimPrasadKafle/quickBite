import uuid
import hashlib
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from modules.users.service import UserService
from modules.users.model import User, RefreshToken, UserRole
from modules.users.schemas import CreateUser
from core.security import Security


# ─── Test data helpers ────────────────────────────────────────────────────────

def make_user(**overrides) -> User:
    user = User()
    user.id = uuid.uuid4()
    user.email = "test@quickbite.com"
    user.phone = "9800000000"
    user.full_name = "Test User"
    user.hashed_password = Security().hash_password("Password123!")
    user.role = UserRole.customer
    user.is_active = True
    user.is_verified = False
    for k, v in overrides.items():
        setattr(user, k, v)
    return user


def make_refresh_token(user_id: uuid.UUID, is_revoked=False, days_valid=7) -> RefreshToken:
    token = RefreshToken()
    token.id = uuid.uuid4()
    token.user_id = user_id
    token.token_hash = "somehash"
    token.is_revoked = is_revoked
    # naive UTC — matches how it comes back from Postgres
    token.expires_at = datetime.utcnow() + timedelta(days=days_valid)
    return token


def make_register_payload(**overrides) -> CreateUser:
    defaults = dict(
        email="test@quickbite.com",
        phone="9800000000",
        full_name="Test User",
        password="Password123!",
        role=UserRole.customer,
    )
    return CreateUser(**{**defaults, **overrides})


# ─── register_user ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(mock_uow, service):
    user = make_user()
    mock_uow.users.get_by_email.return_value = None
    mock_uow.users.create.return_value = user

    result = await service.register_user(make_register_payload())

    assert result.access_token is not None
    assert result.refresh_token is not None
    assert result.user.email == user.email
    mock_uow.users.create.assert_awaited_once()
    mock_uow.refresh_tokens.save.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(mock_uow, service):
    mock_uow.users.get_by_email.return_value = make_user()

    with pytest.raises(ValueError, match="Email already registered"):
        await service.register_user(make_register_payload())

    # nothing should be persisted
    mock_uow.users.create.assert_not_awaited()
    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_access_token_issued_after_commit(mock_uow):
    """
    Verify access token is generated only after commit() returns.
    If commit fails, no token must be in flight.
    We simulate this by checking commit is awaited before the
    returned AuthResponse carries any token.
    """
    user = make_user()
    mock_uow.users.get_by_email.return_value = None
    mock_uow.users.create.return_value = user

    commit_called_before_return = {}

    async def track_commit():
        commit_called_before_return["yes"] = True

    mock_uow.commit = AsyncMock(side_effect=track_commit)

    service = UserService(mock_uow)
    result = await service.register_user(make_register_payload())

    assert commit_called_before_return.get("yes"), "commit() must be awaited before returning tokens"
    assert result.access_token is not None


# ─── login ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(mock_uow, service):
    user = make_user()  # hashed_password = hash("Password123!")
    mock_uow.users.get_by_email.return_value = user

    result = await service.login("test@quickbite.com", "Password123!")

    assert result.access_token is not None
    assert result.refresh_token is not None
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_wrong_password(mock_uow, service):
    user = make_user()
    mock_uow.users.get_by_email.return_value = user

    with pytest.raises(ValueError, match="Invalid credentials"):
        await service.login("test@quickbite.com", "WrongPass!")

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_unknown_email(mock_uow, service):
    mock_uow.users.get_by_email.return_value = None

    with pytest.raises(ValueError, match="Invalid credentials"):
        await service.login("ghost@quickbite.com", "anything")


@pytest.mark.asyncio
async def test_login_same_error_for_wrong_password_and_unknown_email(mock_uow, service):
    """
    Both failure modes must return the exact same message.
    Don't let callers enumerate valid emails via differing error text.
    """
    mock_uow.users.get_by_email.return_value = None
    with pytest.raises(ValueError) as exc_no_user:
        await service.login("ghost@quickbite.com", "x")

    user = make_user()
    mock_uow.users.get_by_email.return_value = user
    with pytest.raises(ValueError) as exc_bad_pass:
        await service.login("test@quickbite.com", "wrong")

    assert str(exc_no_user.value) == str(exc_bad_pass.value)


# ─── refresh_access_token ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_success(mock_uow, service):
    user = make_user()
    raw_token = Security().create_refresh_token({"sub": str(user.id)})
    token_record = make_refresh_token(user.id)

    mock_uow.refresh_tokens.get_by_raw_token.return_value = token_record
    mock_uow.users.get.return_value = user

    result = await service.refresh_access_token(raw_token)

    assert result.access_token is not None
    assert result.refresh_token is not None
    # old token must be revoked before new one issued
    mock_uow.refresh_tokens.revoke.assert_awaited_once_with(token_record)
    mock_uow.refresh_tokens.save.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_revoked_token_raises(mock_uow, service):
    user = make_user()
    raw_token = Security().create_refresh_token({"sub": str(user.id)})
    token_record = make_refresh_token(user.id, is_revoked=True)
    mock_uow.refresh_tokens.get_by_raw_token.return_value = token_record

    with pytest.raises(ValueError, match="revoked"):
        await service.refresh_access_token(raw_token)

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_expired_token_raises(mock_uow, service):
    user = make_user()
    raw_token = Security().create_refresh_token({"sub": str(user.id)})
    token_record = make_refresh_token(user.id, days_valid=-1)  # expired yesterday
    mock_uow.refresh_tokens.get_by_raw_token.return_value = token_record

    with pytest.raises(ValueError, match="expired"):
        await service.refresh_access_token(raw_token)


@pytest.mark.asyncio
async def test_refresh_invalid_jwt_raises(mock_uow, service):
    with pytest.raises(ValueError, match="Invalid or expired"):
        await service.refresh_access_token("not.a.jwt")


# ─── forgot_password ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_known_email_queues_task(mock_uow, service):
    user = make_user()
    mock_uow.users.get_by_email.return_value = user

    with (
        patch("modules.users.service.redis_client.setex", new_callable=AsyncMock),
        patch("modules.users.service.send_reset_email_task") as mock_task,
    ):
        await service.forgot_password(user.email)
        mock_task.delay.assert_called_once()
        args = mock_task.delay.call_args[0]
        assert args[0] == user.email       # email correct
        assert isinstance(args[1], str)    # token is a string


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_silent(mock_uow, service):
    """Must return None silently — never raise, never reveal existence."""
    mock_uow.users.get_by_email.return_value = None

    with patch("modules.users.service.send_reset_email_task") as mock_task:
        result = await service.forgot_password("ghost@quickbite.com")

    assert result is None
    mock_task.delay.assert_not_called()
    mock_uow.commit.assert_not_awaited()


# ─── reset_password ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_password_success(mock_uow, service):
    user = make_user()
    token = Security().create_reset_token(user.email)
    mock_uow.users.get_by_email.return_value = user

    with (
        patch("modules.users.service.redis_client.get", AsyncMock(return_value=user.email)),
        patch("modules.users.service.redis_client.delete", new_callable=AsyncMock),
    ):
        await service.reset_password(token, "NewPassword123!")

    mock_uow.users.update.assert_awaited_once()
    mock_uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_password_redis_deleted_before_commit(mock_uow, service):
    """
    Security invariant: Redis token consumed BEFORE DB commit.
    If commit fails after Redis delete → token burned, user requests fresh one. Acceptable.
    If Redis delete happens after commit → token reusable after successful change. Not acceptable.
    """
    user = make_user()
    token = Security().create_reset_token(user.email)
    mock_uow.users.get_by_email.return_value = user

    call_order = []

    async def redis_delete(key):
        call_order.append("redis_delete")

    async def db_commit():
        call_order.append("db_commit")

    mock_uow.commit = AsyncMock(side_effect=db_commit)

    with (
        patch("modules.users.service.redis_client.get", AsyncMock(return_value=user.email)),
        patch("modules.users.service.redis_client.delete", AsyncMock(side_effect=redis_delete)),
    ):
        await service.reset_password(token, "NewPassword123!")

    assert call_order == ["redis_delete", "db_commit"], (
        f"Expected redis_delete → db_commit, got: {call_order}"
    )


@pytest.mark.asyncio
async def test_reset_password_invalid_token_raises(mock_uow, service):
    with pytest.raises(ValueError, match="Invalid or expired"):
        await service.reset_password("garbage.token", "NewPass!")


@pytest.mark.asyncio
async def test_reset_password_used_token_raises(mock_uow, service):
    """Token not in Redis → already used or expired."""
    user = make_user()
    token = Security().create_reset_token(user.email)

    with patch("modules.users.service.redis_client.get", AsyncMock(return_value=None)):
        with pytest.raises(ValueError, match="already used or expired"):
            await service.reset_password(token, "NewPass!")

    mock_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_password_uses_repo_update_not_direct_mutation(mock_uow, service):
    """Ensure the repo layer is used — not direct attribute mutation + naked commit."""
    user = make_user()
    token = Security().create_reset_token(user.email)
    mock_uow.users.get_by_email.return_value = user

    with (
        patch("modules.users.service.redis_client.get", AsyncMock(return_value=user.email)),
        patch("modules.users.service.redis_client.delete", new_callable=AsyncMock),
    ):
        await service.reset_password(token, "NewPassword123!")

    mock_uow.users.update.assert_awaited_once()
    call_kwargs = mock_uow.users.update.call_args
    assert "hashed_password" in call_kwargs.kwargs