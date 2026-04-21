"""
Auth endpoints: регистрация, логин, профиль
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.services.security_service import hash_password, verify_password, create_access_token, decode_access_token
from app.services.rest_points_service import RestPointsService


router = APIRouter(prefix="/api/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# === Dependency: текущий пользователь ===
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# === Register ===
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Проверка на дубликат
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Создать юзера
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        language=data.language,
        is_verified=True,  # MVP: сразу верифицирован
    )
    db.add(user)
    await db.flush()
    
    # Кошелёк Rest Points
    await RestPointsService.get_or_create_wallet(db, user.id)
    
    await db.commit()
    await db.refresh(user)
    
    # Токен
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    
    return Token(
        access_token=token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
    )


# === Login ===
@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    
    return Token(
        access_token=token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
    )


# === Me ===
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user