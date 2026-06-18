"""
법제처 판례 (precedent) 도메인 라우터.
prefix: /precedent
"""

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PgConn

from api.deps import get_db
from api.routes._common import register_common_routes
from api.schemas.requests import PrecedentDiscoverRequest
from api.schemas.responses import DiscoverResponse
from collectors.precedent.collector import PrecedentCollector
from services.discovery import discover

SOURCE = "precedent"
router = APIRouter(prefix="/precedent", tags=["법제처 판례 (precedent)"])


def _collector():
    return PrecedentCollector()


@router.post("/discover", response_model=DiscoverResponse,
             summary="법제처 판례 목록 수집 → collection_items 저장")
def discover_precedent(
    req: PrecedentDiscoverRequest,
    conn: PgConn = Depends(get_db),
):
    """
    법제처 판례 목록을 검색·수집해 `collection_items` 에 저장합니다.

    **검색 파라미터** (모두 선택 — 채운 값만 적용, 비우면 전체 조회)

    | 파라미터 | 설명 |
    |---|---|
    | `query` | 검색어 (사건명 또는 본문 키워드) |
    | `search` | 검색범위. **1=판례명**(기본), 2=본문검색 |
    | `display` / `page` | 페이지당 건수(최대 100) / 페이지 번호 |
    | `court_org` | 법원종류코드. 400201=대법원, 400202=하위법원 |
    | `court_name` | 법원명. 예: 대법원, 서울고등법원, 광주지법 |
    | `ref_law` | 참조법령명. 예: 형법, 민법 |
    | `sort` | 정렬. ddes=선고일↓(기본) / lasc=사건명↑ / nasc=법원명↑ 등 |
    | `date` / `prnc_yd` | 선고일자 / 선고일자 범위 `YYYYMMDD~YYYYMMDD` |
    | `case_no` | 사건번호. 예: 2024다12345 |
    | `data_src_nm` | 데이터출처명. 예: 국세법령정보시스템, 대법원 |
    | `prec_type` | 판결유형. 판결 / 결정 / 명령 |
    | `gana` | 사전식 검색 (ga, na, da …) |

    각 필드의 상세 설명은 아래 **Schema** 탭에서도 확인할 수 있습니다.
    """
    # None=미사용 파라미터 제외 → 실제 사용한 검색 조건만 discovered_query 로 저장
    api_params = {k: v for k, v in {
        "page":        req.page,
        "display":     req.display,
        "query":       req.query or None,
        "search":      req.search,
        "court_org":   req.court_org,
        "court_name":  req.court_name,
        "ref_law":     req.ref_law,
        "gana":        req.gana,
        "sort":        req.sort,
        "date":        req.date,
        "prnc_yd":     req.prnc_yd,
        "case_no":     req.case_no,
        "data_src_nm": req.data_src_nm,
        "prec_type":   req.prec_type,
    }.items() if v is not None}
    result = discover(SOURCE, _collector(), api_params, conn)
    return result.__dict__


register_common_routes(router, SOURCE, _collector)
