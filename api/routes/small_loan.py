"""
서민금융진흥원 대출상품 (small_loan) 도메인 라우터.
prefix: /small_loan

※ 대출상품 API 는 목록/상세가 분리되어 있지 않다 (HAS_DETAIL_API = False).
  단일 조회로 모든 필드가 반환되므로:
    - discover : 목록 조회 → collection_items 저장 (전체 필드 보존)
    - sync     : 별도 상세 API 호출 없이 collection_items.list_payload 를
                 그대로 normalize 하여 documents 에 저장
  3단계를 한 번에 실행하는 /collect_all 편의 엔드포인트를 추가로 제공한다.
"""

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PgConn

from api.deps import get_db
from api.routes._common import register_common_routes
from api.schemas.requests import SmallLoanDiscoverRequest, SyncRequest
from api.schemas.responses import DiscoverResponse, SyncResponse
from collectors.small_loan.collector import SmallLoanCollector
from services.discovery import discover
from services.targeting import register_targets
from services.sync import sync_details

SOURCE = "small_loan"
router = APIRouter(prefix="/small_loan", tags=["서민금융 대출상품 (small_loan)"])


def _collector():
    return SmallLoanCollector()


def _api_params(req: SmallLoanDiscoverRequest) -> dict:
    return {k: v for k, v in {
        "page":     req.page,
        "display":  req.display,
        "irt_ctg":  req.irt_ctg,
        "usge":     req.usge,
        "inst_ctg": req.inst_ctg,
        "rsd_area": req.rsd_area,
        "tgt_fltr": req.tgt_fltr,
        "prd_ctg":  req.prd_ctg,
    }.items() if v is not None}


@router.post("/discover", response_model=DiscoverResponse,
             summary="서민금융 대출상품 조회 → collection_items 저장 (상세 API 없음)")
def discover_small_loan(
    req: SmallLoanDiscoverRequest,
    conn: PgConn = Depends(get_db),
):
    """
    서민금융 대출상품을 검색·수집해 `collection_items` 에 저장합니다.
    (대출상품 API 는 목록/상세 미분리 — sync 는 이 payload 를 그대로 사용)

    **검색 파라미터** (대문자 API 파라미터로 자동 매핑)

    | 파라미터 | 설명 |
    |---|---|
    | `irt_ctg` | 금리구분 (IRT_CTG). 고정금리 / 변동금리 |
    | `usge` | 용도 (USGE). 생계 / 사업 / 주거 / 교육 |
    | `inst_ctg` | 기관구분 (INST_CTG). 공공기관 / 민간기업 |
    | `rsd_area` | 거주지역 (RSD_AREA_PAMT_EQLT_ISTM). 전국 / 서울 등 |
    | `tgt_fltr` | 대상 필터 (TGT_FLTR). 청년 / 저소득 / 근로자 등 |
    | `prd_ctg` | 상품구분 코드 (PRD_CTG) |
    | `display` / `page` | 페이지당 건수(전체 ~323건) / 페이지 번호 |

    각 필드의 상세 설명은 아래 **Schema** 탭에서도 확인할 수 있습니다.
    """
    result = discover(SOURCE, _collector(), _api_params(req), conn)
    return result.__dict__


@router.post("/collect_all", response_model=SyncResponse,
             summary="discover→targets→sync 일괄 실행 (대출상품 전용 편의 엔드포인트)")
def collect_all_small_loan(
    req: SmallLoanDiscoverRequest,
    conn: PgConn = Depends(get_db),
):
    """
    대출상품은 목록=상세이므로 3단계를 따로 호출할 실익이 적다.
    이 엔드포인트는 discover → targets(전체) → sync(조회분 전체) 를 순차 실행한다.
    """
    collector = _collector()
    disc = discover(SOURCE, collector, _api_params(req), conn)
    register_targets(SOURCE, conn, limit=None, register_all=True)
    result = sync_details(SOURCE, collector, conn,
                          limit=disc.fetched_count or 1, force_resync=True)
    return result.__dict__


register_common_routes(router, SOURCE, _collector)
