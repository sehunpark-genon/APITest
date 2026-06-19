"""
DMZ 수집 파이프라인 API
-----------------------
FastAPI 애플리케이션 진입점.

실행:
    uv run uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

Swagger UI:
    http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI

from api.routes.law_text import router as law_text_router
from api.routes.precedent import router as precedent_router
from api.routes.welfare_central import router as welfare_central_router
from api.routes.welfare_local import router as welfare_local_router
from api.routes.small_loan import router as small_loan_router
from db.schema import ensure_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _init_db():
    ensure_schema()
    logger.info("DB 스키마 확인/생성 완료")


app = FastAPI(
    title="DMZ 수집 파이프라인 API",
    description="""
외부 공공 API 5종을 수집해 PostgreSQL에 적재하는 **DMZ 수집 PoC**.
도메인이 달라도 저장 구조와 흐름은 공통입니다.

## 3단계 파이프라인

| 단계 | 엔드포인트 | 하는 일 |
|------|-----------|--------|
| ① Discovery | `POST /{domain}/discover` | 목록 API 호출 → `collection_items` 저장 |
| ② Targeting | `POST /{domain}/targets` | 수집분 중 계속 챙길 것 → `collection_targets` 등록 |
| ③ Sync | `POST /{domain}/sync` | 상세 API 호출 → `documents` 저장 (+변경 감지) |
| 조회 | `GET /{domain}/items · /targets · /documents/{external_id}` | 각 테이블 조회 |

데이터는 항상 `collection_items → collection_targets → documents → document_versions` 순으로 흐릅니다.

## 꼭 알아둘 개념

- **저장 단위 = 항목 1건** (`source` + `external_id`). 예: `근로기준법` / `근로기준법 시행령` /
  `근로기준법 시행규칙`은 **법적으로 별개 법령**이라 각각 1행. "근로기준법" 검색 시 매칭된 건수만큼 행이 생깁니다.
- **중복 안 쌓임**: 같은 항목을 다시 수집하면 새로 만들지 않고 그 행을 **갱신(upsert)** 합니다 (`UNIQUE(source, external_id)`).
- **원본 보존**: 목록 응답 전체는 `list_payload`, 상세 응답 원본은 `raw_payload`에 그대로 저장합니다.
  자주 쓰는 `external_id`·`title`만 별도 컬럼으로 꺼내둔 것뿐입니다.
- **변경 감지(diff)**: sync 시 `normalized_text`의 **SHA256(`content_hash`)** 를 기존과 비교 →
  신규=insert / 동일=unchanged / 변경=옛 버전을 `document_versions`에 보존 후 update(version+1).
  이미 수집한 문서를 **다시 검사하려면 `force_resync=true`** 로 호출하세요.
- **`limit` 의미**: "잘라 버리는" 게 아니라 **한 번에 처리할 배치 크기**입니다.
  미수집(pending) 대상부터 처리하며, 더 처리하려면 `limit`을 올리거나 반복 호출하면 됩니다.

## 도메인

| Prefix | 대상 | 목록/상세 |
|--------|------|:---:|
| `/law_text` | 법제처 현행법령 | 분리 |
| `/precedent` | 법제처 판례 | 분리 |
| `/welfare_central` | 복지로 중앙부처 복지서비스 | 분리 |
| `/welfare_local` | 복지로 지자체 복지서비스 | 분리 |
| `/small_loan` | 서민금융 대출상품 | **미분리** (sync는 `list_payload` 재사용, `/small_loan/collect_all`로 일괄 실행) |

> **참고**: `status`(ACTIVE/INACTIVE) 컬럼은 마련돼 있으나 **비활성화 정책 미정으로 현재 미구현** —
> 모든 행은 ACTIVE로만 동작합니다. 각 필드의 상세 설명은 아래 엔드포인트의 **Schema** 탭과 요청 설명 표를 참고하세요.
""",
    version="0.3.0",
)

for r in (law_text_router, precedent_router,
          welfare_central_router, welfare_local_router, small_loan_router):
    app.include_router(r)


@app.on_event("startup")
def startup():
    _init_db()


@app.get("/health", tags=["상태"])
def health():
    return {"status": "ok"}
