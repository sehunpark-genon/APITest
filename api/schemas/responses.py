"""
수집 파이프라인 API — 응답 스키마 (Pydantic v2).

requests.py 와 동일하게 모든 필드에 description 을 달아
Swagger UI 의 응답 스키마에서 의미를 즉시 확인할 수 있도록 한다.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# Discovery — POST /{domain}/discover
# ══════════════════════════════════════════════════════════════════════════════

class DiscoverResponse(BaseModel):
    """Discovery 결과 — 목록 API 호출 → collection_items 저장 결과."""

    source: str = Field(description="수집 도메인 (law_text / precedent / ...)")
    requested_filters: dict = Field(
        description="실제로 API 에 전달한 검색 조건 (None 인 미사용 파라미터는 제외)")
    fetched_count: int = Field(description="목록 API 에서 수신한 항목 수")
    inserted_count: int = Field(description="collection_items 에 신규 저장된 건수")
    updated_count: int = Field(description="기존 항목이 갱신된 건수")
    skipped_count: int = Field(description="식별자(external_id) 누락 등으로 건너뛴 건수")
    sample_items: list[dict] = Field(
        description="수신 항목 미리보기 (external_id + title, 최대 3건)")
    message: str = Field(description="처리 요약 메시지")


# ══════════════════════════════════════════════════════════════════════════════
# Targeting — POST /{domain}/targets
# ══════════════════════════════════════════════════════════════════════════════

class TargetResponse(BaseModel):
    """Targeting 결과 — collection_items → collection_targets 등록 결과."""

    source: str = Field(description="수집 도메인")
    registered_count: int = Field(description="이번에 신규로 targets 에 등록된 건수")
    skipped_count: int = Field(description="이미 등록되어 있어 건너뛴 건수")
    target_count: int = Field(description="등록 후 전체 ACTIVE target 수")
    sample_targets: list[dict] = Field(description="등록된 target 미리보기 (최대 3건)")


# ══════════════════════════════════════════════════════════════════════════════
# Sync — POST /{domain}/sync
# ══════════════════════════════════════════════════════════════════════════════

class SyncResponse(BaseModel):
    """Sync 결과 — collection_targets → 상세 조회 → documents 저장 결과."""

    source: str = Field(description="수집 도메인")
    target_count: int = Field(description="전체 ACTIVE target 수")
    pending_count: int = Field(
        description="실행 후 아직 상세 수집이 안 된 잔여 target 수 "
                    "(last_detail_collected_at 이 NULL 이거나 documents 행 없음)")
    synced_count: int = Field(
        description="이번 실행에서 처리된 건수 (= inserted + updated + unchanged)")
    inserted_count: int = Field(description="documents 에 신규 저장된 건수")
    updated_count: int = Field(description="content_hash 변경으로 갱신된 건수 (이전 버전은 이력 보존)")
    unchanged_count: int = Field(description="content_hash 동일 — 변경 없음으로 처리된 건수")
    failed_count: int = Field(description="상세 조회/저장 중 실패한 건수")
    sample_documents: list[dict] = Field(
        description="처리된 문서 미리보기 (external_id + title + result, 최대 3건)")


# ══════════════════════════════════════════════════════════════════════════════
# 조회 — GET /{domain}/items · /targets · /documents/{external_id}
# ══════════════════════════════════════════════════════════════════════════════

class ItemsResponse(BaseModel):
    """collection_items 목록 조회 결과."""

    source: str = Field(description="수집 도메인")
    total: int = Field(description="해당 상태(status)의 전체 collection_items 수")
    items: list[dict] = Field(
        description="collection_items 행 목록 (list_payload, discovered_query 포함)")


class TargetsResponse(BaseModel):
    """collection_targets 목록 조회 결과."""

    source: str = Field(description="수집 도메인")
    total: int = Field(description="해당 상태(status)의 전체 collection_targets 수")
    targets: list[dict] = Field(
        description="collection_targets 행 목록 (collect_detail, last_detail_collected_at 포함)")


class DocumentResponse(BaseModel):
    """documents 상세 조회 결과 — 정제 문서 1건."""

    source: str = Field(description="수집 도메인")
    external_id: str = Field(description="API 식별자 (법령일련번호/servId/seq 등)")
    title: Optional[str] = Field(description="문서 제목")
    content_hash: Optional[str] = Field(
        description="normalized_text 의 SHA256 해시 (변경 감지 기준)")
    version: int = Field(description="문서 버전 (변경 시 1씩 증가)")
    normalized_text: Optional[str] = Field(description="RAG/검색용 정제 텍스트")
    metadata: Optional[dict] = Field(description="주요 메타 필드 (제목/부처/일자 등)")
    raw_payload: dict = Field(description="상세 API 응답 원본 전체 (필드 누락 없이 보존)")
    created_at: Any = Field(description="최초 저장 시각")
    updated_at: Any = Field(description="마지막 갱신 시각")
