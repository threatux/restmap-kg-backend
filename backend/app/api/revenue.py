"""
Revenue API — визуализация 88/7/5 для демо.
Этот endpoint — для красивой секции "Финансы" в UI.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.booking import Booking, BookingStatus
from app.models.transaction import Transaction, TransactionType
from app.api.auth import get_current_user
from app.services.revenue_service import RevenueService


router = APIRouter(prefix="/api/revenue", tags=["Revenue & Analytics"])


# ============================================================
# 📊 CALCULATE SPLIT (preview для UI)
# ============================================================
@router.post("/calculate-split")
async def calculate_split(amount_kgs: float):
    """
    🎯 Для UI: показать разделение до оплаты.
    Возвращает красивые данные для pie chart.
    """
    split = RevenueService.calculate_split(amount_kgs)
    cashback = RevenueService.calculate_rest_points_cashback(amount_kgs)
    
    return {
        **split.to_dict(),
        "rest_points_cashback": {
            "points": cashback,
            "label": f"+{cashback} Rest Points (10% кэшбек)",
            "icon": "💎",
        },
    }


# ============================================================
# 📈 GLOBAL STATS (для демо)
# ============================================================
@router.get("/stats/global")
async def global_stats(db: AsyncSession = Depends(get_db)):
    """
    Общая статистика платформы — для landing/демо.
    """
    # === Total transactions по типам ===
    owner_total = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount_kgs), 0))
        .where(Transaction.type == TransactionType.OWNER_PAYOUT)
    )
    platform_total = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount_kgs), 0))
        .where(Transaction.type == TransactionType.PLATFORM_FEE)
    )
    fund_total = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount_kgs), 0))
        .where(Transaction.type == TransactionType.FUND_CONTRIBUTION)
    )
    
    # Bookings
    total_bookings = await db.execute(
        select(func.count(Booking.id)).where(Booking.status.in_([
            BookingStatus.PAID, BookingStatus.CHECKED_IN, BookingStatus.COMPLETED
        ]))
    )
    
    total_revenue = await db.execute(
        select(func.coalesce(func.sum(Booking.total_amount_kgs), 0))
        .where(Booking.status != BookingStatus.PENDING)
    )
    
    owner_sum = float(owner_total.scalar() or 0)
    platform_sum = float(platform_total.scalar() or 0)
    fund_sum = float(fund_total.scalar() or 0)
    grand_total = owner_sum + platform_sum + fund_sum
    
    return {
        "summary": {
            "total_revenue_kgs": round(grand_total, 2),
            "total_bookings": int(total_bookings.scalar() or 0),
            "avg_booking_kgs": round(grand_total / max(int(total_bookings.scalar() or 1), 1), 2),
        },
        "distribution": {
            "owner": {
                "amount_kgs": round(owner_sum, 2),
                "percentage": 88,
                "label": "Выплачено хозяевам",
                "color": "#10B981",
                "icon": "🏡",
            },
            "platform": {
                "amount_kgs": round(platform_sum, 2),
                "percentage": 7,
                "label": "TamgaFlow (операционка)",
                "color": "#3B82F6",
                "icon": "⚙️",
            },
            "fund": {
                "amount_kgs": round(fund_sum, 2),
                "percentage": 5,
                "label": "WeFund (Фонд туризма)",
                "color": "#8B5CF6",
                "icon": "🏛",
            },
        },
        "fund_impact": {
            "title": "На что пойдут 5% WeFund:",
            "projects": [
                {"icon": "🚴", "title": "Велодорожки у Иссык-Куля", "allocated_kgs": round(fund_sum * 0.3, 0)},
                {"icon": "🚽", "title": "Общественные туалеты", "allocated_kgs": round(fund_sum * 0.2, 0)},
                {"icon": "♻️", "title": "Уборка пляжей", "allocated_kgs": round(fund_sum * 0.25, 0)},
                {"icon": "🌳", "title": "Озеленение", "allocated_kgs": round(fund_sum * 0.15, 0)},
                {"icon": "📡", "title": "Wi-Fi точки", "allocated_kgs": round(fund_sum * 0.1, 0)},
            ],
        },
    }


# ============================================================
# 📈 OWNER STATS (свои rest points)
# ============================================================
@router.get("/stats/owner")
async def owner_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Статистика для владельца"""
    if current_user.role.value not in ["owner", "admin"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only for owners")
    
    # Все мои brони
    from app.models.rest_point import RestPoint
    
    bookings_query = await db.execute(
        select(Booking)
        .join(RestPoint, Booking.rest_point_id == RestPoint.id)
        .where(RestPoint.owner_id == current_user.id)
        .where(Booking.status.in_([BookingStatus.PAID, BookingStatus.CHECKED_IN, BookingStatus.COMPLETED]))
    )
    bookings = bookings_query.scalars().all()
    
    total_earned = sum(b.owner_amount_kgs for b in bookings)
    total_bookings = len(bookings)
    
    # По месяцам
    monthly = {}
    for b in bookings:
        key = b.created_at.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + b.owner_amount_kgs
    
    return {
        "total_earned_kgs": round(total_earned, 2),
        "total_bookings": total_bookings,
        "avg_per_booking_kgs": round(total_earned / max(total_bookings, 1), 2),
        "monthly_chart": [
            {"month": k, "earned_kgs": round(v, 2)}
            for k, v in sorted(monthly.items())
        ],
    }