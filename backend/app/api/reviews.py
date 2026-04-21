"""
Reviews API — отзывы + бонус 50 points
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.review import Review
from app.models.booking import Booking, BookingStatus
from app.models.rest_point import RestPoint
from app.schemas.review import ReviewCreate, ReviewResponse
from app.api.auth import get_current_user
from app.services.rest_points_service import RestPointsService


router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse, status_code=201)
async def create_review(
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать отзыв + получить 50 points"""
    # Проверка: бронь существует и завершена
    result = await db.execute(select(Booking).where(Booking.id == data.booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.tourist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Finish your stay first")
    
    # Проверка на дубликат
    existing = await db.execute(
        select(Review).where(Review.booking_id == booking.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already reviewed")
    
    # Create
    review = Review(
        rating=data.rating,
        comment=data.comment,
        photos=data.photos,
        cleanliness=data.cleanliness,
        location=data.location,
        service=data.service,
        value=data.value,
        tourist_id=current_user.id,
        rest_point_id=booking.rest_point_id,
        booking_id=booking.id,
    )
    db.add(review)
    
    # Обновить рейтинг rest point
    rp_result = await db.execute(
        select(RestPoint).where(RestPoint.id == booking.rest_point_id)
    )
    rp = rp_result.scalar_one()
    
    # Пересчитать средний рейтинг
    avg_result = await db.execute(
        select(func.avg(Review.rating))
        .where(Review.rest_point_id == rp.id)
    )
    new_avg = float(avg_result.scalar() or data.rating)
    rp.avg_rating = round(new_avg, 2)
    rp.total_reviews += 1
    
    # +50 points за отзыв
    await RestPointsService.award_review_bonus(db, current_user.id, booking.id)
    
    await db.commit()
    await db.refresh(review)
    return review


@router.get("/rest-point/{rest_point_id}", response_model=List[ReviewResponse])
async def get_rest_point_reviews(
    rest_point_id: int,
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """Отзывы на rest point"""
    result = await db.execute(
        select(Review)
        .where(Review.rest_point_id == rest_point_id)
        .order_by(Review.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()