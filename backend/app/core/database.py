from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import get_settings
from contextlib import asynccontextmanager
from typing import AsyncGenerator

settings = get_settings()

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for Celery workers
sync_engine = create_engine(
    settings.database_url.replace("+asyncpg", ""),
    echo=False,
    pool_pre_ping=True,
)


async def init_db() -> None:
    """Initialize database tables and PGVector extension."""
    async with async_engine.begin() as conn:
        # Enable PGVector extension
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def get_sync_session() -> Session:
    return Session(sync_engine)


@asynccontextmanager
async def lifespan_db():
    await init_db()
    yield
    await async_engine.dispose()