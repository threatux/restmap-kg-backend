"""
User model — Турист / Хозяин Rest Point / Админ Фонда
"""
from sqlalchemy import String, DateTime, Enum as SQLEnum, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum
from app.database import Base


class UserRole(str, Enum):
    TOURIST = "tourist"           # Турист
    OWNER = "owner"               # Хозяин Rest Point
    FUND_ADMIN = "fund_admin"     # WeFund
    ADMIN = "admin"               # Технический админ


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # === Credentials ===
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # === Profile ===
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # === Role & Status ===
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.TOURIST)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # === Owner-specific ===
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ru")  # ru/kg/en
    
    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === Relations ===
    rest_points = relationship("RestPoint", back_populates="owner", lazy="selectin")
    bookings = relationship("Booking", back_populates="tourist", lazy="selectin")
    wallet = relationship("RestPointsWallet", back_populates="user", uselist=False, lazy="selectin")
    reviews = relationship("Review", back_populates="tourist", lazy="selectin")