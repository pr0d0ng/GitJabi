import os
from contextlib import contextmanager
from typing import Iterator
from psycopg2 import pool, extensions
from psycopg2 import DatabaseError

def get_db_pool_singleton() -> "DatabasePool":
    if not hasattr(get_db_pool_singleton, '_dbpool'):
        setattr(get_db_pool_singleton, '_dbpool', DatabasePool())
    return getattr(get_db_pool_singleton, '_dbpool')

class DatabasePool:
    _pool = None

    def __init__(self):
        self._initialize()

    @classmethod
    def _initialize(cls):
        """커넥션 풀을 초기화합니다. 앱 시작 시 한 번만 호출해야 합니다."""
        if cls._pool is None:
            try:
                cls._pool = pool.ThreadedConnectionPool(
                    minconn=1,  
                    maxconn=10, 
                    host=os.getenv("DB_HOST", "localhost"),
                    database=os.getenv("DB_NAME", "postgres"),
                    user=os.getenv("DB_USER", "postgres"),
                    password=os.getenv("DB_PASSWORD", "password"),
                    port=os.getenv("DB_PORT", 5432)
                )
                print("Connected to PostgreSQL now...")
            except DatabaseError as e:
                print(f"커넥션 풀 생성 실패: {e}")
                raise

    @classmethod
    @contextmanager
    def get_connection(cls) -> Iterator[extensions.connection]:
        """
        풀에서 커넥션을 하나 빌려오고, 사용이 끝나면 자동으로 반환합니다.
        with 구문과 함께 사용해야 합니다.
        """
        if cls._pool is None:
            cls._initialize()
            
        conn = cls._pool.getconn()
        try:
            # yield를 통해 호출자에게 커넥션 제공
            yield conn
        finally:
            # 오류가 발생하든 정상 종료되든 반드시 커넥션을 풀에 반납
            cls._pool.putconn(conn)

    @classmethod
    def close_all(cls):
        """앱이 종료될 때 모든 커넥션을 안전하게 닫습니다."""
        if cls._pool is not None:
            cls._pool.closeall()
            print("* 모든 PSQL 커넥션이 안전하게 종료됨.")