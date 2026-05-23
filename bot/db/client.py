from __future__ import annotations

import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        logger.info("Database pool connected")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool

    async def apply_migrations(self, migrations_dir: Path) -> None:
        files = sorted(migrations_dir.glob("*.sql"))
        async with self.pool.acquire() as conn:
            for f in files:
                logger.info("Applying migration %s", f.name)
                await conn.execute(f.read_text(encoding="utf-8"))
