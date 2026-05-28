from pydantic import BaseModel, EmailStr, field_validator
from shared.enums import UserRole
import uuid
from shared.base_schema import APIResponse



class CreateUser(BaseModel):
    email: EmailStr
    phone: str | None = None
    password: str
    full_name: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str




class Token(BaseModel):
    access_token: str
    token_type: str



class UserResponse(BaseModel):
    id: uuid.UUID  # ✅ instead of str
    email: str
    phone: str | None
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: str | None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email : EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 character")
        return v