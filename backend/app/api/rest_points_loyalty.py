"""
Rest Points Loyalty API — кошелёк, транзакции, уровни.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.rest_points_wallet import (
    RestPointsWallet,
    RestPointsTransaction,
    LoyaltyLevel,
)
from app.api.auth import get_current_user
from app.services.rest_points_service import RestPointsService


router = APIRouter(prefix="/api/rest-points-wallet", tags=["Rest Points Loyalty"])


@router.get("/my")
async def my_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Мой кошелёк"""
    wallet = await RestPointsService.get_or_create_wallet(db, current_user.id)
    await db.commit()
    
    # Level info
    level_info = {
        LoyaltyLevel.BRONZE: {
            "name": "Бронза", "icon": "🥉",
            "discount": 0, "next_level": "Серебро",
            "points_to_next": max(0, 1000 - wallet.balance),
        },
        LoyaltyLevel.SILVER: {
            "name": "Серебро", "icon": "🥈",
            "discount": 5, "next_level": "Золото",
            "points_to_next": max(0, 5000 - wallet.balance),
        },
        LoyaltyLevel.GOLD: {
            "name": "Золото", "icon": "🥇",
            "discount": 10, "next_level": None,
            "points_to_next": 0,
        },
    }
    
    return {
        "balance": wallet.balance,
        "balance_label": f"{wallet.balance} Rest Points",
        "level": wallet.level.value,
        "level_info": level_info.get(wallet.level),
        "total_earned": wallet.total_earned,
        "total_spent": wallet.total_spent,
        "conversion_rate": "1 Rest Point = 1 KGS",
        "max_discount_pct": 50,  # Points могут покрыть до 50% брони
    }


@router.get("/transactions")
async def my_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """История транзакций points"""
    wallet = await RestPointsService.get_or_create_wallet(db, current_user.id)
    
    result = await db.execute(
        select(RestPointsTransaction)
        .where(RestPointsTransaction.wallet_id == wallet.id)
        .order_by(desc(RestPointsTransaction.created_at))
        .limit(limit)
    )
    txs = result.scalars().all()
    
    return [
        {
            "id": tx.id,
            "type": tx.type.value,
            "amount": tx.amount,
            "balance_after": tx.balance_after,
            "description": tx.description,
            "created_at": tx.created_at.isoformat(),
            "icon": "💎" if tx.amount > 0 else "💸",
            "color": "#10B981" if tx.amount > 0 else "#EF4444",
        }
        for tx in txs
    ]