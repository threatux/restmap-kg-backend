"""
Database setup для TamgaFlow
Использует SQLAlchemy 2.0 async + SQLite
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from app.config import settings


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


# Async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI — выдаёт сессию БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Создаёт все таблицы"""
    from app.models import user, rest_point, booking, transaction, checkin, review, rest_points_wallet  # noqa
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)