import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.base_repository import BaseRepository
from .model import User, RefreshToken
from datetime import datetime
import hashlib
 



class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)


    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()
    
class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self):
        super().__init__(RefreshToken)

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


        
    async def save(self, db: AsyncSession, user_id: uuid.UUID, raw_token: str, expires_at: datetime) -> RefreshToken:
        refresh_token = RefreshToken(
                user_id = user_id,
                token_hash=self._hash_token(raw_token),
                expires_at = expires_at,
                is_revoked = False,
            )
        return await self.create(db, refresh_token)
    
    async def get_by_raw_token(self, db:AsyncSession, raw_token: str) -> RefreshToken | None:
        token_hash = self._hash_token(raw_token)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalars().first()
    
    async def revoke(self, db: AsyncSession, refresh_token: RefreshToken) -> None:
        refresh_token.is_revoked = True
        await db.flush()
        

