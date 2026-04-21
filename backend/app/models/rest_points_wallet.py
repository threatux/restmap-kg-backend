"""
Rest Points Wallet — кошелёк лояльности туриста
"""
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum
from app.database import Base


class LoyaltyLevel(str, Enum):
    BRONZE = "bronze"       # 0-999 points
    SILVER = "silver"       # 1000-4999
    GOLD = "gold"           # 5000+


class RestPointsWallet(Base):
    """
    Кошелёк Rest Points.
    Каждый турист → 1 кошелёк.
    """
    __tablename__ = "rest_points_wallets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # === Balance ===
    balance: Mapped[int] = mapped_column(Integer, default=0)              # Текущий баланс
    total_earned: Mapped[int] = mapped_column(Integer, default=0)         # Всего заработано
    total_spent: Mapped[int] = mapped_column(Integer, default=0)          # Всего потрачено
    
    # === Level ===
    level: Mapped[LoyaltyLevel] = mapped_column(SQLEnum(LoyaltyLevel), default=LoyaltyLevel.BRONZE)
    
    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === Relations ===
    user = relationship("User", back_populates="wallet")
    transactions = relationship("RestPointsTransaction", back_populates="wallet", lazy="selectin")


class RestPointsTransactionType(str, Enum):
    EARNED = "earned"       # Начислено (за бронь)
    SPENT = "spent"         # Использовано (оплата)
    BONUS = "bonus"         # Бонус (день рождения, реферал)
    EXPIRED = "expired"     # Истекли


class RestPointsTransaction(Base):
    """
    История начислений/списаний Rest Points.
    """
    __tablename__ = "rest_points_transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("rest_points_wallets.id"), nullable=False)
    booking_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=True)
    
    type: Mapped[RestPointsTransactionType] = mapped_column(SQLEnum(RestPointsTransactionType), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # Может быть отрицательным
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    wallet = relationship("RestPointsWallet", back_populates="transactions")