"""
서민금융진흥원 API — 대출상품한눈에 정보조회 서비스 수집기
===========================================================
API 출처 : 공공데이터포털 data.go.kr
제공기관 : 서민금융진흥원 (kinfa.or.kr)
업데이트 주기 : 연 1회 (총 ~323건 상품)

수집 흐름
---------
목록 조회 1단계로 충분 — 별도 상세 조회 API 없음
pageNo + numOfRows 로 페이지네이션하며 전체 상품 수집 가능

필터 옵션 사용법
--------------
fetch_list() 의 선택 파라미터로 특정 대출상품만 추출할 수 있다.
예:
  fetch_list(irt_ctg="고정금리")
  → 고정금리 상품만 조회

  fetch_list(usge="생계", inst_ctg="공공기관")
  → 공공기관 취급 생계자금 대출상품만 조회

  fetch_list(tgt_fltr="청년")
  → 청년 대상 상품만 조회
"""

import logging

from collectors.base import BaseCollector
from config.settings import (
    COLLECT_PAGE_SIZE,
    PUBLIC_API_KEY,
    SMALL_LOAN_URL,
)

logger = logging.getLogger(__name__)


class SmallLoanCollector(BaseCollector):
    SOURCE_NAME = "small_loan"

    # ──────────────────────────────────────────────────────────
    # 1. 목록 조회
    # ──────────────────────────────────────────────────────────

    def fetch_list(
        self,
        page: int = 1,
        display: int = None,
        irt_ctg: str = None,
        usge: str = None,
        inst_ctg: str = None,
        rsd_area: str = None,
        tgt_fltr: str = None,
        prd_ctg: str = None,
    ) -> list[dict]:
        """
        서민 대출상품 목록 조회.

        ┌─────────────────────────────────────────────────────────────────────┐
        │  GET https://apis.data.go.kr/B553701/LoanProductSearchingInfo/     │
        │      LoanProductSearchingInfo/getLoanProductSearchingInfo          │
        │  ※ 경로 LoanProductSearchingInfo 가 두 번 반복되는 구조 (정상)        │
        └─────────────────────────────────────────────────────────────────────┘

        ※ 대출상품 API 는 목록/상세가 분리되어 있지 않다.
          단일 조회로 모든 상품 필드를 반환하므로 별도 상세 조회 API 가 없다.
          (HAS_DETAIL_API = False — sync 단계는 목록 payload 를 그대로 사용)

        요청 파라미터
        ─────────────
        serviceKey      (필수) 공공데이터포털 인증키
        pageNo          (필수) 페이지 번호 (1부터)
        numOfRows       (필수) 페이지당 결과 수 (display 인자로 조정)

        irt_ctg   → IRT_CTG   (선택) 금리구분 필터
                                      예: '고정금리', '변동금리'
        usge      → USGE      (선택) 용도(자금목적) 필터
                                      예: '생계', '사업', '주거', '교육'
        inst_ctg  → INST_CTG  (선택) 기관구분 필터
                                      예: '공공기관', '민간기업'
        rsd_area  → RSD_AREA_PAMT_EQLT_ISTM (선택) 거주지역 필터
                                      예: '전국', '서울', '경기'
        tgt_fltr  → TGT_FLTR  (선택) 대상 필터
                                      예: '청년', '저소득', '근로자'
        prd_ctg   → PRD_CTG   (선택) 상품구분 코드
                                      ※ 유효 값은 API 문서 참조

        ※ 파라미터명이 대문자인 것 주의 (IRT_CTG, USGE, INST_CTG 등)

        응답 구조 (XML → xmltodict → dict)
        ────────────────────────────────
        response
          ├─ header
          │    ├─ resultCode    결과 코드 (00 = 정상)
          │    └─ resultMsg     결과 메시지 (NORMAL SERVICE.)
          └─ body
               ├─ totalCount    전체 상품 수 (예: 323)
               ├─ pageNo        현재 페이지
               ├─ numOfRows     요청 건수
               └─ items
                    └─ item[]   상품 목록
                         ├─ seq              상품 고유번호
                         ├─ finprdnm         금융상품명 (예: 사잇돌Ⅱ대출_대환형)
                         ├─ lnlmt            대출한도 (만원 단위, 예: 2000)
                         ├─ lnlmt1000abnml   1000만원 초과 가능여부
                         ├─ irtCtg           금리구분 (변동금리/고정금리)
                         ├─ irt              금리 수준 (예: ~19.99)
                         ├─ maxtotlntrm      최대 총 대출기간 (년)
                         ├─ maxdfrmtrm       최대 거치기간 (년)
                         ├─ maxrdpttrm       최대 상환기간 (년)
                         ├─ rdptmthd         상환방법 (예: 원(리)금균등분할상환)
                         ├─ usge             용도 (생계/사업/주거 등)
                         ├─ trgt             지원대상 (예: 근로자, 사업자, 연금소득자)
                         ├─ instCtg          기관구분 (민간기업/공공기관)
                         ├─ ofrinstnm        취급기관명 (예: SGI서울보증)
                         ├─ hdlinst          취급금융기관 (예: 저축은행)
                         ├─ rsdAreaPamtEqltIstm 거주지역 (전국/지역명)
                         ├─ suprtgtdtlcond   지원대상 상세 조건
                         ├─ age              나이 조건
                         ├─ incm             소득 조건
                         ├─ crdtsc           신용점수 조건
                         ├─ tgtFltr          대상 필터 태그
                         ├─ prdCtg           상품구분 코드
                         └─ prdoprprid       상품 운영기간 (상시/기간 지정)
        """
        params = {
            "serviceKey": PUBLIC_API_KEY,
            "pageNo":     page,
            "numOfRows":  display or COLLECT_PAGE_SIZE,
        }
        # 선택 파라미터 — 파라미터명 대문자 주의
        if irt_ctg:
            params["IRT_CTG"] = irt_ctg         # 금리구분 (고정금리/변동금리)
        if usge:
            params["USGE"] = usge               # 용도 (생계/사업/주거 등)
        if inst_ctg:
            params["INST_CTG"] = inst_ctg       # 기관구분 (공공기관/민간기업)
        if rsd_area:
            params["RSD_AREA_PAMT_EQLT_ISTM"] = rsd_area  # 거주지역
        if tgt_fltr:
            params["TGT_FLTR"] = tgt_fltr       # 대상 필터
        if prd_ctg:
            params["PRD_CTG"] = prd_ctg         # 상품구분

        raw = self.fetch_xml(SMALL_LOAN_URL, params)

        # XML 구조: <response><body><items><item>...
        items = (
            raw.get("response", {})
               .get("body", {})
               .get("items", {})
               .get("item", [])
        )
        if isinstance(items, dict):
            items = [items]
        return items if items else []

    # ──────────────────────────────────────────────────────────
    # 2. Discovery / Sync 파이프라인 인터페이스
    # ──────────────────────────────────────────────────────────

    # 별도 상세 API 없음 — sync 시 list_payload 를 그대로 document 로 저장
    HAS_DETAIL_API = False

    def get_external_id(self, item: dict) -> str:
        return str(item.get("seq", ""))

    def get_title(self, item: dict) -> str:
        return item.get("finprdnm", "")

    def normalize_list_item(self, item: dict) -> dict:
        return self.to_json_serializable(item)

    def normalize_detail(self, detail: dict) -> tuple[str, dict]:
        """
        서민금융 상품 → normalized_text + metadata.
        상세 API 없으므로 detail 은 목록 item 과 동일.

        주요 필드:
          finprdnm(상품명), lnlmt(한도), irtCtg(금리구분), irt(금리),
          usge(용도), trgt(지원대상), rdptmthd(상환방법),
          ofrinstnm(취급기관), hdlinst(취급금융기관),
          rsdAreaPamtEqltIstm(거주지역), suprtgtdtlcond(지원대상상세)
        """
        parts = [
            f"상품명: {detail.get('finprdnm', '')}",
            f"취급기관: {detail.get('ofrinstnm', '')} ({detail.get('hdlinst', '')})",
            f"금리구분: {detail.get('irtCtg', '')} / 금리: {detail.get('irt', '')}%",
            f"대출한도: {detail.get('lnlmt', '')}만원",
            f"용도: {detail.get('usge', '')}",
            f"지원대상: {detail.get('trgt', '')}",
            f"지원대상상세: {detail.get('suprtgtdtlcond', '')}",
            f"상환방법: {detail.get('rdptmthd', '')}",
            f"거주지역: {detail.get('rsdAreaPamtEqltIstm', '')}",
            f"총대출기간: {detail.get('maxtotlntrm', '')}년",
            f"나이조건: {detail.get('age', '')}",
            f"소득조건: {detail.get('incm', '')}",
            f"신용점수: {detail.get('crdtsc', '')}",
        ]
        normalized_text = "\n".join(p for p in parts if not p.endswith(": ") and not p.endswith("()")  and not p.endswith("만원") or detail.get('lnlmt'))

        metadata = {
            "title": detail.get("finprdnm", ""),
            "offering_inst": detail.get("ofrinstnm", ""),
            "handling_inst": detail.get("hdlinst", ""),
            "loan_limit": detail.get("lnlmt", ""),
            "interest_type": detail.get("irtCtg", ""),
            "interest_rate": detail.get("irt", ""),
            "loan_purpose": detail.get("usge", ""),
            "target": detail.get("trgt", ""),
            "inst_category": detail.get("instCtg", ""),
            "support_region": detail.get("rsdAreaPamtEqltIstm", ""),
            "repay_method": detail.get("rdptmthd", ""),
            "prd_ctg": detail.get("prdCtg", ""),
            "source_url": detail.get("rltsite", ""),
        }
        return normalized_text, metadata

    def build_detail_params(self, external_id: str) -> dict:
        # 상세 API 없음 — 호출되지 않음
        return {}
