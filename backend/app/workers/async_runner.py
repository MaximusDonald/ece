"""Run one async Celery task and release its loop-bound DB pool before loop exit."""

import asyncio
from typing import Awaitable, TypeVar

from sqlalchemy.ext.asyncio import AsyncEngine

T = TypeVar("T")


async def _run_and_dispose(awaitable: Awaitable[T], engine: AsyncEngine) -> T:
    try:
        return await awaitable
    finally:
        # Celery invokes sync tasks repeatedly, each with a fresh asyncio.run loop.
        # Dispose on the same loop that used the asyncpg connections.
        await engine.dispose()


def run_async_task(awaitable: Awaitable[T], engine: AsyncEngine) -> T:
    return asyncio.run(_run_and_dispose(awaitable, engine))
