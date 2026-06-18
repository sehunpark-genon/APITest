"""
FastAPI 공통 의존성.
"""

from typing import Generator
from fastapi import HTTPException

from db.connection import get_connection


def get_db() -> Generator:
    conn = get_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
