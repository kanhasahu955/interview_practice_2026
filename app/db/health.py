"""Lightweight async DB connectivity check for startup logging."""

import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ping_database(engine: AsyncEngine) -> tuple[bool, float, str | None]:
    """
    Returns (ok, latency_ms, error_message).
    """
    t0 = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, (time.perf_counter() - t0) * 1000, None
    except Exception as e:  # noqa: BLE001 — surface any driver error
        return False, (time.perf_counter() - t0) * 1000, f"{type(e).__name__}: {e}"
