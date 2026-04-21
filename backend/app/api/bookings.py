"""
Bookings API — весь flow:
  1. Create booking (PENDING)
  2. Confirm payment (→ PAID, revenue split)
  3. Checkin (QR) → локальная инфа
  4. Checkout (QR)
  5. Review (→ points bonus)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date
from typing import List
import uuid

from app.database import get_db
from app.models.user import User
from app.models.rest_point import RestPoint
from app.models.booking import Booking, BookingStatus
from app.models.checkin import Checkin
from app.schemas.booking import (
    BookingCreate,
    BookingResponse,
    PaymentConfirm,
    CheckinRequest,
)
from app.api.auth import get_current_user
from app.services.revenue_service import RevenueService
from app.services.rest_points_service import RestPointsService
from app.services.qr_service import QRService
from app.services.weather_service import WeatherService


router = APIRouter(prefix="/api/bookings", tags=["Bookings"])


def _generate_booking_code() -> str:
    """TF-20251108-ABC123"""
    today = datetime.utcnow().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TF-{today}-{suffix}"


# ============================================================
# 📝 CREATE BOOKING (PENDING)
# ============================================================
@router.post("/", response_model=BookingResponse, status_code=201)
async def create_booking(
    data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создаёт бронь в статусе PENDING (ждёт оплаты)"""
    
    # === 1. Валидация дат ===
    if data.check_in_date < date.today():
        raise HTTPException(status_code=400, detail="Check-in date must be in the future")
    if data.check_out_date <= data.check_in_date:
        raise HTTPException(status_code=400, detail="Check-out must be after check-in")
    
    nights = (data.check_out_date - data.check_in_date).days
    
    # === 2. Rest Point ===
    result = await db.execute(select(RestPoint).where(RestPoint.id == data.rest_point_id))
    rp = result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Rest point not found")
    if rp.status.value != "active":
        raise HTTPException(status_code=400, detail="Rest point not available")
    if data.guests_count > rp.max_guests:
        raise HTTPException(status_code=400, detail=f"Max {rp.max_guests} guests")
    
    # === 3. Расчёт суммы ===
    total = rp.current_price_kgs * nights
    
    # === 4. Проверка Rest Points (если используются) ===
    rest_points_used = 0
    if data.use_rest_points > 0:
        wallet = await RestPointsService.get_or_create_wallet(db, current_user.id)
        if wallet.balance < data.use_rest_points:
            raise HTTPException(status_code=400, detail="Not enough Rest Points")
        # Points максимум могут покрыть 50% от суммы
        max_usable = int(total * 0.5)
        rest_points_used = min(data.use_rest_points, max_usable)
        total -= rest_points_used  # 1 point = 1 сом
    
    # === 5. Revenue Split ===
    split = RevenueService.calculate_split(total)
    
    # === 6. Rest Points cashback (10% от итога) ===
    points_earned = RevenueService.calculate_rest_points_cashback(total)
    
    # === 7. Create booking ===
    booking = Booking(
        booking_code=_generate_booking_code(),
        tourist_id=current_user.id,
        rest_point_id=rp.id,
        check_in_date=data.check_in_date,
        check_out_date=data.check_out_date,
        nights=nights,
        guests_count=data.guests_count,
        total_amount_kgs=total,
        owner_amount_kgs=split.owner,
        platform_amount_kgs=split.platform,
        fund_amount_kgs=split.fund,
        rest_points_earned=points_earned,
        rest_points_used=rest_points_used,
        special_requests=data.special_requests,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    
    return booking


# ============================================================
# 💳 CONFIRM PAYMENT (PENDING → PAID)
# ============================================================
@router.post("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_payment(
    booking_id: int,
    data: PaymentConfirm,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    После успешной оплаты:
      1. Статус → PAID
      2. Создаём 3 transactions (88/7/5)
      3. Генерируем QR
      4. Списываем использованные points
    """
    result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.tourist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Booking already processed")
    
    # Загружаем rest_point для revenue service
    rp_result = await db.execute(
        select(RestPoint).where(RestPoint.id == booking.rest_point_id)
    )
    booking.rest_point = rp_result.scalar_one()
    
    # === 1. Update status ===
    booking.status = BookingStatus.PAID
    booking.payment_method = data.payment_method
    booking.payment_transaction_id = data.transaction_id or f"demo-{uuid.uuid4().hex[:8]}"
    booking.paid_at = datetime.utcnow()
    
    # === 2. Revenue split → 3 transactions ===
    await RevenueService.create_transactions(db, booking)
    
    # === 3. QR-код ===
    qr_data = QRService.generate_booking_qr(
        booking_code=booking.booking_code,
        rest_point_id=booking.rest_point_id,
        tourist_id=booking.tourist_id,
    )
    booking.qr_code_data = qr_data
    
    # === 4. Списываем использованные points ===
    if booking.rest_points_used > 0:
        await RestPointsService.spend_points(
            db, current_user.id, booking.rest_points_used,
            booking_id=booking.id,
            description=f"Оплата брони {booking.booking_code}",
        )
    
    # === 5. Обновляем статистику rest point ===
    rp = booking.rest_point
    rp.total_bookings += 1
    
    await db.commit()
    await db.refresh(booking)
    return booking


# ============================================================
# ✅ CHECKIN (QR) — турист приехал
# ============================================================
@router.post("/checkin")
async def checkin(
    data: CheckinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Чекин по QR-коду.
    Возвращает турист-локальную информацию:
      - погода
      - ближайшие услуги
      - персонализированные активности
    """
    # === 1. Найти бронь по коду ===
    result = await db.execute(
        select(Booking).where(Booking.booking_code == data.booking_code)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.tourist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    
    if booking.status != BookingStatus.PAID:
        raise HTTPException(status_code=400, detail="Booking not paid yet")
    
    # === 2. Rest Point ===
    rp_result = await db.execute(
        select(RestPoint).where(RestPoint.id == booking.rest_point_id)
    )
    rp = rp_result.scalar_one()
    
    # === 3. Update booking ===
    booking.status = BookingStatus.CHECKED_IN
    booking.checked_in_at = datetime.utcnow()
    
    # === 4. Погода на месте ===
    weather = await WeatherService.get_current_weather(rp.latitude, rp.longitude)
    
    # === 5. Запись в checkins ===
    checkin_entry = Checkin(
        booking_id=booking.id,
        tourist_id=current_user.id,
        rest_point_id=rp.id,
        latitude=data.latitude,
        longitude=data.longitude,
        weather_data=weather,
    )
    db.add(checkin_entry)
    
    await db.commit()
    await db.refresh(booking)
    
    # === 6. Персонализированные рекомендации ===
    recommendations = [
        {"icon": "🐎", "title": "Конные прогулки", "distance_km": 2.5, "price_kgs": 1500},
        {"icon": "🛶", "title": "Каякинг", "distance_km": 1.2, "price_kgs": 2000},
        {"icon": "🔥", "title": "Баня на дровах", "distance_km": 0.1, "price_kgs": 1500},
        {"icon": "🍽", "title": "Ужин у озера", "distance_km": 3.5, "price_kgs": 800},
    ]
    
    return {
        "status": "checked_in",
        "booking": {
            "code": booking.booking_code,
            "rest_point_name": rp.name,
            "check_in_at": booking.checked_in_at.isoformat(),
            "check_out_date": booking.check_out_date.isoformat(),
            "nights_remaining": (booking.check_out_date - date.today()).days,
        },
        "welcome_message": f"🎉 Добро пожаловать в {rp.name}!",
        "weather": weather,
        "recommendations": recommendations,
        "emergency_contacts": {
            "police": "102",
            "ambulance": "103",
            "rescue": "161",
            "tamgaflow_support": "+996 555 TAMGA",
        },
    }


# ============================================================
# 🚪 CHECKOUT
# ============================================================
@router.post("/{booking_id}/checkout")
async def checkout(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Checkout → бронь COMPLETED.
    Начисляются Rest Points.
    """
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.tourist_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")
    if booking.status != BookingStatus.CHECKED_IN:
        raise HTTPException(status_code=400, detail="Not checked in")
    
    # === Update ===
    booking.status = BookingStatus.COMPLETED
    booking.checked_out_at = datetime.utcnow()
    
    # === Начисляем Rest Points ===
    if booking.rest_points_earned > 0:
        await RestPointsService.earn_points(
            db,
            user_id=current_user.id,
            amount=booking.rest_points_earned,
            booking_id=booking.id,
            description=f"Кэшбек за бронь {booking.booking_code}",
        )
    
    await db.commit()
    await db.refresh(booking)
    
    return {
        "status": "completed",
        "booking_code": booking.booking_code,
        "rest_points_earned": booking.rest_points_earned,
        "message": f"✨ Спасибо! Вам начислено {booking.rest_points_earned} Rest Points",
        "review_bonus_available": 50,  # +50 за отзыв
    }


# ============================================================
# 📋 MY BOOKINGS
# ============================================================
@router.get("/my", response_model=List[BookingResponse])
async def my_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: BookingStatus = None,
):
    """Мои брони"""
    query = select(Booking).where(Booking.tourist_id == current_user.id)
    if status:
        query = query.where(Booking.status == status)
    query = query.order_by(Booking.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


# ============================================================
# 📋 OWNER BOOKINGS (для хозяина)
# ============================================================
@router.get("/owner/all", response_model=List[BookingResponse])
async def owner_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Брони для всех rest points владельца"""
    if current_user.role.value != "owner":
        raise HTTPException(status_code=403, detail="Only for owners")
    
    query = (
        select(Booking)
        .join(RestPoint, Booking.rest_point_id == RestPoint.id)
        .where(RestPoint.owner_id == current_user.id)
        .order_by(Booking.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


# ============================================================
# 📄 GET BY ID
# ============================================================
@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Только сам турист ИЛИ владелец rest point ИЛИ админ
    if booking.tourist_id != current_user.id:
        rp_res = await db.execute(
            select(RestPoint).where(RestPoint.id == booking.rest_point_id)
        )
        rp = rp_res.scalar_one()
        if rp.owner_id != current_user.id and current_user.role.value != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
    
    return booking