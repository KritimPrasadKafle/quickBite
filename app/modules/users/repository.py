
import uuid
import hashlib
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.base_repository import BaseRepository
from .model import User, RefreshToken


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalars().first()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession):
        super().__init__(RefreshToken, session)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def save(
        self, user_id: uuid.UUID, raw_token: str, expires_at: datetime
    ) -> RefreshToken:
        obj = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(raw_token),
            expires_at=expires_at,
            is_revoked=False,
        )
        return await self.create(obj)

    async def get_by_raw_token(self, raw_token: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == self._hash_token(raw_token)
            )
        )
        return result.scalars().first()

    async def revoke(self, refresh_token: RefreshToken) -> None:
        refresh_token.is_revoked = True
        await self.session.flush()