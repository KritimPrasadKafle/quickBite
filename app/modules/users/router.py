# users/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from .repository import UserRepository, RefreshTokenRepository
from .service import UserService
from .schemas import CreateUser, LoginRequest, AuthResponse, UserResponse, RefreshTokenRequest,ResetPasswordRequest, ForgotPasswordRequest
from core.dependencies import get_current_user, require_role
from modules.users.model import User

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.redis import blacklist_token
from shared.base_schema import APIResponse

router = APIRouter()
bearer_scheme = HTTPBearer()

def get_user_service() -> UserService:
    return UserService(repo=UserRepository(), refresh_repo=RefreshTokenRepository())


@router.post("/register", response_model=APIResponse[AuthResponse], status_code=201)
async def register(
    user: CreateUser,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
):
    try:
        result = await service.register_user(db, user)
        return APIResponse(
            message="User registered successfully",
            status_code=201,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=APIResponse[AuthResponse], status_code=200)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
):
    try:
        result = await service.login(db, credentials.email, credentials.password)
        return APIResponse(
            message="Login successful",
            status_code=200,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    

@router.get("/me", response_model = APIResponse[UserResponse], status_code=200)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return APIResponse(
        message="User fetched successfully",
        status_code=200,
        data=current_user
    )

@router.get("/admin-only", response_model=APIResponse, status_code=200)
async def admin_only(
    current_user: User = Depends(require_role("ADMIN")),
):
    return APIResponse(
        message=f"Welcome {current_user.full_name}, you are an ADMIN",
        status_code=200,
    )


@router.post("/logout",response_model=APIResponse, status_code = 200)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                 current_user: User = Depends(get_current_user)):
    await blacklist_token(credentials.credentials)
    return APIResponse(
        message="Successfully logged out",
        status_code=200,
    )

@router.post("/refresh",  response_model=APIResponse[AuthResponse], status_code=200)
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service),
):
    try:
        result = await service.refresh_access_token(db, body.refresh_token)
        return APIResponse(
            message="Token refreshed successfully",
            status_code=200,
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
@router.post("/forgot-password", response_model=APIResponse, status_code=200)
async def forgot_password(
    body: ForgotPasswordRequest, 
    db: AsyncSession = Depends(get_db),
    service: UserService = Depends(get_user_service)
):
    await service.forgot_password(db, body.email)
    return APIResponse(
        message="If that email exists, a reset link has been sent",
        status_code=200
    )

@router.post("/reset-password", response_model=APIResponse, status_code=200)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db), service: UserService = Depends(get_user_service)):
    try:
        await service.reset_password(db, body.token, body.new_password)
        return APIResponse(
            message="Password reset successfully",
            status_code=200,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    