"""
Revenue Split Service — ядро бизнес-логики.
88% владельцу / 7% платформе / 5% Фонду.
"""
from dataclasses import dataclass
from typing import Dict
from backend.app.core.config import settings


@dataclass
class RevenueSplit:
    """Результат сплита для одной брони"""
    total: float
    owner: float            # 88%
    platform: float         # 7%
    fund: float             # 5%
    
    owner_pct: float = settings.REVENUE_OWNER_PCT
    platform_pct: float = settings.REVENUE_PLATFORM_PCT
    fund_pct: float = settings.REVENUE_FUND_PCT
    
    def to_dict(self) -> Dict:
        return {
            "total_kgs": round(self.total, 2),
            "split": {
                "owner": {
                    "amount_kgs": round(self.owner, 2),
                    "percentage": self.owner_pct,
                    "label": "Хозяину Rest Point",
                    "color": "#10B981",  # Зелёный
                    "icon": "🏡",
                },
                "platform": {
                    "amount_kgs": round(self.platform, 2),
                    "percentage": self.platform_pct,
                    "label": "TamgaFlow (платформа)",
                    "color": "#3B82F6",  # Синий
                    "icon": "⚙️",
                },
                "fund": {
                    "amount_kgs": round(self.fund, 2),
                    "percentage": self.fund_pct,
                    "label": "WeFund (Фонд туризма)",
                    "color": "#8B5CF6",  # Фиолетовый
                    "icon": "🏛",
                },
            },
        }


class RevenueService:
    """Сервис для расчёта и записи revenue split"""
    
    @staticmethod
    def calculate_split(total_amount_kgs: float) -> RevenueSplit:
        """Рассчитывает split 88/7/5"""
        owner = total_amount_kgs * (settings.REVENUE_OWNER_PCT / 100)
        platform = total_amount_kgs * (settings.REVENUE_PLATFORM_PCT / 100)
        fund = total_amount_kgs * (settings.REVENUE_FUND_PCT / 100)
        
        return RevenueSplit(
            total=total_amount_kgs,
            owner=owner,
            platform=platform,
            fund=fund,
        )
    
    @staticmethod
    def calculate_rest_points_cashback(total_amount_kgs: float) -> int:
        """10% кэшбек в Rest Points (1 сом = 1 point)"""
        return int(total_amount_kgs * (settings.REST_POINTS_CASHBACK_PCT / 100))
    
    @staticmethod
    async def create_transactions(db, booking):
        """
        Создаёт 3 транзакции для брони.
        Используется в /api/bookings/confirm.
        """
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        from datetime import datetime
        
        split = RevenueService.calculate_split(booking.total_amount_kgs)
        
        # 1. Owner 88%
        tx_owner = Transaction(
            booking_id=booking.id,
            type=TransactionType.OWNER_PAYOUT,
            amount_kgs=split.owner,
            percentage=split.owner_pct,
            recipient_type="owner",
            recipient_id=booking.rest_point.owner_id if booking.rest_point else None,
            recipient_name=booking.rest_point.owner.full_name if booking.rest_point and booking.rest_point.owner else "Owner",
            status=TransactionStatus.COMPLETED,
            description=f"Выплата хозяину за бронь {booking.booking_code}",
            completed_at=datetime.utcnow(),
        )
        db.add(tx_owner)
        
        # 2. Platform 7%
        tx_platform = Transaction(
            booking_id=booking.id,
            type=TransactionType.PLATFORM_FEE,
            amount_kgs=split.platform,
            percentage=split.platform_pct,
            recipient_type="platform",
            recipient_name="TamgaFlow Platform",
            status=TransactionStatus.COMPLETED,
            description=f"Комиссия платформы за бронь {booking.booking_code}",
            completed_at=datetime.utcnow(),
        )
        db.add(tx_platform)
        
        # 3. Fund 5%
        tx_fund = Transaction(
            booking_id=booking.id,
            type=TransactionType.FUND_CONTRIBUTION,
            amount_kgs=split.fund,
            percentage=split.fund_pct,
            recipient_type="fund",
            recipient_name="WeFund Tourism",
            status=TransactionStatus.COMPLETED,
            description=f"Взнос в Фонд за бронь {booking.booking_code}",
            completed_at=datetime.utcnow(),
        )
        db.add(tx_fund)
        
        await db.flush()
        return split