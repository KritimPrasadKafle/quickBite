from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Security:
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def create_access_token(self, data: dict) -> str: 
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.ACCESS_TOKEN_SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_token(self, token: str): 
        try:
            payload = jwt.decode(token, settings.ACCESS_TOKEN_SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
        
    def create_refresh_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.REFRESH_TOKEN_SECRET_KEY, algorithm=settings.ALGORITHM)
    
    def verify_refresh_token(self, token: str):
        try:
            payload = jwt.decode(token, settings.REFRESH_TOKEN_SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
        
    def create_reset_token(self, email: str) -> str:
        to_encode = {"sub": email, "type": "reset"}
        expire = datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.ACCESS_TOKEN_SECRET_KEY, algorithm=settings.ALGORITHM)

    def verify_reset_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, settings.ACCESS_TOKEN_SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "reset":
                return None
            return payload.get("sub") 
        except JWTError:
            return None
        
