import uuid
from typing import Protocol, runtime_checkable
from sqlalchemy.ext.asyncio import AsyncSession
from .model import User


@runtime_checkable
class IUserRepository(Protocol):
    async def get(self, db: AsyncSession, id: uuid.UUID) -> User | None:
        ...

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        ...

    async def create(self, db: AsyncSession, user: User) -> User:
        ...