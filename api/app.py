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
API 도메인별로 그룹화된 3단계 수집 파이프라인.

## 3단계 수집 파이프라인 (도메인 공통)

| 단계 | 엔드포인트 | 설명 |
|------|-----------|------|
| 1. Discovery | `POST /{domain}/discover` | 목록 API 호출 → `collection_items` 저장 |
| 2. Targeting | `POST /{domain}/targets` | `collection_items` → `collection_targets` 등록 |
| 3. Sync | `POST /{domain}/sync` | 상세 API 호출 → `documents` 저장 |
| 조회 | `GET /{domain}/items` · `/targets` · `/documents/{external_id}` | 각 테이블 조회 |

## 도메인

- **/law_text** — 법제처 법령 (목록·상세 분리)
- **/precedent** — 법제처 판례 (목록·상세 분리)
- **/welfare_central** — 복지로 중앙부처 복지서비스 (목록·상세 분리)
- **/welfare_local** — 복지로 지자체 복지서비스 (목록·상세 분리)
- **/small_loan** — 서민금융 대출상품 (목록·상세 미분리 — sync 는 list_payload 재사용,
  `/small_loan/collect_all` 로 3단계 일괄 실행 가능)
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
