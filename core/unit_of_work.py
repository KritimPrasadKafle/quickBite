from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from modules.users.repository import UserRepository, RefreshTokenRepository
from modules.restaurants.repository import RestaurantRepository   


class UnitOfWork:
    """
    Async context manager. One instance = one DB transaction.

    Usage in a service:
        async with uow:
            user = await uow.users.create(email=...)
            await uow.commit()

    Usage via FastAPI dependency:
        async def endpoint(uow: UnitOfWork = Depends(get_uow)):
            ...
    """

    # session_factory is set once at app startup (see core/dependencies.py)
    session_factory: async_sessionmaker[AsyncSession]

    def __init__(self):
        # session_factory must be configured before use
        pass

    async def __aenter__(self) -> "UnitOfWork":
        self.session: AsyncSession = self.session_factory()
        # Repos share this single session — one transaction, one commit
        self.users = UserRepository(self.session)
        self.refresh_tokens = RefreshTokenRepository(self.session)
        self.restaurants = RestaurantRepository(self.session)   

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        await self.session.close()
        # Returning None/False lets the exception propagate normally

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()