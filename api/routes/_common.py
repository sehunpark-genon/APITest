"""
도메인 라우터 공통 헬퍼.

targets / sync / items / documents 엔드포인트는 모든 도메인이 동일하므로
register_common_routes() 로 한 번에 등록한다.
discover 엔드포인트만 도메인별로 파라미터가 달라 각 모듈에서 개별 정의한다.
"""

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extensions import connection as PgConn

from api.deps import get_db
from api.schemas.requests import TargetRegisterRequest, SyncRequest
from api.schemas.responses import (
    TargetResponse, SyncResponse, ItemsResponse, TargetsResponse, DocumentResponse,
)
from db.items import (
    list_items, count_items, list_targets, count_targets, get_document,
)
from services.targeting import register_targets
from services.sync import sync_details


def _serialize(row: dict) -> dict:
    """datetime 등 직렬화 불가 값을 문자열로 변환."""
    return {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in row.items()}


def register_common_routes(
    router: APIRouter,
    source: str,
    collector_factory: Callable,
):
    """
    주어진 router 에 공통 엔드포인트 5종을 등록한다.

    Parameters
    ----------
    router            : 도메인 APIRouter (prefix/tags 가 이미 설정됨)
    source            : 수집기 source 이름 (DB 필터 키)
    collector_factory : 인자 없이 호출하면 수집기 인스턴스를 반환하는 함수
    """

    # ── Targeting ────────────────────────────────────────────────
    @router.post("/targets", response_model=TargetResponse,
                 summary="collection_items → collection_targets 등록")
    def register_targets_endpoint(
        req: TargetRegisterRequest,
        conn: PgConn = Depends(get_db),
    ):
        result = register_targets(
            source, conn,
            limit=req.limit,
            register_all=req.register_all,
            only_active_items=req.only_active_items,
        )
        return result.__dict__

    # ── Sync ─────────────────────────────────────────────────────
    @router.post("/sync", response_model=SyncResponse,
                 summary="collection_targets 기준 상세 조회 → documents 저장")
    def sync_endpoint(
        req: SyncRequest,
        conn: PgConn = Depends(get_db),
    ):
        collector = collector_factory()
        result = sync_details(
            source, collector, conn,
            limit=req.limit,
            pending_only=req.pending_only,
            force_resync=req.force_resync,
            stale_after_days=req.stale_after_days,
        )
        return result.__dict__

    # ── 조회: collection_items ───────────────────────────────────
    @router.get("/items", response_model=ItemsResponse,
                summary="collection_items 목록 조회")
    def get_items(
        status: str = Query(default="ACTIVE", description="상태 필터 (ACTIVE / INACTIVE)"),
        limit: int = Query(default=20, ge=1, le=200, description="페이지 크기"),
        offset: int = Query(default=0, ge=0, description="오프셋"),
        conn: PgConn = Depends(get_db),
    ):
        with conn.cursor() as cur:
            total = count_items(cur, source, status)
            items = list_items(cur, source, status, limit, offset)
        return {"source": source, "total": total,
                "items": [_serialize(i) for i in items]}

    # ── 조회: collection_targets ─────────────────────────────────
    @router.get("/targets", response_model=TargetsResponse,
                summary="collection_targets 목록 조회")
    def get_targets(
        status: str = Query(default="ACTIVE"),
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        conn: PgConn = Depends(get_db),
    ):
        with conn.cursor() as cur:
            total = count_targets(cur, source, status)
            targets = list_targets(cur, source, status, limit, offset)
        return {"source": source, "total": total,
                "targets": [_serialize(t) for t in targets]}

    # ── 조회: documents 상세 ─────────────────────────────────────
    @router.get("/documents/{external_id}", response_model=DocumentResponse,
                summary="documents 상세 조회 (정제 텍스트 + 원본 payload)")
    def get_document_endpoint(
        external_id: str,
        conn: PgConn = Depends(get_db),
    ):
        with conn.cursor() as cur:
            doc = get_document(cur, source, external_id)
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"[{source}] external_id={external_id} 문서를 찾을 수 없습니다.",
            )
        return {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in doc.items()}
