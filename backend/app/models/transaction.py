"""
Transaction — движение денег (для Dashboard Фонда)
Каждая бронь → 3 транзакции (owner, platform, fund)
"""
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum
from app.database import Base


class TransactionType(str, Enum):
    OWNER_PAYOUT = "owner_payout"       # 88% хозяину
    PLATFORM_FEE = "platform_fee"       # 7% платформе
    FUND_CONTRIBUTION = "fund_contribution"  # 5% Фонду WeFund
    REFUND = "refund"                   # Возврат


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Transaction(Base):
    """
    Транзакция — атомарная запись движения денег.
    Используется в Dashboard Фонда для real-time потока.
    """
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # === Relations ===
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False)
    
    # === Type & Amount ===
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    amount_kgs: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)  # 88 / 7 / 5
    
    # === Destination ===
    recipient_type: Mapped[str] = mapped_column(String(50), nullable=False)  # owner/platform/fund
    recipient_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # user_id для owner
    recipient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # === Status ===
    status: Mapped[TransactionStatus] = mapped_column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # === Metadata ===
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # === Relations ===
    booking = relationship("Booking", back_populates="transactions")