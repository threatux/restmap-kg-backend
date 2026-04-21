from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=200)
    phone: str | None = None
    role: UserRole = UserRole.TOURIST
    language: str = "ru"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole
    full_name: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    phone: str | None = None
    avatar_url: str | None = None
    is_verified: bool
    language: str
    
    class Config:
        from_attributes = True