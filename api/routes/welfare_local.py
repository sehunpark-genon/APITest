"""
복지로 지자체 복지서비스 (welfare_local) 도메인 라우터.
prefix: /welfare_local
"""

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PgConn

from api.deps import get_db
from api.routes._common import register_common_routes
from api.schemas.requests import WelfareLocalDiscoverRequest
from api.schemas.responses import DiscoverResponse
from collectors.welfare.local_collector import WelfareLocalCollector
from services.discovery import discover

SOURCE = "welfare_local"
router = APIRouter(prefix="/welfare_local", tags=["복지로 지자체 (welfare_local)"])


def _collector():
    return WelfareLocalCollector()


@router.post("/discover", response_model=DiscoverResponse,
             summary="복지로 지자체 복지서비스 목록 수집 → collection_items 저장")
def discover_welfare_local(
    req: WelfareLocalDiscoverRequest,
    conn: PgConn = Depends(get_db),
):
    """
    복지로 지자체 복지서비스 목록을 검색·수집해 `collection_items` 에 저장합니다.

    **검색 파라미터**

    | 파라미터 | 설명 |
    |---|---|
    | `region_name` | 시도명. ※코드 아닌 **이름**! 예: 서울특별시, 경기도 |
    | `city_name` | 시군구명. ※이름! 예: 강남구, 수원시 |
    | `search_word` | 검색어 |
    | `srch_key_code` | 검색분류. 001=제목 002=내용 003=제목+내용 |
    | `display` / `page` | 출력 건수(최대 500) / 페이지 시작위치 |
    | `life_array` | 생애주기 코드 (콤마 구분) |
    | `target_group` | 가구상황 코드 (콤마 구분) |
    | `intr_thema` | 관심주제 코드 (콤마 구분) |
    | `age` | 나이 (세) |
    | `sort_order` | 정렬순서 (arrgOrd) |

    각 필드의 상세 설명은 아래 **Schema** 탭에서도 확인할 수 있습니다.
    """
    # None=미사용 파라미터 제외 → 실제 사용한 검색 조건만 discovered_query 로 저장
    api_params = {k: v for k, v in {
        "page":          req.page,
        "display":       req.display,
        "region_name":   req.region_name,
        "city_name":     req.city_name,
        "srch_key_code": req.srch_key_code,
        "search_word":   req.search_word,
        "life_array":    req.life_array,
        "target_group":  req.target_group,
        "intr_thema":    req.intr_thema,
        "age":           req.age,
        "sort_order":    req.sort_order,
    }.items() if v is not None}
    result = discover(SOURCE, _collector(), api_params, conn)
    return result.__dict__


register_common_routes(router, SOURCE, _collector)
