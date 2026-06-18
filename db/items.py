"""
collection_items / collection_targets / documents CRUD 헬퍼.
서비스 레이어에서 공통으로 사용.
"""

import hashlib
import json
import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# collection_items
# ──────────────────────────────────────────────────────────

def upsert_item(cur, source: str, external_id: str, title: str,
                list_payload: dict, discovered_query: dict) -> str:
    """
    collection_items upsert.
    Returns: 'inserted' | 'updated'
    """
    cur.execute(
        """
        INSERT INTO collection_items
            (source, external_id, title, list_payload, discovered_query)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (source, external_id) DO UPDATE SET
            title            = EXCLUDED.title,
            list_payload     = EXCLUDED.list_payload,
            discovered_query = EXCLUDED.discovered_query,
            status           = 'ACTIVE',
            last_seen_at     = NOW(),
            updated_at       = NOW()
        RETURNING (xmax = 0) AS inserted
        """,
        (
            source, external_id, title,
            json.dumps(list_payload, ensure_ascii=False),
            json.dumps(discovered_query, ensure_ascii=False),
        ),
    )
    row = cur.fetchone()
    return "inserted" if (row and row[0]) else "updated"


def list_items(cur, source: str, status: str = "ACTIVE",
               limit: int = 50, offset: int = 0) -> list[dict]:
    cur.execute(
        """
        SELECT id, source, external_id, title, list_payload,
               discovered_query, status, last_seen_at, created_at
        FROM collection_items
        WHERE source = %s AND status = %s
        ORDER BY last_seen_at DESC
        LIMIT %s OFFSET %s
        """,
        (source, status, limit, offset),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def count_items(cur, source: str, status: str = "ACTIVE") -> int:
    cur.execute(
        "SELECT COUNT(*) FROM collection_items WHERE source=%s AND status=%s",
        (source, status),
    )
    return cur.fetchone()[0]


def get_item_payload(cur, source: str, external_id: str) -> dict | None:
    """collect_items 에서 list_payload 가져오기 (small_loan sync 등)."""
    cur.execute(
        "SELECT list_payload FROM collection_items WHERE source=%s AND external_id=%s",
        (source, external_id),
    )
    row = cur.fetchone()
    return row[0] if row else None


# ──────────────────────────────────────────────────────────
# collection_targets
# ──────────────────────────────────────────────────────────

def upsert_target(cur, source: str, external_id: str, title: str) -> str:
    """
    collection_targets upsert.
    Returns: 'inserted' | 'skipped'
    """
    cur.execute(
        """
        INSERT INTO collection_targets (source, external_id, title)
        VALUES (%s, %s, %s)
        ON CONFLICT (source, external_id) DO UPDATE SET
            title      = EXCLUDED.title,
            status     = 'ACTIVE',
            updated_at = NOW()
        RETURNING (xmax = 0) AS inserted
        """,
        (source, external_id, title),
    )
    row = cur.fetchone()
    return "inserted" if (row and row[0]) else "skipped"


def list_targets(cur, source: str, status: str = "ACTIVE",
                 limit: int = 50, offset: int = 0) -> list[dict]:
    cur.execute(
        """
        SELECT id, source, external_id, title, status,
               collect_detail, last_detail_collected_at, created_at
        FROM collection_targets
        WHERE source = %s AND status = %s
        ORDER BY last_detail_collected_at ASC NULLS FIRST
        LIMIT %s OFFSET %s
        """,
        (source, status, limit, offset),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def count_targets(cur, source: str, status: str = "ACTIVE") -> int:
    cur.execute(
        "SELECT COUNT(*) FROM collection_targets WHERE source=%s AND status=%s",
        (source, status),
    )
    return cur.fetchone()[0]


def get_sync_targets(cur, source: str, limit: int,
                     force_resync: bool = False,
                     pending_only: bool = True,
                     stale_after_days: int = None) -> list[dict]:
    """
    sync 대상 target 목록 선별.

    선별 규칙 (OR 조건 — 하나라도 만족하면 대상)
      - force_resync=True               : 모든 ACTIVE target (이미 동기화된 것 포함)
      - last_detail_collected_at IS NULL : 아직 한 번도 상세 수집 안 됨 (pending)
      - documents 행 없음                : 정제 문서가 아직 없음 (pending)
      - pending_only=False               : pending 제한 해제 → 전체 대상
      - stale_after_days 경과            : 마지막 동기화가 N일보다 오래됨 (재동기화)

    정렬: last_detail_collected_at ASC NULLS FIRST
          → 한 번도 안 한 것 → 오래된 것 순으로 처리
    """
    cur.execute(
        """
        SELECT ct.external_id, ct.title
        FROM collection_targets ct
        LEFT JOIN documents d
            ON d.source = ct.source AND d.external_id = ct.external_id
        WHERE ct.source = %(source)s
          AND ct.status = 'ACTIVE'
          AND ct.collect_detail = TRUE
          AND (
                %(force_resync)s = TRUE
             OR ct.last_detail_collected_at IS NULL
             OR d.id IS NULL
             OR %(pending_only)s = FALSE
             OR (
                  %(stale_days)s IS NOT NULL
                  AND ct.last_detail_collected_at < NOW() - make_interval(days => %(stale_days)s)
                )
          )
        ORDER BY ct.last_detail_collected_at ASC NULLS FIRST
        LIMIT %(limit)s
        """,
        {
            "source": source,
            "force_resync": force_resync,
            "pending_only": pending_only,
            "stale_days": stale_after_days,
            "limit": limit,
        },
    )
    return [{"external_id": r[0], "title": r[1]} for r in cur.fetchall()]


def count_pending_targets(cur, source: str) -> int:
    """
    아직 상세 수집이 안 된 pending target 수.
    (last_detail_collected_at IS NULL 이거나 documents 행이 없는 경우)
    """
    cur.execute(
        """
        SELECT COUNT(*)
        FROM collection_targets ct
        LEFT JOIN documents d
            ON d.source = ct.source AND d.external_id = ct.external_id
        WHERE ct.source = %s
          AND ct.status = 'ACTIVE'
          AND ct.collect_detail = TRUE
          AND (ct.last_detail_collected_at IS NULL OR d.id IS NULL)
        """,
        (source,),
    )
    return cur.fetchone()[0]


def mark_target_synced(cur, source: str, external_id: str):
    cur.execute(
        """
        UPDATE collection_targets
        SET last_detail_collected_at = NOW(), updated_at = NOW()
        WHERE source = %s AND external_id = %s
        """,
        (source, external_id),
    )


# ──────────────────────────────────────────────────────────
# documents
# ──────────────────────────────────────────────────────────

def make_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def upsert_document(cur, source: str, external_id: str, title: str,
                    raw_payload: dict, normalized_text: str,
                    metadata: dict) -> str:
    """
    documents upsert + 변경 시 document_versions 이력 저장.
    Returns: 'inserted' | 'updated' | 'unchanged'
    """
    content_hash = make_content_hash(normalized_text or "")
    raw_json = json.dumps(raw_payload, ensure_ascii=False)
    meta_json = json.dumps(metadata, ensure_ascii=False)

    # 기존 문서 조회
    cur.execute(
        "SELECT id, content_hash, version FROM documents WHERE source=%s AND external_id=%s",
        (source, external_id),
    )
    existing = cur.fetchone()

    if not existing:
        cur.execute(
            """
            INSERT INTO documents
                (source, external_id, title, content_hash,
                 raw_payload, normalized_text, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (source, external_id, title, content_hash,
             raw_json, normalized_text, meta_json),
        )
        return "inserted"

    doc_id, old_hash, version = existing
    if old_hash == content_hash:
        return "unchanged"

    # 변경됨 — 이전 버전 이력 보존
    cur.execute(
        """
        INSERT INTO document_versions
            (document_id, source, external_id, content_hash,
             raw_payload, normalized_text, metadata, version)
        SELECT id, source, external_id, content_hash,
               raw_payload, normalized_text, metadata, version
        FROM documents WHERE id = %s
        """,
        (doc_id,),
    )
    cur.execute(
        """
        UPDATE documents SET
            title          = %s,
            content_hash   = %s,
            raw_payload    = %s,
            normalized_text= %s,
            metadata       = %s,
            version        = version + 1,
            updated_at     = NOW()
        WHERE id = %s
        """,
        (title, content_hash, raw_json, normalized_text, meta_json, doc_id),
    )
    return "updated"


def get_document(cur, source: str, external_id: str) -> dict | None:
    cur.execute(
        """
        SELECT id, source, external_id, title, content_hash,
               raw_payload, normalized_text, metadata, version,
               created_at, updated_at
        FROM documents
        WHERE source = %s AND external_id = %s
        """,
        (source, external_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))
