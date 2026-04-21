"""
Rest Points API — самый важный endpoint (создание с AI).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from slugify import slugify
import uuid

from app.database import get_db
from app.models.user import User, UserRole
from app.models.rest_point import RestPoint, RestPointStatus, RestPointType
from app.schemas.rest_point import (
    RestPointCreate,
    RestPointUpdate,
    RestPointResponse,
    RestPointListItem,
)
from app.api.auth import get_current_user
from app.ml.inference import tourosat_engine, extract_features_from_coords
from app.services.pricing_service import PricingService
from app.services.llm_service import llm_service


router = APIRouter(prefix="/api/rest-points", tags=["Rest Points"])


# ============================================================
# ⭐ CREATE REST POINT (C AI-ПАЙПЛАЙНОМ)
# ============================================================
@router.post("/", response_model=RestPointResponse, status_code=201)
async def create_rest_point(
    data: RestPointCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    🎯 КЛЮЧЕВОЙ ENDPOINT:
    
    Pipeline:
      1. Проверка роли (OWNER или ADMIN)
      2. TOUROSAT v3 → score + insights
      3. LLM → генерация описания + сервисы
      4. PricingService → динамическая цена
      5. Определение Hidden Gem
      6. Сохранение
    """
    # === 1. Проверка роли ===
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only owners can create rest points")
    
    # === 2. TOUROSAT v3 ===
    features = extract_features_from_coords(
        lat=data.latitude,
        lon=data.longitude,
    )
    tourosat_result = tourosat_engine.predict(features)
    
    # === 3. LLM Generation (если включено) ===
    description = data.description or ""
    description_kg = ""
    description_en = ""
    services = []
    
    if data.auto_generate_description:
        llm_card = await llm_service.generate_rest_point_card(
            name=data.name,
            rest_point_type=data.type.value,
            coordinates=(data.latitude, data.longitude),
            tourosat_score=tourosat_result.score,
            insights=tourosat_result.insights,
            amenities=data.amenities,
            language="ru",
        )
        description = llm_card.get("description", description)
        description_kg = llm_card.get("description_kg", "")
        description_en = llm_card.get("description_en", "")
        services = llm_card.get("services", [])
    
    # === 4. Pricing ===
    pricing = PricingService.calculate_price(
        base_price=data.base_price_kgs,
        tourosat_score=tourosat_result.score,
        competitors_count=features.competitors_count,
    )
    
    # === 5. Hidden Gem? ===
    is_hidden_gem = (
        tourosat_result.score >= 75
        and features.competitors_count < 3
        and features.uniqueness_score > 0.6
    )
    
    # === 6. Slug (unique) ===
    base_slug = slugify(data.name)
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
    
    # === 7. Save ===
    rp = RestPoint(
        name=data.name,
        slug=slug,
        type=data.type,
        description=description,
        description_kg=description_kg,
        description_en=description_en,
        latitude=data.latitude,
        longitude=data.longitude,
        zone=data.zone,
        address=data.address,
        
        tourism_score=tourosat_result.score,
        score_confidence=tourosat_result.confidence,
        score_method=tourosat_result.method,
        tourosat_features=tourosat_result.features,
        ai_insights=tourosat_result.insights,
        
        base_price_kgs=data.base_price_kgs,
        current_price_kgs=pricing.final_price,
        price_multiplier=pricing.multiplier,
        
        max_guests=data.max_guests,
        bedrooms=data.bedrooms,
        beds=data.beds,
        services=services,
        amenities=data.amenities,
        payment_methods=data.payment_methods,
        photos=data.photos,
        cover_photo=data.photos[0] if data.photos else None,
        
        is_hidden_gem=is_hidden_gem,
        status=RestPointStatus.ACTIVE,
        owner_id=current_user.id,
    )
    
    db.add(rp)
    await db.commit()
    await db.refresh(rp)
    
    return rp


# ============================================================
# 🔍 LIST (с фильтрацией для карты)
# ============================================================
@router.get("/", response_model=List[RestPointListItem])
async def list_rest_points(
    db: AsyncSession = Depends(get_db),
    min_score: float = Query(0, ge=0, le=100),
    max_price: Optional[float] = Query(None, gt=0),
    type: Optional[RestPointType] = None,
    hidden_gems_only: bool = False,
    featured_only: bool = False,
    zone: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """Список Rest Points с фильтрами (для карты/списка)"""
    query = select(RestPoint).where(RestPoint.status == RestPointStatus.ACTIVE)
    
    if min_score > 0:
        query = query.where(RestPoint.tourism_score >= min_score)
    if max_price:
        query = query.where(RestPoint.current_price_kgs <= max_price)
    if type:
        query = query.where(RestPoint.type == type)
    if hidden_gems_only:
        query = query.where(RestPoint.is_hidden_gem == True)
    if featured_only:
        query = query.where(RestPoint.is_featured == True)
    if zone:
        query = query.where(RestPoint.zone == zone)
    
    query = query.order_by(RestPoint.tourism_score.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


# ============================================================
# 🗺 GEO SEARCH (для карты — points в bounding box)
# ============================================================
@router.get("/geo", response_model=List[RestPointListItem])
async def geo_search(
    db: AsyncSession = Depends(get_db),
    min_lat: float = Query(...),
    max_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lon: float = Query(...),
    limit: int = Query(200, le=1000),
):
    """Для отображения на карте — points в видимом регионе"""
    query = (
        select(RestPoint)
        .where(RestPoint.status == RestPointStatus.ACTIVE)
        .where(RestPoint.latitude.between(min_lat, max_lat))
        .where(RestPoint.longitude.between(min_lon, max_lon))
        .order_by(RestPoint.tourism_score.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


# ============================================================
# 📄 GET BY ID
# ============================================================
@router.get("/{rest_point_id}", response_model=RestPointResponse)
async def get_rest_point(
    rest_point_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RestPoint).where(RestPoint.id == rest_point_id)
    )
    rp = result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Rest point not found")
    return rp


# ============================================================
# ✏️ UPDATE
# ============================================================
@router.patch("/{rest_point_id}", response_model=RestPointResponse)
async def update_rest_point(
    rest_point_id: int,
    data: RestPointUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RestPoint).where(RestPoint.id == rest_point_id))
    rp = result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Not found")
    
    if rp.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not your rest point")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rp, key, value)
    
    # Пересчёт цены если изменилась base_price
    if "base_price_kgs" in update_data:
        pricing = PricingService.calculate_price(
            base_price=rp.base_price_kgs,
            tourosat_score=rp.tourism_score,
        )
        rp.current_price_kgs = pricing.final_price
        rp.price_multiplier = pricing.multiplier
    
    await db.commit()
    await db.refresh(rp)
    return rp


# ============================================================
# 🗑 DELETE (soft — меняем статус)
# ============================================================
@router.delete("/{rest_point_id}", status_code=204)
async def delete_rest_point(
    rest_point_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RestPoint).where(RestPoint.id == rest_point_id))
    rp = result.scalar_one_or_none()
    if not rp:
        raise HTTPException(status_code=404, detail="Not found")
    if rp.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not your rest point")
    
    rp.status = RestPointStatus.INACTIVE
    await db.commit()