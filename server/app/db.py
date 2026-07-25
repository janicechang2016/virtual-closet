"""Async Postgres pool. One shared pool for the app lifetime."""
from typing import Optional

import asyncpg

from .config import config

_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=1, max_size=10)
        await _ensure_budget_row()
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_pool() at startup.")
    return _pool


async def _ensure_budget_row() -> None:
    """Seed the singleton budget row from the configured cap if absent."""
    async with _pool.acquire() as con:
        await con.execute(
            """
            INSERT INTO budget (id, cap_usd, phase)
            VALUES (TRUE, $1, 'v2-foundation')
            ON CONFLICT (id) DO NOTHING
            """,
            config.BUDGET_CAP_USD,
        )
