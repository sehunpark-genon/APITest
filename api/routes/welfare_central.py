"""
복지로 중앙부처 복지서비스 (welfare_central) 도메인 라우터.
prefix: /welfare_central
"""

from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as PgConn

from api.deps import get_db
from api.routes._common import register_common_routes
from api.schemas.requests import WelfareCentralDiscoverRequest
from api.schemas.responses import DiscoverResponse
from collectors.welfare.central_collector import WelfareCentralCollector
from services.discovery import discover

SOURCE = "welfare_central"
router = APIRouter(prefix="/welfare_central", tags=["복지로 중앙부처 (welfare_central)"])


def _collector():
    return WelfareCentralCollector()


@router.post("/discover", response_model=DiscoverResponse,
             summary="복지로 중앙부처 복지서비스 목록 수집 → collection_items 저장")
def discover_welfare_central(
    req: WelfareCentralDiscoverRequest,
    conn: PgConn = Depends(get_db),
):
    """
    복지로 중앙부처 복지서비스 목록을 검색·수집해 `collection_items` 에 저장합니다.

    **검색 파라미터**

    | 파라미터 | 설명 |
    |---|---|
    | `srch_key_code` | 검색분류(필수). **001=제목**, 002=내용, 003=제목+내용 |
    | `search_word` | 검색어. 비우면 전체 조회 |
    | `display` / `page` | 페이지당 건수(최대 500) / 페이지 번호 |
    | `life_array` | 생애주기 코드 (콤마 구분 복수 선택) |
    | `target_group` | 가구유형 코드. 001=장애인 002=국가보훈 003=한부모 등 |
    | `intr_thema` | 관심주제 코드 (콤마 구분) |
    | `age` | 나이 (세) |
    | `online_apply_yn` | 온라인신청 가능여부. Y / N |
    | `order_by` | 정렬. **date=조회순**(기본), popular=인기순 |

    각 필드의 상세 설명은 아래 **Schema** 탭에서도 확인할 수 있습니다.
    """
    # None=미사용 파라미터 제외 → 실제 사용한 검색 조건만 discovered_query 로 저장
    api_params = {k: v for k, v in {
        "page":            req.page,
        "display":         req.display,
        "srch_key_code":   req.srch_key_code,
        "search_word":     req.search_word,
        "life_array":      req.life_array,
        "target_group":    req.target_group,
        "intr_thema":      req.intr_thema,
        "age":             req.age,
        "online_apply_yn": req.online_apply_yn,
        "order_by":        req.order_by,
    }.items() if v is not None}
    result = discover(SOURCE, _collector(), api_params, conn)
    return result.__dict__


register_common_routes(router, SOURCE, _collector)
