import uuid
from typing import Protocol, runtime_checkable
from sqlalchemy.ext.asyncio import AsyncSession
from .model import User, RefreshToken
from datetime import datetime


@runtime_checkable
class IUserRepository(Protocol):
    async def get(self, db: AsyncSession, id: uuid.UUID) -> User | None:
        ...

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        ...

    async def create(self, db: AsyncSession, user: User) -> User:
        ...


@runtime_checkable
class IRefreshTokenRepository(Protocol):
    async def save(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        raw_token: str,
        expires_at: datetime,
    ) -> RefreshToken:
        ...

    async def get_by_raw_token(
        self, db: AsyncSession, raw_token: str
    ) -> RefreshToken | None:
        ...

    async def revoke(
        self, db: AsyncSession, refresh_token: RefreshToken
    ) -> None:
        ...