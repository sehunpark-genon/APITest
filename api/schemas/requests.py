"""
수집 파이프라인 API — 도메인별 요청 스키마 (Pydantic v2).

각 도메인 API 의 실제 요청 파라미터를 1:1 로 노출해 Swagger 에서 그대로 보이도록 한다.
모든 필드에 description 을 달아 Swagger UI 에서 의미를 즉시 확인할 수 있다.
필수 고정값(serviceKey, OC, target, type, callTp 등)은 수집기 내부에서 자동 주입하므로
요청 본문에는 포함하지 않는다.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# 법제처 법령 (law_text) — lawSearch.do target=law
# ══════════════════════════════════════════════════════════════════════════════

class LawTextDiscoverRequest(BaseModel):
    """법제처 현행법령 목록 조회 파라미터."""

    page: int = Field(default=1, ge=1, description="페이지 번호 (기본 1)")
    display: int = Field(default=20, ge=1, le=100,
                         description="페이지당 결과 수 (기본 20, 최대 100)")
    query: Optional[str] = Field(
        default=None,
        description="검색어 (법령명 또는 본문 키워드). 빈 값이면 전체 조회.",
        examples=["근로기준법"],
    )
    search: int = Field(
        default=1,
        description="검색범위. 1=법령명(기본), 2=본문검색",
        examples=[1],
    )
    nw: Optional[str] = Field(
        default=None,
        description="연혁/시행예정/현행 구분. 1=연혁, 2=시행예정, 3=현행 (생략 시 전체). 조합 가능 예: '1,3'",
        examples=["3"],
    )
    sort: Optional[str] = Field(
        default=None,
        description="정렬옵션. lasc=법령오름차순 / ldes=법령내림차순 / "
                    "dasc·ddes=공포일자 / nasc·ndes=공포번호 / efasc·efdes=시행일자",
        examples=["efdes"],
    )
    ef_yd: Optional[str] = Field(
        default=None,
        description="시행일자 범위 검색 (efYd). 형식 'YYYYMMDD~YYYYMMDD'",
        examples=["20090101~20090130"],
    )
    anc_yd: Optional[str] = Field(
        default=None,
        description="공포일자 범위 검색 (ancYd). 형식 'YYYYMMDD~YYYYMMDD'",
    )
    anc_no: Optional[str] = Field(
        default=None,
        description="공포번호 범위 검색 (ancNo). 예: '306~400'",
    )
    date: Optional[str] = Field(
        default=None,
        description="공포일자 단일 검색 (YYYYMMDD)",
    )
    rr_cls_cd: Optional[str] = Field(
        default=None,
        description="제개정 종류 코드 (rrClsCd). 300201=제정 300202=일부개정 "
                    "300203=전부개정 300204=폐지 300209=타법개정 등",
    )
    nb: Optional[str] = Field(default=None, description="공포번호 검색 (숫자)")
    org: Optional[str] = Field(
        default=None,
        description="소관부처 코드 (law.go.kr 소관부처코드 표 기준). "
                    "※ data.go.kr 부처코드와 다를 수 있으니 법제처 코드표 값을 사용",
    )
    knd: Optional[str] = Field(default=None, description="법령종류 코드 (법제처 코드표 참조)")
    gana: Optional[str] = Field(default=None, description="사전식 검색 (ga, na, da …)")
    lid: Optional[str] = Field(default=None, description="법령ID (LID). 예: '830'")
    # ※ 모델 레벨 example 을 두지 않는다 — FastAPI 가 None 값을 제거해 일부 필터가
    #   사라지기 때문. example 없이 두면 Swagger 가 스키마의 모든 필드로 본문 예시를
    #   생성하므로, 위 필터 전부가 노출되어 사용자가 직접 채워 검색할 수 있다.


# ══════════════════════════════════════════════════════════════════════════════
# 법제처 판례 (precedent) — lawSearch.do target=prec
# ══════════════════════════════════════════════════════════════════════════════

class PrecedentDiscoverRequest(BaseModel):
    """법제처 판례 목록 조회 파라미터."""

    page: int = Field(default=1, ge=1, description="페이지 번호 (기본 1)")
    display: int = Field(default=20, ge=1, le=100,
                         description="페이지당 결과 수 (기본 20, 최대 100)")
    query: Optional[str] = Field(
        default=None,
        description="검색어 (사건명 또는 본문 키워드). 빈 값이면 전체 조회.",
        examples=["손해배상"],
    )
    search: int = Field(
        default=1,
        description="검색범위. 1=판례명(기본), 2=본문검색",
        examples=[1],
    )
    court_org: Optional[str] = Field(
        default=None,
        description="법원종류 코드 (org). 400201=대법원, 400202=하위법원",
        examples=["400201"],
    )
    court_name: Optional[str] = Field(
        default=None,
        description="법원명 (curt). 예: '대법원', '서울고등법원', '광주지법'",
        examples=["대법원"],
    )
    ref_law: Optional[str] = Field(
        default=None,
        description="참조법령명 (JO). 예: '형법', '민법'",
        examples=["민법"],
    )
    gana: Optional[str] = Field(default=None, description="사전식 검색 (ga, na, da …)")
    sort: Optional[str] = Field(
        default=None,
        description="정렬옵션. lasc·ldes=사건명 / dasc·ddes=선고일자(ddes 기본) / nasc·ndes=법원명",
        examples=["ddes"],
    )
    date: Optional[str] = Field(default=None, description="선고일자 단일 검색 (YYYYMMDD)")
    prnc_yd: Optional[str] = Field(
        default=None,
        description="선고일자 범위 검색 (prncYd). 형식 'YYYYMMDD~YYYYMMDD'",
        examples=["20090101~20090130"],
    )
    case_no: Optional[str] = Field(
        default=None,
        description="판례 사건번호 (nb). 예: '2024다12345'",
    )
    data_src_nm: Optional[str] = Field(
        default=None,
        description="데이터출처명 (datSrcNm). 예: '국세법령정보시스템', '대법원'",
    )
    prec_type: Optional[str] = Field(
        default=None,
        description="판결유형 (precType). 판결 / 결정 / 명령",
        examples=["판결"],
    )
    # ※ 모델 레벨 example 없음 — Swagger 가 모든 필드로 본문 예시 자동 생성 (위 law_text 참고)


# ══════════════════════════════════════════════════════════════════════════════
# 복지로 중앙부처 (welfare_central) — NationalWelfarelistV001 (callTp=L)
# ══════════════════════════════════════════════════════════════════════════════

class WelfareCentralDiscoverRequest(BaseModel):
    """복지로 중앙부처 복지서비스 목록 조회 파라미터."""

    page: int = Field(default=1, ge=1, description="페이지 번호 (pageNo, 기본 1, 최대 1000)")
    display: int = Field(default=10, ge=1, le=500,
                         description="페이지당 결과 수 (numOfRows, 기본 10, 최대 500)")
    srch_key_code: str = Field(
        default="001",
        description="검색분류 (srchKeyCode, 필수). 001=제목 002=내용 003=제목+내용",
        examples=["001"],
    )
    search_word: Optional[str] = Field(
        default=None,
        description="검색어 (searchWrd). 빈 값이면 전체 조회.",
        examples=["임산부"],
    )
    life_array: Optional[str] = Field(
        default=None,
        description="생애주기 코드 (lifeArray, 콤마 구분 복수 선택). 코드표 참조",
        examples=["001"],
    )
    target_group: Optional[str] = Field(
        default=None,
        description="가구유형 코드 (trgterIndvdlArray, 콤마 구분). 001=장애인 002=국가보훈 003=한부모 등",
    )
    intr_thema: Optional[str] = Field(
        default=None,
        description="관심주제 코드 (intrsThemaArray, 콤마 구분)",
    )
    age: Optional[int] = Field(default=None, description="나이 (age, 단위: 세)")
    online_apply_yn: Optional[str] = Field(
        default=None,
        description="온라인신청 가능여부 (onapPsbltYn). Y=가능 N=불가능",
        examples=["Y"],
    )
    order_by: Optional[str] = Field(
        default="date",
        description="정렬순서 (orderBy). date=조회순(기본), popular=인기순",
        examples=["date"],
    )
    # ※ 모델 레벨 example 없음 — Swagger 가 모든 필드로 본문 예시 자동 생성 (위 law_text 참고)


# ══════════════════════════════════════════════════════════════════════════════
# 복지로 지자체 (welfare_local) — LcgvWelfarelist
# ══════════════════════════════════════════════════════════════════════════════

class WelfareLocalDiscoverRequest(BaseModel):
    """복지로 지자체 복지서비스 목록 조회 파라미터."""

    page: int = Field(default=1, ge=1, description="페이지 시작위치 (pageNo, 기본 1)")
    display: int = Field(default=10, ge=1, le=500,
                         description="출력 건수 (numOfRows, 기본 10)")
    region_name: Optional[str] = Field(
        default=None,
        description="시도명 (ctpvNm). ※코드가 아닌 이름! 예: '서울특별시', '경기도'",
        examples=["서울특별시"],
    )
    city_name: Optional[str] = Field(
        default=None,
        description="시군구명 (sggNm). ※이름! 예: '강남구', '수원시'",
        examples=["강남구"],
    )
    srch_key_code: Optional[str] = Field(
        default=None,
        description="검색분류 (srchKeyCode). 001=제목 002=내용 003=제목+내용",
    )
    search_word: Optional[str] = Field(
        default=None,
        description="검색어 (searchWrd)",
        examples=["청년"],
    )
    life_array: Optional[str] = Field(
        default=None,
        description="생애주기 코드 (lifeArray, 콤마 구분)",
    )
    target_group: Optional[str] = Field(
        default=None,
        description="가구상황 코드 (trgterIndvdlArray, 콤마 구분)",
    )
    intr_thema: Optional[str] = Field(
        default=None,
        description="관심주제 코드 (intrsThemaArray, 콤마 구분)",
    )
    age: Optional[int] = Field(default=None, description="나이 (age, 단위: 세)")
    sort_order: Optional[str] = Field(
        default=None,
        description="정렬순서 (arrgOrd). API 문서 참조",
    )
    # ※ 모델 레벨 example 없음 — Swagger 가 모든 필드로 본문 예시 자동 생성 (위 law_text 참고)


# ══════════════════════════════════════════════════════════════════════════════
# 서민금융진흥원 대출상품 (small_loan) — getLoanProductSearchingInfo
# ※ 목록/상세 미분리 — 단일 조회로 전체 필드 반환
# ══════════════════════════════════════════════════════════════════════════════

class SmallLoanDiscoverRequest(BaseModel):
    """서민금융진흥원 대출상품 조회 파라미터. (대문자 API 파라미터로 자동 매핑)"""

    page: int = Field(default=1, ge=1, description="페이지 번호 (pageNo, 기본 1)")
    display: int = Field(default=20, ge=1, le=500,
                         description="페이지당 결과 수 (numOfRows). 전체 ~323건")
    irt_ctg: Optional[str] = Field(
        default=None,
        description="금리구분 (IRT_CTG). 고정금리 / 변동금리",
        examples=["고정금리"],
    )
    usge: Optional[str] = Field(
        default=None,
        description="용도(자금목적) (USGE). 생계 / 사업 / 주거 / 교육",
        examples=["생계"],
    )
    inst_ctg: Optional[str] = Field(
        default=None,
        description="기관구분 (INST_CTG). 공공기관 / 민간기업",
        examples=["공공기관"],
    )
    rsd_area: Optional[str] = Field(
        default=None,
        description="거주지역 (RSD_AREA_PAMT_EQLT_ISTM). 전국 / 서울 / 경기 등",
        examples=["전국"],
    )
    tgt_fltr: Optional[str] = Field(
        default=None,
        description="대상 필터 (TGT_FLTR). 청년 / 저소득 / 근로자 등",
        examples=["청년"],
    )
    prd_ctg: Optional[str] = Field(
        default=None,
        description="상품구분 코드 (PRD_CTG). API 문서 참조",
    )
    # ※ 모델 레벨 example 없음 — Swagger 가 모든 필드로 본문 예시 자동 생성 (위 law_text 참고)


# ══════════════════════════════════════════════════════════════════════════════
# 공통 — Targeting / Sync (모든 도메인 동일)
# ══════════════════════════════════════════════════════════════════════════════

class TargetRegisterRequest(BaseModel):
    """collection_items → collection_targets 등록 파라미터."""

    register_all: bool = Field(
        default=False,
        description="True=collection_items 전체를 targets 로 등록(이미 등록된 것 포함 재등록). "
                    "False=아직 targets 에 없는 신규 항목만 등록(기본).",
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description="등록할 최대 건수(테스트용). 미설정 시 조건을 만족하는 전체 등록.",
        examples=[100],
    )
    only_active_items: bool = Field(
        default=True,
        description="True=status='ACTIVE' 인 collection_items 만 대상(기본). False=모든 상태 포함.",
    )


class SyncRequest(BaseModel):
    """collection_targets → 상세 조회 → documents 동기화 파라미터."""

    limit: int = Field(
        default=5,
        ge=1,
        le=500,
        description="이번 sync 에서 처리할 최대 건수.",
        examples=[10],
    )
    pending_only: bool = Field(
        default=True,
        description="True=아직 상세 수집 안 된 pending 대상만 처리(기본). "
                    "documents 에 없거나 last_detail_collected_at 이 NULL 인 target 우선.",
    )
    force_resync: bool = Field(
        default=False,
        description="True=이미 동기화된 대상도 상세 API 를 다시 호출. "
                    "content_hash 비교로 동일하면 unchanged, 다르면 updated 처리.",
    )
    stale_after_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="마지막 동기화가 N일보다 오래된 대상도 재동기화 대상에 포함.",
        examples=[7],
    )
