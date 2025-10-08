# student_system/core/db.py
from contextlib import contextmanager
from psycopg2.pool import SimpleConnectionPool
from loguru import logger
from .config import get_settings

_pool: SimpleConnectionPool | None = None

def init_pool(minconn: int = 1, maxconn: int = 5) -> SimpleConnectionPool:
    """Uygulamayı başlatırken 1 kez çağır."""
    global _pool
    if _pool:
        return _pool
    s = get_settings()
    _pool = SimpleConnectionPool(
        minconn, maxconn,
        host=s.host, port=s.port, dbname=s.name,
        user=s.user, password=s.password,
        connect_timeout=5, options="-c timezone=Europe/Istanbul"
    )
    logger.success("DB pool ready → {}@{}:{}/{}", s.user, s.host, s.port, s.name)
    return _pool

@contextmanager
def cursor():
    pool = init_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            yield cur
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)

def execute(sql: str, params: tuple | None = None):
    with cursor() as cur:
        cur.execute(sql, params or ())

def fetch_one(sql: str, params: tuple | None = None):
    with cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()

def fetch_all(sql: str, params: tuple | None = None):
    with cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()
