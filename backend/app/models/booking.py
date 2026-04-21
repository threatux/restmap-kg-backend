"""
Booking — бронь с revenue split 88/7/5
"""
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey, Enum as SQLEnum, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from enum import Enum
from app.database import Base


class BookingStatus(str, Enum):
    PENDING = "pending"         # Ожидает оплаты
    PAID = "paid"               # Оплачено
    CHECKED_IN = "checked_in"   # Турист заехал
    CHECKED_OUT = "checked_out" # Турист выехал
    COMPLETED = "completed"     # Завершено (с отзывом)
    CANCELLED = "cancelled"     # Отменено


class PaymentMethod(str, Enum):
    MBANK = "mbank"
    ODENGI = "odengi"
    CARD = "card"
    CASH = "cash"


class Booking(Base):
    __tablename__ = "bookings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # === Unique code для QR ===
    booking_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    # Формат: TF-YYYYMMDD-XXXXX
    
    # === Relations ===
    tourist_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    rest_point_id: Mapped[int] = mapped_column(Integer, ForeignKey("rest_points.id"), nullable=False)
    
    # === Dates ===
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    nights: Mapped[int] = mapped_column(Integer, nullable=False)
    guests_count: Mapped[int] = mapped_column(Integer, default=1)
    
    # === 💰 Revenue Split (CORE LOGIC) ===
    total_amount_kgs: Mapped[float] = mapped_column(Float, nullable=False)       # Общая сумма
    service_fee_kgs: Mapped[float] = mapped_column(Float, default=0.0)           # Сервисный сбор
    
    owner_amount_kgs: Mapped[float] = mapped_column(Float, nullable=False)       # 88%
    platform_amount_kgs: Mapped[float] = mapped_column(Float, nullable=False)    # 7%
    fund_amount_kgs: Mapped[float] = mapped_column(Float, nullable=False)        # 5% → WeFund
    
    # === Rest Points (Loyalty) ===
    rest_points_earned: Mapped[int] = mapped_column(Integer, default=0)          # Начислено (10% кэшбек)
    rest_points_used: Mapped[int] = mapped_column(Integer, default=0)            # Использовано при оплате
    
    # === Payment ===
    payment_method: Mapped[PaymentMethod | None] = mapped_column(SQLEnum(PaymentMethod), nullable=True)
    payment_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # === QR Code ===
    qr_code_data: Mapped[str | None] = mapped_column(Text, nullable=True)        # Base64 PNG
    qr_code_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # URL картинки
    
    # === Status ===
    status: Mapped[BookingStatus] = mapped_column(SQLEnum(BookingStatus), default=BookingStatus.PENDING)
    
    # === Checkin/Checkout ===
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checkin_lat: Mapped[float | None] = mapped_column(Float, nullable=True)  # Геопроверка
    checkin_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # === Metadata ===
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === Relations ===
    tourist = relationship("User", back_populates="bookings")
    rest_point = relationship("RestPoint", back_populates="bookings")
    transactions = relationship("Transaction", back_populates="booking", lazy="selectin")
    checkin = relationship("Checkin", back_populates="booking", uselist=False, lazy="selectin")
    review = relationship("Review", back_populates="booking", uselist=False, lazy="selectin")