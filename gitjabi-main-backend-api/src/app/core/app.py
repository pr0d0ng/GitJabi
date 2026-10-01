__all__ = (
    'CoreApp',
)
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.database.psql import create_db_pool

# 생명 주기
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # DB Pool 생성
        app.state.db_pool = await create_db_pool()
    except Exception as e:
        logging.error(e)
    yield
    try:
        # 자원 종료
        await app.state.db_pool.close()
    except Exception as e:
        logging.error(e)

class CoreApp(
    FastAPI
):
    def __init__(self, *args, **kwargs):
        if not 'lifespan' in kwargs:
            kwargs['lifespan'] = lifespan
        super().__init__(*args, **kwargs)

    def set_middleware(self, **kwargs):
        self.add_middleware(
            CORSMiddleware,
            **kwargs
        )

    def init_logging(self, development=False):
        if development:
            logging.basicConfig(
                level=logging.INFO,
                format="[%(levelname)s]     [%(asctime)s] [%(name)s] %(message)s",
            )

        logger = logging.getLogger("src")
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel('WARNING')
