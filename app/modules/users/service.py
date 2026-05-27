# users/service.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from .model import User
from .schemas import CreateUser, AuthResponse
from .interface import IUserRepository
from core.security import Security


class UserService:
    def __init__(self, repo: IUserRepository):
        self.repo = repo
        self.security = Security()

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
        await db.commit()  # ✅ service owns the transaction

        token = self.security.create_access_token(
            data={
                "sub": str(user_result.id),
                "email": user_result.email,
                "role": user_result.role.value,
            }
        )

        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=user_result,
        )

    async def login(self, db: AsyncSession, email: str, password: str) -> AuthResponse:
        user = await self.repo.get_by_email(db, email)
        if not user:
            raise ValueError("Invalid credentials")

        if not self.security.verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        token = self.security.create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
            }
        )

        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=user,
        )

    async def get_user_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        return await self.repo.get(db, user_id)

    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        return await self.repo.get_by_email(db, email)