from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ReviewCreate(BaseModel):
    booking_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)
    photos: List[str] = []
    
    # Sub-ratings
    cleanliness: Optional[int] = Field(None, ge=1, le=5)
    location: Optional[int] = Field(None, ge=1, le=5)
    service: Optional[int] = Field(None, ge=1, le=5)
    value: Optional[int] = Field(None, ge=1, le=5)


class ReviewResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str]
    photos: List[str]
    cleanliness: Optional[int]
    location: Optional[int]
    service: Optional[int]
    value: Optional[int]
    tourist_id: int
    rest_point_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True