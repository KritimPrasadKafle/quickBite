# users/service.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from .model import User
from .schemas import CreateUser, AuthResponse
from .interface import IUserRepository, IRefreshTokenRepository
from core.security import Security
from core.config import settings
import hashlib
from core.redis import redis_client

from datetime import datetime, timedelta

from core.tasks import send_reset_email_task


class UserService:
    def __init__(self, repo: IUserRepository, refresh_repo: IRefreshTokenRepository):
        self.repo = repo
        self.security = Security()
        self.refresh_repo = refresh_repo

    async def register_user(self, db: AsyncSession, data: CreateUser) -> AuthResponse:
        existing_user = await self.repo.get_by_email(db, data.email)
        if existing_user:
            raise ValueError("Email already registered")

        user = User(
            email=data.email,
            phone=data.phone,
            hashed_password=self.security.hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )

        user_result = await self.repo.create(db, user)

        raw_refresh_token = self.security.create_refresh_token(
            data={"sub": str(user_result.id)}
        )
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_repo.save(db, user_result.id, raw_refresh_token, expires_at)

        await db.commit()  

        access_token = self.security.create_access_token(
            data={
                "sub": str(user_result.id),
                "email": user_result.email,
                "role": user_result.role.value,
            }
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=raw_refresh_token, 
            user=user_result,
        )

    async def login(self, db: AsyncSession, email: str, password: str) -> AuthResponse:
        user = await self.repo.get_by_email(db, email)
        if not user:
            raise ValueError("Invalid credentials")

        if not self.security.verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        
        raw_refresh_token = self.security.create_refresh_token(
            data={"sub": str(user.id)}
        )
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_repo.save(db, user.id, raw_refresh_token, expires_at)
        await db.commit()  

        access_token = self.security.create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
            }
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=raw_refresh_token, 
            user=user,
        )
    
    async def refresh_access_token(self, db:AsyncSession, raw_refresh_token: str) -> AuthResponse:
        payload = self.security.verify_refresh_token(raw_refresh_token)
        if not payload:
            raise ValueError("Invalid or expired refresh token")
        
        token_record = await self.refresh_repo.get_by_raw_token(db, raw_refresh_token)

        if not token_record:
            raise ValueError("Refresh token not found")
        
        if token_record.is_revoked:
            raise ValueError("Refresh token has been revoked")
    
        if token_record.expires_at < datetime.utcnow():
            raise ValueError("Refresh token has expired")
    
        user = await self.repo.get(db, token_record.user_id)
        if not user:
            raise ValueError("User not found")
        
        await self.refresh_repo.revoke(db, token_record)

        new_access_token = self.security.create_access_token(
            data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
            }
        )

        new_refresh_token = self.security.create_refresh_token(
            data = {"sub": str(user.id)}
        )

        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_repo.save(db, user.id, new_refresh_token, expires_at)
        await db.commit()

        return AuthResponse(
            access_token=new_access_token,
            token_type="bearer",
            refresh_token=new_refresh_token,
            user=user,
        )


        

    async def get_user_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        return await self.repo.get(db, user_id)

    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        return await self.repo.get_by_email(db, email)
    
    async def forgot_password(self, db: AsyncSession, email: str) -> None:
        user = await self.repo.get_by_email(db, email)
        if not user:
            # don't reveal whether email exists
            return

        reset_token = self.security.create_reset_token(email)

        # store token hash in Redis with 15 min TTL
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
        await redis_client.setex(
            f"reset:{token_hash}",
            settings.RESET_TOKEN_EXPIRE_MINUTES * 60,
            email
        )

        send_reset_email_task.delay(email, reset_token)


    async def reset_password(
        self, db: AsyncSession, token: str, new_password: str
    ) -> None:
        # verify signature and type
        email = self.security.verify_reset_token(token)
        if not email:
            raise ValueError("Invalid or expired reset token")

        # check Redis — token must not have been used already
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stored_email = await redis_client.get(f"reset:{token_hash}")
        if not stored_email:
            raise ValueError("Reset token has already been used or expired")

        # get user
        user = await self.repo.get_by_email(db, email)
        if not user:
            raise ValueError("User not found")

        # update password
        user.hashed_password = self.security.hash_password(new_password)
        await db.commit()

        # delete token from Redis — one time use
        await redis_client.delete(f"reset:{token_hash}")