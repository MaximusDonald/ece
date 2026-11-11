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
        # create_all does not add columns to existing tables; this additive
        # migration keeps existing local databases compatible.
        await conn.exec_driver_sql(
            "ALTER TABLE document ADD COLUMN IF NOT EXISTS document_type VARCHAR(50);"
        )
        # Additive fields for scheduled collection of registered legal URLs.
        for column, definition in {
            "collection_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
            "last_collection_at": "TIMESTAMP NULL",
            "last_successful_collection_at": "TIMESTAMP NULL",
            "last_collection_status": "VARCHAR(20) NULL",
            "last_collection_run_id": "UUID NULL",
            "source_etag": "VARCHAR(500) NULL",
            "source_last_modified": "VARCHAR(200) NULL",
            "is_portal": "BOOLEAN NOT NULL DEFAULT FALSE",
            "parent_source_id": "UUID NULL REFERENCES legal_source(id) ON DELETE SET NULL",
            "original_filename": "VARCHAR(500) NULL",
            "download_url": "VARCHAR(1000) NULL",
            "minio_object_path": "VARCHAR(500) NULL",
            "legal_terms": "JSON NULL",
            "extracted_articles": "JSON NULL",
            "summary": "TEXT NULL",
            "crawl_depth": "INTEGER NOT NULL DEFAULT 2",
        }.items():
            await conn.exec_driver_sql(
                f"ALTER TABLE legal_source ADD COLUMN IF NOT EXISTS {column} {definition};"
            )

        for column, definition in {
            "discovered_urls_count": "INTEGER NOT NULL DEFAULT 0",
            "downloaded_files_count": "INTEGER NOT NULL DEFAULT 0",
            "ai_processed_count": "INTEGER NOT NULL DEFAULT 0",
        }.items():
            await conn.exec_driver_sql(
                f"ALTER TABLE source_collection_run ADD COLUMN IF NOT EXISTS {column} {definition};"
            )


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
