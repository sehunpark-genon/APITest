"""
Sync 서비스 — collection_targets 기준 상세 API 호출 → documents 저장.
"""

import logging
from dataclasses import dataclass, field

from collectors.base import BaseCollector
from db.items import (
    get_sync_targets, count_pending_targets, count_targets, get_item_payload,
    upsert_document, mark_target_synced,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    source: str
    target_count: int       # 전체 ACTIVE target 수
    pending_count: int      # 아직 상세 수집 안 된 target 수 (실행 후 기준)
    synced_count: int       # 이번 실행에서 처리된 건수 (inserted+updated+unchanged)
    inserted_count: int
    updated_count: int
    unchanged_count: int
    failed_count: int
    sample_documents: list = field(default_factory=list)


def sync_details(
    source: str,
    collector: BaseCollector,
    conn,
    limit: int = 10,
    pending_only: bool = True,
    force_resync: bool = False,
    stale_after_days: int = None,
) -> SyncResult:
    """
    collection_targets 기준 상세 API 호출 → documents upsert.

    - HAS_DETAIL_API = True  : fetch_detail() 호출
    - HAS_DETAIL_API = False : collection_items.list_payload 로 대체 (small_loan)

    대상 선별 정책
    --------------
    기본(pending_only=True): 아직 상세 수집이 안 된 target(처음 동기화 또는
        documents 행 없음)만 우선 처리.
    force_resync=True: 이미 동기화된 target 도 상세 API 를 다시 호출하고
        content_hash 비교 → 동일하면 unchanged, 다르면 updated.
    stale_after_days=N: 마지막 동기화가 N일보다 오래된 target 도 재동기화 대상에 포함.

    Parameters
    ----------
    source           : 수집기 이름
    collector        : 해당 수집기 인스턴스
    conn             : psycopg2 커넥션
    limit            : 이번 sync 에서 처리할 최대 건수
    pending_only     : 미수집 대상만 처리 (기본 True)
    force_resync     : 이미 수집된 대상도 강제 재수집 (기본 False)
    stale_after_days : N일 경과한 대상 재수집 (기본 None)
    """
    inserted = updated = unchanged = failed = 0
    sample_docs = []

    with conn.cursor() as cur:
        targets = get_sync_targets(
            cur, source, limit,
            force_resync=force_resync,
            pending_only=pending_only,
            stale_after_days=stale_after_days,
        )

    for target in targets:
        ext_id = target["external_id"]
        title = target["title"]

        try:
            # 상세 데이터 확보
            if collector.HAS_DETAIL_API:
                params = collector.build_detail_params(ext_id)
                detail = collector.fetch_detail(**params)
                collector.throttle()
            else:
                # 상세 API 없음 — list_payload 활용
                with conn.cursor() as cur:
                    detail = get_item_payload(cur, source, ext_id) or {}

            normalized_text, metadata = collector.normalize_detail(detail)
            raw_payload = collector.to_json_serializable(detail)

            with conn:
                with conn.cursor() as cur:
                    result = upsert_document(
                        cur, source, ext_id, title,
                        raw_payload, normalized_text, metadata,
                    )
                    mark_target_synced(cur, source, ext_id)

            if result == "inserted":
                inserted += 1
            elif result == "updated":
                updated += 1
            else:
                unchanged += 1

            if len(sample_docs) < 3:
                sample_docs.append({
                    "external_id": ext_id,
                    "title": title,
                    "result": result,
                })

        except Exception as exc:
            failed += 1
            logger.error("[%s] sync 실패 external_id=%s: %s", source, ext_id, exc)

    synced = inserted + updated + unchanged

    # 실행 후 기준 전체/잔여 카운트
    with conn.cursor() as cur:
        total_targets = count_targets(cur, source)
        pending = count_pending_targets(cur, source)

    logger.info(
        "[%s] sync 완료 — 처리 %d건 (신규 %d / 변경 %d / 동일 %d / 실패 %d), 잔여 pending %d건",
        source, synced, inserted, updated, unchanged, failed, pending,
    )

    return SyncResult(
        source=source,
        target_count=total_targets,
        pending_count=pending,
        synced_count=synced,
        inserted_count=inserted,
        updated_count=updated,
        unchanged_count=unchanged,
        failed_count=failed,
        sample_documents=sample_docs,
    )
