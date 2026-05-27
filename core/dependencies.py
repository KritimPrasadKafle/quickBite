from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import Security
from modules.users.repository import UserRepository
from modules.users.model import User
import uuid

bearer_scheme = HTTPBearer()
security = Security()
user_repo = UserRepository()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                           db: AsyncSession = Depends(get_db)) -> User:
    token = credentials.credentials

    payload = security.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id : str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid token payload"
        )

    user = await user_repo.get(db, uuid.UUID(user_id))

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail = "User no longer exists")
    
    if not user.is_active:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN, detail = "Account is deactivated",
        )
    return user

def require_role(*roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied. Required roles: {', '. join(roles)}",
                                )
        return current_user
    return role_checker