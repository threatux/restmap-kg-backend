"""Alembic environment for TamgaFlow (async SQLite)."""
import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

# 🔥 ВАЖНО: добавляем путь к проекту
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Импорт настроек (у тебя config.py в app/, не в app/core/)
from app.config import settings

# Импорт Base из database.py
from app.database import Base

# 🔥 КРИТИЧНО: импортируем ВСЕ модели чтобы Alembic их видел
from app.models import (
    User, UserRole,
    RestPoint, RestPointStatus, RestPointType,
    Booking, BookingStatus, PaymentMethod,
    Transaction, TransactionType, TransactionStatus,
    Checkin,
    Review,
    RestPointsWallet, RestPointsTransaction, LoyaltyLevel, RestPointsTransactionType,
)

config = context.config

# Устанавливаем URL базы
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # 🔥 ВАЖНО для SQLite (ALTER TABLE)
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()