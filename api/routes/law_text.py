"""
법제처 법령 (law_text) 도메인 라우터.
prefix: /law_text
"""

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PgConn

from api.deps import get_db
from api.routes._common import register_common_routes
from api.schemas.requests import LawTextDiscoverRequest
from api.schemas.responses import DiscoverResponse
from collectors.law_text.collector import LawTextCollector
from services.discovery import discover

SOURCE = "law_text"
router = APIRouter(prefix="/law_text", tags=["법제처 법령 (law_text)"])


def _collector():
    return LawTextCollector()


@router.post("/discover", response_model=DiscoverResponse,
             summary="법제처 현행법령 목록 수집 → collection_items 저장")
def discover_law_text(
    req: LawTextDiscoverRequest,
    conn: PgConn = Depends(get_db),
):
    """
    법제처 현행법령 목록을 검색·수집해 `collection_items` 에 저장합니다.

    **검색 파라미터** (모두 선택 — 채운 값만 적용, 비우면 전체 조회)

    | 파라미터 | 설명 |
    |---|---|
    | `query` | 검색어 (법령명 또는 본문 키워드) |
    | `search` | 검색범위. **1=법령명**(기본), 2=본문검색 |
    | `display` / `page` | 페이지당 건수(최대 100) / 페이지 번호 |
    | `nw` | 연혁(1)/시행예정(2)/현행(3). 조합 가능 `1,3` |
    | `sort` | 정렬. efdes=시행일↓ / ddes=공포일↓ / ldes=법령명↓ 등 |
    | `ef_yd` | 시행일자 범위 `YYYYMMDD~YYYYMMDD` |
    | `anc_yd` / `anc_no` | 공포일자 범위 / 공포번호 범위 |
    | `date` / `nb` | 공포일자 / 공포번호 |
    | `rr_cls_cd` | 제개정종류 (300201=제정, 300202=일부개정 …) |
    | `org` | 소관부처코드 (law.go.kr 코드표 기준) |
    | `knd` | 법령종류 코드 |
    | `gana` | 사전식 검색 (ga, na, da …) |
    | `lid` | 법령ID |

    각 필드의 상세 설명은 아래 **Schema** 탭에서도 확인할 수 있습니다.
    """
    # fetch_list() 실제 인자로 매핑 (None=미사용 파라미터 제외)
    # → 이 dict 가 그대로 discovered_query 로 저장되어 실제 사용한 조건만 남는다
    api_params = {k: v for k, v in {
        "page":      req.page,
        "display":   req.display,
        "query":     req.query or None,
        "search":    req.search,
        "nw":        req.nw,
        "sort":      req.sort,
        "ef_yd":     req.ef_yd,
        "anc_yd":    req.anc_yd,
        "anc_no":    req.anc_no,
        "date":      req.date,
        "rr_cls_cd": req.rr_cls_cd,
        "nb":        req.nb,
        "org":       req.org,
        "knd":       req.knd,
        "gana":      req.gana,
        "lid":       req.lid,
    }.items() if v is not None}
    result = discover(SOURCE, _collector(), api_params, conn)
    return result.__dict__


register_common_routes(router, SOURCE, _collector)
