"""Run one async Celery task and release its loop-bound DB pool before loop exit."""

import asyncio
from typing import Awaitable, TypeVar

from sqlalchemy.ext.asyncio import AsyncEngine
from app.core.database import async_engine as core_async_engine

T = TypeVar("T")


async def _run_and_dispose(awaitable: Awaitable[T], engine: AsyncEngine) -> T:
    try:
        return await awaitable
    finally:
        # Celery invokes sync tasks repeatedly, each with a fresh asyncio.run loop.
        # Dispose both the worker's engine and the shared core engine on the same loop
        # so no pooled asyncpg connection leaks across closed event loops.
        await engine.dispose()
        if core_async_engine is not engine:
            await core_async_engine.dispose()


def run_async_task(awaitable: Awaitable[T], engine: AsyncEngine) -> T:
    return asyncio.run(_run_and_dispose(awaitable, engine))
