"""
Analytics service — aggregated metrics for owner & admin.
"""
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.rest_point import RestPoint


class AnalyticsService:
    """Сервис бизнес-аналитики."""
    
    @staticmethod
    async def owner_stats(db: AsyncSession, owner_id: int) -> dict[str, Any]:
        """Собирает статистику для владельца."""
        
        # Общее количество бронирований
        total_bookings_q = (
            select(func.count(Booking.id))
            .join(RestPoint, Booking.rest_point_id == RestPoint.id)
            .where(RestPoint.owner_id == owner_id)
        )
        total_bookings = (await db.execute(total_bookings_q)).scalar() or 0
        
        # Подтверждённые + активные
        confirmed_q = (
            select(func.count(Booking.id))
            .join(RestPoint, Booking.rest_point_id == RestPoint.id)
            .where(
                RestPoint.owner_id == owner_id,
                Booking.status.in_([
                    BookingStatus.CONFIRMED,
                    BookingStatus.CHECKED_IN,
                    BookingStatus.COMPLETED,
                ]),
            )
        )
        confirmed = (await db.execute(confirmed_q)).scalar() or 0
        
        # Общий доход (только за COMPLETED)
        revenue_q = (
            select(func.coalesce(func.sum(Booking.owner_amount_kgs), 0))
            .join(RestPoint, Booking.rest_point_id == RestPoint.id)
            .where(
                RestPoint.owner_id == owner_id,
                Booking.status == BookingStatus.COMPLETED,
            )
        )
        total_revenue = float((await db.execute(revenue_q)).scalar() or 0)
        
        # Доход за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        revenue_30d_q = (
            select(func.coalesce(func.sum(Booking.owner_amount_kgs), 0))
            .join(RestPoint, Booking.rest_point_id == RestPoint.id)
            .where(
                RestPoint.owner_id == owner_id,
                Booking.status == BookingStatus.COMPLETED,
                Booking.created_at >= thirty_days_ago,
            )
        )
        revenue_30d = float((await db.execute(revenue_30d_q)).scalar() or 0)
        
        # Количество локаций
        rest_points_count_q = (
            select(func.count(RestPoint.id)).where(RestPoint.owner_id == owner_id)
        )
        rest_points_count = (await db.execute(rest_points_count_q)).scalar() or 0
        
        # Активные локации
        active_rp_q = (
            select(func.count(RestPoint.id)).where(
                RestPoint.owner_id == owner_id,
                RestPoint.status == 'approved',
                RestPoint.is_active.is_(True),
            )
        )
        active_rest_points = (await db.execute(active_rp_q)).scalar() or 0
        
        # Средний чек
        avg_check_q = (
            select(func.coalesce(func.avg(Booking.total_kgs), 0))
            .join(RestPoint, Booking.rest_point_id == RestPoint.id)
            .where(
                RestPoint.owner_id == owner_id,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED]),
            )
        )
        avg_check = float((await db.execute(avg_check_q)).scalar() or 0)
        
        # Conversion rate
        conversion = (
            (confirmed / total_bookings * 100) if total_bookings > 0 else 0
        )
        
        return {
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed,
            "total_revenue_kgs": round(total_revenue, 2),
            "revenue_30d_kgs": round(revenue_30d, 2),
            "rest_points_count": rest_points_count,
            "active_rest_points": active_rest_points,
            "avg_check_kgs": round(avg_check, 2),
            "conversion_rate": round(conversion, 1),
        }
    
    @staticmethod
    async def platform_stats(db: AsyncSession) -> dict[str, Any]:
        """Для админа: общая статистика платформы."""
        from app.models.user import User
        
        # Пользователи
        users_q = select(func.count(User.id))
        total_users = (await db.execute(users_q)).scalar() or 0
        
        # Локации по статусам
        rp_pending_q = select(func.count(RestPoint.id)).where(
            RestPoint.status == 'pending'
        )
        rp_pending = (await db.execute(rp_pending_q)).scalar() or 0
        
        rp_approved_q = select(func.count(RestPoint.id)).where(
            RestPoint.status == 'approved'
        )
        rp_approved = (await db.execute(rp_approved_q)).scalar() or 0
        
        # Выручка платформы
        platform_fee_q = select(
            func.coalesce(func.sum(Booking.platform_fee_kgs), 0)
        ).where(Booking.status == BookingStatus.COMPLETED)
        platform_revenue = float((await db.execute(platform_fee_q)).scalar() or 0)
        
        # Общий GMV
        gmv_q = select(func.coalesce(func.sum(Booking.total_kgs), 0)).where(
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.COMPLETED])
        )
        gmv = float((await db.execute(gmv_q)).scalar() or 0)
        
        return {
            "total_users": total_users,
            "pending_moderation": rp_pending,
            "approved_rest_points": rp_approved,
            "platform_revenue_kgs": round(platform_revenue, 2),
            "gmv_kgs": round(gmv, 2),
        }