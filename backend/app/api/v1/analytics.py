from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_admin
from app.models.user import User, UserRole
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/owner/me")
async def my_owner_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Статистика для текущего владельца."""
    if user.role not in (UserRole.OWNER, UserRole.ADMIN):
        return {"detail": "Only owners"}
    return await AnalyticsService.owner_stats(db, owner_id=user.id)


@router.get("/platform", dependencies=[Depends(require_admin)])
async def platform_stats(db: AsyncSession = Depends(get_db)):
    """Общая статистика платформы (только админ)."""
    return await AnalyticsService.platform_stats(db)