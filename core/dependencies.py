from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.security import Security
from modules.users.model import User
import uuid
from core.redis import is_token_blacklisted
from typing import AsyncGenerator
from core.unit_of_work import UnitOfWork
from core.database import async_session_factory


bearer_scheme = HTTPBearer()
security = Security()
# user_repo = UserRepository()



# Wire the factory into UnitOfWork once at import time
UnitOfWork.session_factory = async_session_factory


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """
    FastAPI dependency. Provides one UoW per request.

    The `async with` guarantees:
      - session opened before handler runs
      - session closed (and rolled back on exception) after handler returns
      - even if the handler raises an unhandled exception
    """
    async with UnitOfWork() as uow:
        yield uow


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    uow: UnitOfWork = Depends(get_uow),         
) -> User:
    token = credentials.credentials

    if await is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = security.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await uow.users.get(uuid.UUID(user_id))   # ← instance, not class
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user
def require_role(*roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied. Required roles: {', '. join(roles)}",
                                )
        return current_user
    return role_checker