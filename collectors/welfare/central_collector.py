"""
복지로 중앙부처복지서비스 Open API — 수집기
=============================================
API 출처 : 공공데이터포털 data.go.kr
제공기관 : 한국사회보장정보원
서비스 ID : 15113474 (NationalWelfareInformationsV001)

제공 메서드 (services 파이프라인이 사용)
---------------------------------------
- fetch_list()        목록 조회 (/NationalWelfarelistV001, callTp=L)
- fetch_detail()      상세 조회 (/NationalWelfaredetailedV001, callTp=D)
                      지원대상(tgtrDtlCn)·선정기준(slctCritCn)·지원내용(alwServCn) 등
- get_external_id()   servId 추출 / get_title() servNm 추출
- normalize_detail()  상세 → (normalized_text, metadata)

→ Discovery/Targeting/Sync 단계는 services.discovery / targeting / sync 참고.

필터 옵션 사용법
--------------
fetch_list() 에 파라미터를 전달해 원하는 복지서비스만 추출할 수 있다.
예:
  fetch_list(search_word="아동", life_array="001,002")
  → 영유아·아동 생애주기 복지서비스 중 '아동' 검색어 포함 항목 조회

  fetch_list(target_group="002", online_apply_yn="Y")
  → 장애인 대상 온라인 신청 가능 서비스만 조회
"""

import logging

from collectors.base import BaseCollector
from config.settings import (
    COLLECT_PAGE_SIZE,
    PUBLIC_API_KEY,
    WELFARE_CENTRAL_DETAIL_URL,
    WELFARE_CENTRAL_LIST_URL,
)

logger = logging.getLogger(__name__)


class WelfareCentralCollector(BaseCollector):
    """복지로 중앙부처 복지서비스 수집기."""

    SOURCE_NAME = "welfare_central"

    # ──────────────────────────────────────────────────────────
    # 1. 목록 조회
    # ──────────────────────────────────────────────────────────

    def fetch_list(
        self,
        page: int = 1,
        display: int = None,
        srch_key_code: str = "001",
        search_word: str = None,
        life_array: str = None,
        target_group: str = None,
        intr_thema: str = None,
        age: str = None,
        online_apply_yn: str = None,
        order_by: str = "date",
    ) -> list[dict]:
        """
        중앙부처 복지서비스 목록 조회 (callTp=L).

        ┌─────────────────────────────────────────────────────────────────────┐
        │  GET https://apis.data.go.kr/B554287/                              │
        │      NationalWelfareInformationsV001/NationalWelfarelistV001        │
        └─────────────────────────────────────────────────────────────────────┘

        요청 파라미터
        ─────────────
        serviceKey      (필수) 공공데이터포털 인증키
        callTp          (필수) 'L' = 목록조회 (고정값)
        pageNo          (필수) 페이지 번호 (1부터, 최대 1000)
        numOfRows       (필수) 페이지당 결과 수 (기본 10, 최대 500)
        srchKeyCode     (필수) 검색분류 — searchWrd 없이도 반드시 포함해야 함
                                 001 = 제목(서비스명) 검색
                                 002 = 내용 검색
                                 003 = 제목+내용 검색
                                 ※ searchWrd 없으면 전체 목록 반환

        search_word  → searchWrd       (선택) 검색어
                                              예: '아동', '임산부', '장애인'
        life_array   → lifeArray       (선택) 생애주기 필터 (콤마 구분 복수 선택 가능)
                                              임신·출산 / 영유아 / 아동 / 청소년
                                              청년 / 중장년 / 노년 / 장애
                                              ※ API 문서의 생애주기 코드표 참조
        target_group → trgterIndvdlArray (선택) 가구유형 필터 (콤마 구분 복수 선택)
                                              001=장애인 002=국가보훈 003=한부모
                                              004=다문화·외국인 등 코드표 참조
        intr_thema   → intrsThemaArray (선택) 관심주제 필터 (콤마 구분)
                                              생활안정 / 주거 / 교육 / 취업·창업
                                              문화·여가 / 보건·의료 / 법률·안전 등
        age          → age             (선택) 나이 (숫자, 단위: 세)
                                              예: '30' → 30세 대상 서비스만
        online_apply_yn → onapPsbltYn  (선택) 온라인 신청 가능 여부
                                              'Y' = 온라인 신청 가능한 서비스만
                                              'N' = 온라인 신청 불가 서비스만
        order_by     → orderBy         (선택) 정렬 기준
                                              'date'    = 최신 등록순 ← 기본
                                              'popular' = 인기순 (조회수 높은 순)

        응답 구조 (XML → xmltodict → dict)
        ────────────────────────────────
        wantedList
          ├─ totalCount       전체 서비스 수 (예: 452)
          ├─ pageNo           현재 페이지
          ├─ numOfRows        요청 건수
          ├─ resultCode       결과 코드 (0 = 정상)
          ├─ resultMessage    결과 메시지 (SUCCESS)
          └─ servList[]       복지서비스 목록
               ├─ servId           서비스ID (상세 조회 키, 예: WLF00001088)
               ├─ servNm           서비스명 (예: 고위험 임산부 의료비 지원)
               ├─ jurMnofNm        소관부처명 (예: 보건복지부)
               ├─ jurOrgNm         담당부서명 (예: 출산정책과)
               ├─ lifeArray        생애주기 (예: 임신·출산)
               ├─ intrsThemaArray  관심주제
               ├─ srvPvsnNm        지원방법 (현금지급 / 현물지급 / 서비스 등)
               ├─ sprtCycNm        지원주기 (1회성 / 월 / 연 등)
               ├─ onapPsbltYn      온라인신청가능여부 (Y/N)
               ├─ rprsCtadr        대표연락처 (예: 129)
               ├─ servDgst         서비스 요약 설명
               ├─ servDtlLink      서비스 상세 링크 URL
               ├─ inqNum           조회수
               └─ svcfrstRegTs     서비스 최초 등록일 (YYYYMMDD)
        """
        params = {
            "serviceKey":  PUBLIC_API_KEY,
            "callTp":      "L",                      # L = 목록조회 (필수 고정값)
            "pageNo":      page,
            "numOfRows":   display or COLLECT_PAGE_SIZE,
            "srchKeyCode": srch_key_code,            # 필수 — 001=제목 002=내용 003=제목+내용
        }
        if order_by:
            params["orderBy"] = order_by        # date=최신순, popular=인기순
        if search_word:
            params["searchWrd"] = search_word   # 검색어 (없으면 전체 조회)
        if life_array:
            params["lifeArray"] = life_array    # 생애주기 (콤마 구분, 예: '임신·출산')
        if target_group:
            params["trgterIndvdlArray"] = target_group  # 가구유형
        if intr_thema:
            params["intrsThemaArray"] = intr_thema      # 관심주제
        if age:
            params["age"] = age                 # 나이 (숫자)
        if online_apply_yn:
            params["onapPsbltYn"] = online_apply_yn     # Y/N

        raw = self.fetch_xml(WELFARE_CENTRAL_LIST_URL, params)

        # XML 구조: <wantedList><servList>...</servList><servList>...
        # 단건이면 dict, 복수면 list 로 반환
        items = raw.get("wantedList", {}).get("servList", [])
        if isinstance(items, dict):
            items = [items]
        return items if items else []

    # ──────────────────────────────────────────────────────────
    # 2. 상세 조회
    # ──────────────────────────────────────────────────────────

    def fetch_detail(self, service_id: str) -> dict:
        """
        중앙부처 복지서비스 상세 조회 (callTp=D).

        ┌─────────────────────────────────────────────────────────────────────┐
        │  GET https://apis.data.go.kr/B554287/                              │
        │      NationalWelfareInformationsV001/NationalWelfaredetailedV001    │
        └─────────────────────────────────────────────────────────────────────┘

        요청 파라미터
        ─────────────
        serviceKey  (필수) 공공데이터포털 인증키
        callTp      (필수) 'D' = 상세조회 (고정값)
        servId      (필수) 서비스ID — 목록 조회의 servList[].servId

        응답 구조 (목록 대비 추가 상세 필드)
        ─────────────────────────────────
        wantedDtl
          ├─ servId         서비스ID
          ├─ servNm         서비스명
          ├─ jurMnofNm      소관부처 (예: 보건복지부 출산정책과)
          ├─ crtrYr         기준년도
          ├─ tgtrDtlCn      지원대상 상세 — 자격 기준 전문
          ├─ slctCritCn     선정기준 상세 설명
          ├─ alwServCn      지원내용 상세 설명
          ├─ wlfareInfoOutlCn  서비스 요약 개요
          ├─ sprtCycNm      지원주기
          ├─ srvPvsnNm      지원방법
          ├─ rprsCtadr      대표연락처
          ├─ lifeArray      생애주기
          ├─ intrsThemaArray 관심주제
          ├─ applmetList    신청방법 목록
          ├─ inqplCtadrList 문의처 목록
          ├─ inqplHmpgReldList 관련 홈페이지 목록
          ├─ basfrmList     구비서류 목록
          └─ baslawList     관련 법령 목록
        """
        params = {
            "serviceKey": PUBLIC_API_KEY,
            "callTp":     "D",          # D = 상세조회 (필수 고정값)
            "servId":     service_id,   # 목록에서 확보한 servId
        }
        raw = self.fetch_xml(WELFARE_CENTRAL_DETAIL_URL, params)
        return raw.get("wantedDtl", raw)

    # ──────────────────────────────────────────────────────────
    # 3. Discovery / Sync 파이프라인 인터페이스
    # ──────────────────────────────────────────────────────────

    def get_external_id(self, item: dict) -> str:
        return item.get("servId", "")

    def get_title(self, item: dict) -> str:
        return item.get("servNm", "")

    def normalize_list_item(self, item: dict) -> dict:
        return self.to_json_serializable(item)

    def normalize_detail(self, detail: dict) -> tuple[str, dict]:
        """
        중앙부처 복지서비스 상세 → normalized_text + metadata.

        detail 필드 (NationalWelfaredetailedV001 응답):
          servNm, jurMnofNm, tgtrDtlCn(지원대상 상세),
          slctCritCn(선정기준), alwServCn(지원내용),
          wlfareInfoOutlCn(요약), sprtCycNm, srvPvsnNm,
          applmetList(신청방법), basfrmList(구비서류), inqplCtadrList(문의처)
        """
        def _list_text(v) -> str:
            if isinstance(v, list):
                return " / ".join(str(i) for i in v if i)
            if isinstance(v, dict):
                return " ".join(str(x) for x in v.values() if x)
            return str(v) if v else ""

        parts = [
            f"서비스명: {detail.get('servNm', '')}",
            f"소관부처: {detail.get('jurMnofNm', '')}",
            f"지원대상: {detail.get('tgtrDtlCn', '')}",
            f"선정기준: {detail.get('slctCritCn', '')}",
            f"지원내용: {detail.get('alwServCn', '')}",
            f"지원방법: {detail.get('srvPvsnNm', '')}",
            f"지원주기: {detail.get('sprtCycNm', '')}",
            f"신청방법: {_list_text(detail.get('applmetList', ''))}",
            f"구비서류: {_list_text(detail.get('basfrmList', ''))}",
            f"관련법령: {_list_text(detail.get('baslawList', ''))}",
        ]
        normalized_text = "\n".join(p for p in parts if not p.endswith(": "))

        metadata = {
            "title": detail.get("servNm", ""),
            "ministry": detail.get("jurMnofNm", ""),
            "life_array": detail.get("lifeArray", ""),
            "intr_thema": detail.get("intrsThemaArray", ""),
            "support_method": detail.get("srvPvsnNm", ""),
            "support_cycle": detail.get("sprtCycNm", ""),
            "online_apply_yn": detail.get("onapPsbltYn", ""),
            "contact": detail.get("rprsCtadr", ""),
            "source_url": detail.get("servDtlLink", ""),
        }
        return normalized_text, metadata

    def build_detail_params(self, external_id: str) -> dict:
        return {"service_id": external_id}
