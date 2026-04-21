from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.rest_point import RestPointType, RestPointStatus


class RestPointCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    type: RestPointType = RestPointType.YURT
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    zone: str = "south"
    address: Optional[str] = None
    base_price_kgs: float = Field(..., gt=0)
    max_guests: int = Field(default=2, ge=1, le=50)
    bedrooms: int = Field(default=1, ge=1)
    beds: int = Field(default=1, ge=1)
    amenities: List[str] = []
    payment_methods: List[str] = ["cash", "mbank", "odengi"]
    photos: List[str] = []
    description: Optional[str] = None
    
    # Если хотим заполнить авто через LLM:
    auto_generate_description: bool = True


class RestPointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price_kgs: Optional[float] = None
    max_guests: Optional[int] = None
    amenities: Optional[List[str]] = None
    photos: Optional[List[str]] = None
    status: Optional[RestPointStatus] = None


class RestPointResponse(BaseModel):
    id: int
    name: str
    slug: str
    type: RestPointType
    description: str
    description_kg: Optional[str] = None
    description_en: Optional[str] = None
    latitude: float
    longitude: float
    zone: str
    address: Optional[str] = None
    
    # TOUROSAT
    tourism_score: float
    score_confidence: float
    score_method: str
    tourosat_features: dict
    ai_insights: List[str]
    
    # Pricing
    base_price_kgs: float
    current_price_kgs: float
    price_multiplier: float
    
    # Info
    max_guests: int
    bedrooms: int
    beds: int
    services: List[dict]
    amenities: List[str]
    transfers: List[dict]
    payment_methods: List[str]
    photos: List[str]
    cover_photo: Optional[str] = None
    
    # Stats
    avg_rating: float
    total_reviews: int
    total_bookings: int
    
    # Status
    status: RestPointStatus
    is_featured: bool
    is_hidden_gem: bool
    
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class RestPointListItem(BaseModel):
    """Упрощённый для списков"""
    id: int
    name: str
    type: RestPointType
    latitude: float
    longitude: float
    tourism_score: float
    current_price_kgs: float
    max_guests: int
    cover_photo: Optional[str] = None
    avg_rating: float
    is_hidden_gem: bool
    
    class Config:
        from_attributes = True