from contextlib import contextmanager
from typing import Any, Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import get_settings


def _connect_kwargs() -> dict[str, Any]:
    settings = get_settings()
    return {
        "host": settings["db_host"],
        "port": int(settings["db_port"]),
        "user": settings["db_user"],
        "password": settings["db_password"],
        "database": settings["db_name"],
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": True,
    }


@contextmanager
def get_connection() -> Iterator[pymysql.connections.Connection]:
    conn = pymysql.connect(**_connect_kwargs())
    try:
        yield conn
    finally:
        conn.close()


def check_connection() -> bool:
    settings = get_settings()
    if not settings["db_password"] and not settings.get("db_user"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                row = cur.fetchone()
                return bool(row and row.get("ok") == 1)
    except Exception:
        return False
