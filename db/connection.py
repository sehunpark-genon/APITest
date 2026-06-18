"""
PostgreSQL 연결 관리
psycopg2 기반 단순 연결 팩토리 (테스트용 - 커넥션 풀 없음)
"""

import psycopg2
import psycopg2.extras
from config.settings import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def get_connection():
    """새 DB 연결 반환. 사용 후 반드시 close() 또는 with 블록으로 닫을 것."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
    )


def get_cursor(conn):
    """DictCursor 반환 (컬럼명으로 접근 가능)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
