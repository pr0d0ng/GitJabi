import logging
import asyncpg
from fastapi import Request
from app.settings import api_settings
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from asyncpg.pool import Pool

async def create_db_pool():
    pool = await asyncpg.create_pool(
        user=api_settings.DATABASE_USER,
        password=api_settings.DATABASE_PASSWORD,
        database=api_settings.DATABASE_DB,
        host=api_settings.DATABASE_HOST,
        port=api_settings.DATABASE_PORT
    )
    logging.info(f"A database connection pool is created: {api_settings.DATABASE_HOST}")
    return pool

async def aget_db_pool(request: Request) -> "Pool | None":
    return request.app.state.db_pool

