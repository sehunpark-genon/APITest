"""
법제처 국가법령정보 Open API — 법률 판례 수집기
================================================
API 가이드 : https://open.law.go.kr/LSO/openApi/guideResult.do
판례 목록 : https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=precListGuide
판례 본문 : https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=precInfoGuide
인증키 발급 : https://open.law.go.kr → 오픈API → 이용신청

제공 메서드 (services 파이프라인이 사용)
---------------------------------------
- fetch_list()        판례 목록 조회 (lawSearch.do, target=prec)
- fetch_detail()      판례 본문 조회 (lawService.do, target=prec)
                      ※ 본문은 type 파라미터와 무관하게 항상 HTML 형식 반환
- get_external_id()   판례일련번호 추출
- get_title()         사건명 추출
- normalize_detail()  본문 HTML → (normalized_text, metadata)

→ Discovery/Targeting/Sync 단계는 services.discovery / targeting / sync 참고.

중요 주의사항
-------------
- 판례 본문(lawService.do) 은 HTML 전용 응답
  xmltodict 가 {'html': {...}} 구조로 파싱 → JSONB 저장 가능
  Diff/텍스트 추출 단계에서 HTML 파싱 필요
- 법원종류(org 파라미터) 미지정 시 대법원·고등법원·지방법원 등 전체 포함
"""

import logging

from collectors.base import BaseCollector
from config.settings import (
    COLLECT_PAGE_SIZE,
    LAW_OC_KEY,
    LAW_SEARCH_URL,
    LAW_SERVICE_URL,
)

logger = logging.getLogger(__name__)


class PrecedentCollector(BaseCollector):
    SOURCE_NAME = "precedent"

    # ──────────────────────────────────────────────────────────
    # 1. 목록 조회
    # ──────────────────────────────────────────────────────────

    def fetch_list(
        self,
        page: int = 1,
        display: int = None,
        query: str = None,
        search: int = 1,
        court_org: str = None,
        court_name: str = None,
        ref_law: str = None,
        gana: str = None,
        sort: str = None,
        date: str = None,
        prnc_yd: str = None,
        case_no: str = None,
        data_src_nm: str = None,
        prec_type: str = None,
    ) -> list[dict]:
        """
        판례 목록 조회.

        ┌─────────────────────────────────────────────────────────┐
        │  GET https://www.law.go.kr/DRF/lawSearch.do            │
        └─────────────────────────────────────────────────────────┘

        요청 파라미터 (법제처 lawSearch.do target=prec 전체 스펙)
        ──────────────────────────────────────────────────────────
        고정값 (코드에서 자동 지정)
          OC       (필수) 법제처 Open API 인증키 (.env LAW_OC_KEY)
          target   (필수) 'prec' = 판례
          type     (필수) 'XML'  (xmltodict 파싱용)

        호출자 지정 가능 파라미터
          page         페이지 번호 (기본 1)
          display      페이지당 결과 수 (기본 20, 최대 100)
          query        검색어 (사건명 또는 본문 내 키워드)
                         예: '손해배상', '계약해지', '임금체불'
          search       검색범위. 1=판례명(기본), 2=본문검색
          court_org    법원종류코드 (org). 400201=대법원, 400202=하위법원
          court_name   법원명 (curt). 예: '대법원', '서울고등법원', '광주지법'
          ref_law      참조법령명 (JO). 예: '형법', '민법'
          gana         사전식 검색 (ga, na, da …)
          sort         정렬옵션
                         lasc=사건명오름차순 / ldes=사건명내림차순
                         dasc=선고일자오름차순 / ddes=선고일자내림차순(기본)
                         nasc=법원명오름차순 / ndes=법원명내림차순
          date         판례 선고일자 단일 검색 (YYYYMMDD)
          prnc_yd      선고일자 범위 검색 (prncYd, 예: '20090101~20090130')
          case_no      판례 사건번호 (nb, 예: '2024다12345')
          data_src_nm  데이터출처명 (datSrcNm)
                         예: '국세법령정보시스템', '근로복지공단산재판례', '대법원'
          prec_type    판결유형 (precType). 판결 / 결정 / 명령

        응답 구조 (XML → xmltodict → dict)
        ────────────────────────────────
        PrecSearch
          ├─ totalCnt       전체 판례 수
          ├─ page           현재 페이지
          ├─ numOfRows      요청 건수
          ├─ resultCode     결과 코드 (00 = 정상)
          └─ prec[@id][]    판례 목록
               ├─ 판례일련번호   MST 값 (본문 조회 키)
               ├─ 사건명        판례 제목 (예: 손해배상(기))
               ├─ 사건번호      예: '2024다12345'
               ├─ 선고일자      YYYYMMDD 형식
               ├─ 법원명        예: '대법원', '서울고등법원'
               ├─ 법원종류      법원종류코드 (400201 등)
               └─ 판결유형      판결 / 결정 / 명령
        """
        params = {
            "OC":      LAW_OC_KEY,
            "target":  "prec",
            "type":    "XML",
            "search":  search,                       # 1=판례명(기본), 2=본문검색
            "page":    page,
            "display": display or COLLECT_PAGE_SIZE,  # 페이지당 결과 수
        }
        if query:
            params["query"] = query           # 검색어 (없으면 전체 판례 반환)
        if court_org:
            params["org"] = court_org         # 법원종류코드 (400201=대법원 등)
        if court_name:
            params["curt"] = court_name       # 법원명 (예: 서울고등법원)
        if ref_law:
            params["JO"] = ref_law            # 참조법령명 (형법, 민법 등)
        if gana:
            params["gana"] = gana             # 사전식 검색
        if sort:
            params["sort"] = sort             # 정렬옵션 (ddes 기본)
        if date:
            params["date"] = date             # 선고일자 단일 검색
        if prnc_yd:
            params["prncYd"] = prnc_yd        # 선고일자 범위 검색
        if case_no:
            params["nb"] = case_no            # 사건번호
        if data_src_nm:
            params["datSrcNm"] = data_src_nm  # 데이터출처명
        if prec_type:
            params["precType"] = prec_type    # 판결유형 필터

        raw = self.fetch_xml(LAW_SEARCH_URL, params)

        # XML 구조: <PrecSearch><prec id="1">...</prec>...
        precs = raw.get("PrecSearch", {}).get("prec", [])
        if isinstance(precs, dict):
            precs = [precs]
        return precs if precs else []

    # ──────────────────────────────────────────────────────────
    # 2. 본문 조회
    # ──────────────────────────────────────────────────────────

    def fetch_detail(self, prec_msn: str) -> dict:
        """
        판례 본문 상세 조회.

        ┌─────────────────────────────────────────────────────────┐
        │  GET https://www.law.go.kr/DRF/lawService.do           │
        └─────────────────────────────────────────────────────────┘

        요청 파라미터
        ─────────────
        OC       (필수) 법제처 Open API 인증키
        target   (필수) 'prec' (판례)
        MST      (필수) 판례일련번호 — 목록 조회의 prec[].판례일련번호
        type     (필수) 응답 형식
                         ⚠️  판례 본문은 type 값과 무관하게 항상 HTML 반환
                         XML 요청 → Content-Type: text/html 로 응답
                         → xmltodict 가 {'html': {'head':..., 'body':...}} 로 파싱
                         → raw_response JSONB 에 HTML 파싱 결과 저장
        mobileYn (선택) 모바일 최적화 여부 (Y / N, 기본 N)

        응답 구조 (HTML → xmltodict → dict)
        ─────────────────────────────────
        html
          ├─ head     메타정보
          └─ body     판례 본문 영역
               ├─ 판시사항    핵심 법률 쟁점 요약
               ├─ 판결요지    주요 판단 결론 및 이유 요약
               ├─ 참조조문    관련 법령 조문 목록
               │              예: 민법 제750조, 형법 제347조
               ├─ 참조판례    선례 판례 목록
               │              예: 대법원 2020다12345 판결
               └─ 판례내용    판례 전문 (HTML 태그 포함)
                              - 사실관계, 원심 판단, 대법원 판단 포함
                              - Diff·텍스트 추출 단계에서 HTML 파싱 필요

        ※ 향후 텍스트 추출(DMZ 정제 단계) 시 BeautifulSoup 등으로
          HTML 태그 제거 후 정제된 텍스트 별도 컬럼 저장 권장
        """
        params = {
            "OC":     LAW_OC_KEY,
            "target": "prec",
            "MST":    prec_msn,
            "type":   "XML",    # HTML로 반환되지만 XML 요청 — xmltodict 로 파싱 가능
        }
        return self.fetch_xml(LAW_SERVICE_URL, params)

    # ──────────────────────────────────────────────────────────
    # 3. Discovery / Sync 파이프라인 인터페이스
    # ──────────────────────────────────────────────────────────

    def get_external_id(self, item: dict) -> str:
        return item.get("판례일련번호", "")

    def get_title(self, item: dict) -> str:
        return item.get("사건명", "")

    def normalize_list_item(self, item: dict) -> dict:
        return self.to_json_serializable(item)

    def normalize_detail(self, detail: dict) -> tuple[str, dict]:
        """
        판례 본문 → normalized_text + metadata.

        detail 구조 (lawService.do → HTML → xmltodict):
          html
            head: title, meta[]
            body: 판시사항, 판결요지, 참조조문, 판례내용 (HTML 태그 포함)
        """

        def _extract_text(obj, max_depth: int = 8) -> str:
            """dict/list 에서 텍스트만 재귀 추출."""
            if max_depth <= 0:
                return ""
            if isinstance(obj, str):
                return obj.strip()
            if isinstance(obj, list):
                return " ".join(_extract_text(v, max_depth - 1) for v in obj if v)
            if isinstance(obj, dict):
                return " ".join(
                    _extract_text(v, max_depth - 1)
                    for k, v in obj.items()
                    if not k.startswith("@") and v
                )
            return str(obj) if obj else ""

        html_body = detail.get("html", {}).get("body", detail)
        normalized_text = _extract_text(html_body)

        # 목록 item 에는 없을 수 있으므로 detail 에서도 시도
        metadata = {
            "title": detail.get("사건명", ""),
            "case_number": detail.get("사건번호", ""),
            "court_name": detail.get("법원명", ""),
            "decision_date": detail.get("선고일자", ""),
            "verdict_type": detail.get("판결유형", ""),
            "source_url": detail.get("판례상세링크", ""),
        }
        return normalized_text, metadata

    def build_detail_params(self, external_id: str) -> dict:
        return {"prec_msn": external_id}
