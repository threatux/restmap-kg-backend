"""
Rest Point — локация на Иссык-Куле
Ядро продукта: каждая точка имеет TOUROSAT score + владельца + услуги
"""
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey, JSON, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum
from app.database import Base


class RestPointStatus(str, Enum):
    DRAFT = "draft"           # Создаётся
    PENDING = "pending"       # На модерации
    ACTIVE = "active"         # Опубликован
    INACTIVE = "inactive"     # Приостановлен


class RestPointType(str, Enum):
    YURT = "yurt"                   # Юрта
    GUESTHOUSE = "guesthouse"       # Гестхаус
    HOTEL = "hotel"                 # Отель
    CAMPING = "camping"             # Кемпинг
    ECO_VILLAGE = "eco_village"     # Эко-деревня


class RestPoint(Base):
    __tablename__ = "rest_points"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # === Owner ===
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # === Basic Info ===
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    type: Mapped[RestPointType] = mapped_column(SQLEnum(RestPointType), default=RestPointType.YURT)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_kg: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # === Location ===
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    zone: Mapped[str] = mapped_column(String(50), nullable=False)  # south/north/east/west
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    
    # === 🛰 TOUROSAT AI Score (THE STAR) ===
    tourism_score: Mapped[float] = mapped_column(Float, default=0.0)           # 0-100
    score_confidence: Mapped[float] = mapped_column(Float, default=0.0)        # 0-1
    score_method: Mapped[str] = mapped_column(String(50), default="ensemble_v3")
    score_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # === 24 TOUROSAT Features (JSON) ===
    # NDVI, NDWI, elevation, slope, distance_to_water, competitors_count, etc.
    tourosat_features: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_insights: Mapped[list] = mapped_column(JSON, default=list)  # ["✅ Мало конкурентов", ...]
    
    # === Pricing (Dynamic based on score) ===
    base_price_kgs: Mapped[float] = mapped_column(Float, nullable=False)       # Сом/ночь базовая
    current_price_kgs: Mapped[float] = mapped_column(Float, nullable=False)    # С учётом динамики
    price_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    
    # === Capacity ===
    max_guests: Mapped[int] = mapped_column(Integer, default=2)
    bedrooms: Mapped[int] = mapped_column(Integer, default=1)
    beds: Mapped[int] = mapped_column(Integer, default=1)
    
    # === Services (LLM-generated) ===
    services: Mapped[list] = mapped_column(JSON, default=list)
    # [{name: "Баня", price: 1500, description: "..."}, ...]
    
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    # ["wifi", "fireplace", "shower", "parking"]
    
    # === Transfers (from team idea) ===
    transfers: Mapped[list] = mapped_column(JSON, default=list)
    # [{from: "Бишкек", price: 3000, duration: "4h", driver_phone: "+996..."}]
    
    # === Payment Methods ===
    payment_methods: Mapped[list] = mapped_column(JSON, default=list)
    # ["cash", "mbank", "odengi", "card"]
    
    # === Media ===
    photos: Mapped[list] = mapped_column(JSON, default=list)
    # ["https://...", ...]
    cover_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # === Stats (agregated) ===
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    total_bookings: Mapped[int] = mapped_column(Integer, default=0)
    
    # === Status ===
    status: Mapped[RestPointStatus] = mapped_column(SQLEnum(RestPointStatus), default=RestPointStatus.ACTIVE)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hidden_gem: Mapped[bool] = mapped_column(Boolean, default=False)  # Скрытая жемчужина
    
    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === Relations ===
    owner = relationship("User", back_populates="rest_points")
    bookings = relationship("Booking", back_populates="rest_point", lazy="selectin")
    reviews = relationship("Review", back_populates="rest_point", lazy="selectin")