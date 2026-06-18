"""
Discovery 서비스 — 목록 API 호출 → collection_items 저장.
"""

import logging
from dataclasses import dataclass, field

from collectors.base import BaseCollector
from db.items import upsert_item

logger = logging.getLogger(__name__)


@dataclass
class DiscoverResult:
    source: str
    requested_filters: dict
    fetched_count: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    sample_items: list = field(default_factory=list)
    message: str = ""


def discover(
    source: str,
    collector: BaseCollector,
    filters: dict,
    conn,
) -> DiscoverResult:
    """
    목록 API 호출 → collection_items upsert.

    Parameters
    ----------
    source    : 수집기 이름 (law_text / welfare_central / ...)
    collector : 해당 수집기 인스턴스
    filters   : fetch_list() 에 전달할 검색 파라미터.
                None(미사용) 파라미터는 라우터에서 이미 제외되므로
                discovered_query 에는 실제 사용한 조건만 기록된다.
    conn      : psycopg2 커넥션
    """
    items = collector.fetch_list(**filters)
    inserted = updated = 0

    with conn:
        with conn.cursor() as cur:
            for item in items:
                ext_id = collector.get_external_id(item)
                if not ext_id:
                    continue
                title = collector.get_title(item)
                payload = collector.normalize_list_item(item)

                result = upsert_item(cur, source, ext_id, title, payload, filters)
                if result == "inserted":
                    inserted += 1
                else:
                    updated += 1

    total = inserted + updated
    logger.info("[%s] discover 완료 — 수신 %d건, 신규 %d건, 갱신 %d건",
                source, len(items), inserted, updated)

    sample = []
    for item in items[:3]:
        sample.append({
            "external_id": collector.get_external_id(item),
            "title": collector.get_title(item),
        })

    return DiscoverResult(
        source=source,
        requested_filters=filters,
        fetched_count=len(items),
        inserted_count=inserted,
        updated_count=updated,
        skipped_count=0,
        sample_items=sample,
        message=f"Discovery 완료: {inserted}건 신규, {updated}건 갱신",
    )
