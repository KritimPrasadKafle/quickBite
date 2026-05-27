# users/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from .repository import UserRepository
from .service import UserService
from .schemas import CreateUser, LoginRequest, AuthResponse, UserResponse
from core.dependencies import get_current_user, require_role
from modules.users.model import User

router = APIRouter()


def get_user_service() -> UserService:
    return UserService(repo=UserRepository())


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    user: CreateUser,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
):
    try:
        return await service.register_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse, status_code=200)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
):
    try:
        return await service.login(db, credentials.email, credentials.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    

@router.get("/me", response_model = UserResponse, status_code=200)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user

@router.get("/admin-only", status_code = 200)
async def admin_only(current_user = Depends(require_role("ADMIN"))):
    return {"message": f"Welcome {current_user.full_name}, you are an ADMIN"}