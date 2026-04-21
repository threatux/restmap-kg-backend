from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from app.models.booking import BookingStatus, PaymentMethod


class BookingCreate(BaseModel):
    rest_point_id: int
    check_in_date: date
    check_out_date: date
    guests_count: int = Field(default=1, ge=1)
    use_rest_points: int = Field(default=0, ge=0)  # Сколько points использовать
    special_requests: Optional[str] = None


class BookingResponse(BaseModel):
    id: int
    booking_code: str
    tourist_id: int
    rest_point_id: int
    
    check_in_date: date
    check_out_date: date
    nights: int
    guests_count: int
    
    total_amount_kgs: float
    owner_amount_kgs: float
    platform_amount_kgs: float
    fund_amount_kgs: float
    
    rest_points_earned: int
    rest_points_used: int
    
    status: BookingStatus
    payment_method: Optional[PaymentMethod] = None
    qr_code_data: Optional[str] = None
    
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaymentConfirm(BaseModel):
    payment_method: PaymentMethod
    transaction_id: Optional[str] = None  # От платёжной системы


class CheckinRequest(BaseModel):
    booking_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None