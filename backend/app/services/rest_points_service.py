"""
Rest Points — loyalty service (кэшбек, уровни).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rest_points_wallet import (
    RestPointsWallet,
    RestPointsTransaction,
    RestPointsTransactionType,
    LoyaltyLevel,
)
from backend.app.core.config import settings


class RestPointsService:
    
    @staticmethod
    async def get_or_create_wallet(db: AsyncSession, user_id: int) -> RestPointsWallet:
        result = await db.execute(
            select(RestPointsWallet).where(RestPointsWallet.user_id == user_id)
        )
        wallet = result.scalar_one_or_none()
        
        if not wallet:
            wallet = RestPointsWallet(user_id=user_id, balance=0)
            db.add(wallet)
            await db.flush()
        
        return wallet
    
    @staticmethod
    def calculate_level(balance: int) -> LoyaltyLevel:
        if balance >= settings.REST_POINTS_LEVEL_GOLD:
            return LoyaltyLevel.GOLD
        elif balance >= settings.REST_POINTS_LEVEL_SILVER:
            return LoyaltyLevel.SILVER
        return LoyaltyLevel.BRONZE
    
    @staticmethod
    async def earn_points(
        db: AsyncSession,
        user_id: int,
        amount: int,
        booking_id: int = None,
        description: str = "Кэшбек за бронь",
    ) -> RestPointsWallet:
        """Начисляет points (10% от суммы брони)"""
        wallet = await RestPointsService.get_or_create_wallet(db, user_id)
        
        wallet.balance += amount
        wallet.total_earned += amount
        wallet.level = RestPointsService.calculate_level(wallet.balance)
        
        tx = RestPointsTransaction(
            wallet_id=wallet.id,
            booking_id=booking_id,
            type=RestPointsTransactionType.EARNED,
            amount=amount,
            balance_after=wallet.balance,
            description=description,
        )
        db.add(tx)
        await db.flush()
        return wallet
    
    @staticmethod
    async def spend_points(
        db: AsyncSession,
        user_id: int,
        amount: int,
        booking_id: int = None,
        description: str = "Оплата Rest Points",
    ) -> tuple[RestPointsWallet, bool]:
        """Списывает points. Возвращает (wallet, success)"""
        wallet = await RestPointsService.get_or_create_wallet(db, user_id)
        
        if wallet.balance < amount:
            return wallet, False
        
        wallet.balance -= amount
        wallet.total_spent += amount
        
        tx = RestPointsTransaction(
            wallet_id=wallet.id,
            booking_id=booking_id,
            type=RestPointsTransactionType.SPENT,
            amount=-amount,
            balance_after=wallet.balance,
            description=description,
        )
        db.add(tx)
        await db.flush()
        return wallet, True
    
    @staticmethod
    async def award_review_bonus(db: AsyncSession, user_id: int, booking_id: int) -> RestPointsWallet:
        """+50 points за отзыв"""
        return await RestPointsService.earn_points(
            db, user_id, amount=50,
            booking_id=booking_id,
            description="Бонус +50 за отзыв",
        )