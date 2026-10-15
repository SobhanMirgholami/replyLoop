"""A tiny database layer: SQLite locally, Postgres (Supabase) in production.

All SQL in this project is written once, with ? placeholders, in syntax both databases understand
(ON CONFLICT upserts, RETURNING). For Postgres the placeholders are converted to %s.
"""
import sqlite3
import threading
from contextlib import contextmanager

from config import DATABASE_URL

IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
ID = "BIGSERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"

_pool = None
_pool_lock = threading.Lock()


def _sqlite_path() -> str:
    return DATABASE_URL.removeprefix("sqlite:///") or "replyloop.db"


@contextmanager
def _conn():
    global _pool
    if IS_PG:
        if _pool is None:
            with _pool_lock:
                if _pool is None:
                    from psycopg.rows import dict_row
                    from psycopg_pool import ConnectionPool
                    # prepare_threshold=None: Supabase's pooler doesn't support prepared statements
                    _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, open=True,
                                           kwargs={"row_factory": dict_row, "prepare_threshold": None})
        with _pool.connection() as c:   # commits on success, rolls back on error
            yield c
    else:
        c = sqlite3.connect(_sqlite_path(), timeout=10)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()


def _sql(sql: str) -> str:
    return sql.replace("%", "%%").replace("?", "%s") if IS_PG else sql


def rows(sql: str, params=()) -> list[dict]:
    with _conn() as c:
        cur = c.execute(_sql(sql), tuple(params))
        return [dict(r) for r in cur.fetchall()] if cur.description else []


def row(sql: str, params=()) -> dict | None:
    r = rows(sql, params)
    return r[0] if r else None


def run(sql: str, params=()) -> int:
    """Runs a statement; returns how many rows it changed."""
    with _conn() as c:
        return c.execute(_sql(sql), tuple(params)).rowcount


def run_many(statements: list[str]):
    with _conn() as c:
        for s in statements:
            c.execute(_sql(s))
