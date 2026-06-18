"""
Targeting 서비스 — collection_items → collection_targets 등록.
"""

import logging
from dataclasses import dataclass, field

from db.items import upsert_target, count_targets, list_targets

logger = logging.getLogger(__name__)


@dataclass
class TargetResult:
    source: str
    registered_count: int
    skipped_count: int
    target_count: int
    sample_targets: list = field(default_factory=list)


def register_targets(
    source: str,
    conn,
    limit: int | None = None,
    register_all: bool = False,
    only_active_items: bool = True,
) -> TargetResult:
    """
    collection_items → collection_targets 등록.

    Parameters
    ----------
    source            : 수집기 이름
    conn              : psycopg2 커넥션
    limit             : 최대 등록 건수 (None = 전체)
    register_all      : True  = collection_items 전체를 대상으로 등록(재등록 포함)
                        False = 아직 targets 에 없는 항목만 등록 (기본)
    only_active_items : True  = status='ACTIVE' 인 collection_items 만 대상 (기본)
                        False = 모든 상태 포함
    """
    registered = skipped = 0

    with conn:
        with conn.cursor() as cur:
            # collection_items → targets 등록 대상 조회
            query = """
                SELECT ci.external_id, ci.title
                FROM collection_items ci
                LEFT JOIN collection_targets ct
                    ON ci.source = ct.source AND ci.external_id = ct.external_id
                WHERE ci.source = %s
            """
            params = [source]
            if only_active_items:
                query += " AND ci.status = 'ACTIVE'"
            if not register_all:
                # 아직 targets 에 없는 항목만 (신규 등록)
                query += " AND ct.id IS NULL"
            query += " ORDER BY ci.last_seen_at DESC"
            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

            for ext_id, title in rows:
                result = upsert_target(cur, source, ext_id, title)
                if result == "inserted":
                    registered += 1
                else:
                    skipped += 1

            total = count_targets(cur, source)
            sample = list_targets(cur, source, limit=3)

    logger.info("[%s] targeting 완료 — 신규 등록 %d건, 스킵 %d건, 전체 %d건",
                source, registered, skipped, total)

    return TargetResult(
        source=source,
        registered_count=registered,
        skipped_count=skipped,
        target_count=total,
        sample_targets=sample,
    )
