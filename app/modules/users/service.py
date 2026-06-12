
import uuid
import hashlib
from datetime import datetime, timedelta, timezone

from .model import User
from .schemas import CreateUser, AuthResponse
from core.security import Security
from core.config import settings
from core.redis import redis_client
from core.unit_of_work import UnitOfWork
from core.tasks import send_reset_email_task


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.security = Security()

    # ── Register ──────────────────────────────────────────────────────

    async def register_user(self, data: CreateUser) -> AuthResponse:
        existing = await self.uow.users.get_by_email(data.email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=data.email,
            phone=data.phone,
            hashed_password=self.security.hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        user = await self.uow.users.create(user)

        raw_refresh_token = self.security.create_refresh_token(
            data={"sub": str(user.id)}
        )
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.uow.refresh_tokens.save(user.id, raw_refresh_token, expires_at)

        await self.uow.commit()  # access token only issued after a successful commit

        access_token = self.security.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=raw_refresh_token,
            user=user,
        )

    # ── Login ─────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> AuthResponse:
        user = await self.uow.users.get_by_email(email)
        if not user or not self.security.verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")  # same error — don't reveal which field failed

        raw_refresh_token = self.security.create_refresh_token(
            data={"sub": str(user.id)}
        )
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.uow.refresh_tokens.save(user.id, raw_refresh_token, expires_at)
        await self.uow.commit()

        access_token = self.security.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=raw_refresh_token,
            user=user,
        )

    # ── Refresh ───────────────────────────────────────────────────────

    async def refresh_access_token(self, raw_refresh_token: str) -> AuthResponse:
        payload = self.security.verify_refresh_token(raw_refresh_token)
        if not payload:
            raise ValueError("Invalid or expired refresh token")

        token_record = await self.uow.refresh_tokens.get_by_raw_token(raw_refresh_token)
        if not token_record:
            raise ValueError("Refresh token not found")
        if token_record.is_revoked:
            raise ValueError("Refresh token has been revoked")

        # DB stores naive UTC datetimes — attach tzinfo before comparing
        token_expires = token_record.expires_at.replace(tzinfo=timezone.utc)
        if token_expires < datetime.now(timezone.utc):
            raise ValueError("Refresh token has expired")

        user = await self.uow.users.get(token_record.user_id)
        if not user:
            raise ValueError("User not found")

        # revoke old token BEFORE issuing new one — rotation
        await self.uow.refresh_tokens.revoke(token_record)

        new_access_token = self.security.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        new_refresh_token = self.security.create_refresh_token(
            data={"sub": str(user.id)}
        )
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.uow.refresh_tokens.save(user.id, new_refresh_token, expires_at)
        await self.uow.commit()

        return AuthResponse(
            access_token=new_access_token,
            token_type="bearer",
            refresh_token=new_refresh_token,
            user=user,
        )

    # ── Helpers ───────────────────────────────────────────────────────

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.uow.users.get(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.uow.users.get_by_email(email)

    # ── Password reset ────────────────────────────────────────────────

    async def forgot_password(self, email: str) -> None:
        user = await self.uow.users.get_by_email(email)
        if not user:
            return  # silent — don't reveal whether email is registered

        reset_token = self.security.create_reset_token(email)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

        await redis_client.setex(
            f"reset:{token_hash}",
            settings.RESET_TOKEN_EXPIRE_MINUTES * 60,
            email,
        )
        send_reset_email_task.delay(email, reset_token)

    async def reset_password(self, token: str, new_password: str) -> None:
        email = self.security.verify_reset_token(token)
        if not email:
            raise ValueError("Invalid or expired reset token")

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stored_email = await redis_client.get(f"reset:{token_hash}")
        if not stored_email:
            raise ValueError("Reset token already used or expired")

        user = await self.uow.users.get_by_email(email)
        if not user:
            raise ValueError("User not found")

        # Delete from Redis BEFORE committing the password change.
        # If commit later fails → token is consumed, user requests a new one. Acceptable.
        # If Redis delete happens AFTER commit → token stays valid after a successful
        # password change. That's the worse failure mode.
        await redis_client.delete(f"reset:{token_hash}")

        await self.uow.users.update(
            user, hashed_password=self.security.hash_password(new_password)
        )
        await self.uow.commit()
