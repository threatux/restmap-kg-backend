"""
Checkin/Checkout — QR-сканирование
"""
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database import Base


class Checkin(Base):
    """
    Чекин/Чекаут через QR.
    При чекине турист получает локальную инфу (врач, милиция, погода).
    """
    __tablename__ = "checkins"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    
    # === Checkin ===
    checkin_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checkin_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    checkin_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    checkin_verified: Mapped[bool] = mapped_column(default=False)  # Геопроверка пройдена
    
    # === Local Info (при чекине) ===
    weather_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    # {temp: 18, condition: "sunny", wind: 5}
    
    nearby_medical: Mapped[list] = mapped_column(JSON, default=list)
    # [{name, phone, distance_km, address}]
    
    nearby_police: Mapped[list] = mapped_column(JSON, default=list)
    
    emergency_contacts: Mapped[dict] = mapped_column(JSON, default=dict)
    # {police: "102", medical: "103", fire: "101"}
    
    # === Checkout ===
    checkout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checkout_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # === Relations ===
    booking = relationship("Booking", back_populates="checkin")