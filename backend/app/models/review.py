"""
Review — отзыв после чекаута (за отзыв +50 Rest Points)
"""
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # === Relations ===
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), unique=True, nullable=False)
    tourist_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    rest_point_id: Mapped[int] = mapped_column(Integer, ForeignKey("rest_points.id"), nullable=False)
    
    # === Rating ===
    overall_rating: Mapped[float] = mapped_column(Float, nullable=False)  # 1-5
    cleanliness: Mapped[float | None] = mapped_column(Float, nullable=True)
    service: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[float | None] = mapped_column(Float, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # === Text ===
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # === Bonus ===
    rest_points_awarded: Mapped[int] = mapped_column(Integer, default=50)  # +50 за отзыв
    
    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # === Relations ===
    booking = relationship("Booking", back_populates="review")
    tourist = relationship("User", back_populates="reviews")
    rest_point = relationship("RestPoint", back_populates="reviews")