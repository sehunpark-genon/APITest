"""
복지로 지자체복지서비스 Open API — 수집기
==========================================
API 출처 : 공공데이터포털 data.go.kr
제공기관 : 한국사회보장정보원
서비스 ID : 15113474 (LocalGovernmentWelfareInformations)

제공 메서드 (services 파이프라인이 사용)
---------------------------------------
- fetch_list()        목록 조회 (/LcgvWelfarelist)
- fetch_detail()      상세 조회 (/LcgvWelfaredetailed) — callTp 없음(중앙부처와 다름)
                      지원대상(sprtTrgtCn)·선정기준(slctCritCn)·지원내용(alwServCn) 등
- get_external_id()   servId 추출 / get_title() servNm 추출
- normalize_detail()  상세 → (normalized_text, metadata)

→ Discovery/Targeting/Sync 단계는 services.discovery / targeting / sync 참고.

필터 옵션 사용법
--------------
fetch_list() 에 파라미터를 전달해 특정 지역·대상의 복지서비스만 추출할 수 있다.
예:
  fetch_list(region_name="서울특별시", city_name="강남구")
  → 서울 강남구 소관 지자체 복지서비스만 조회
  ※ 시도명/시군구명은 코드가 아닌 이름(문자열) 으로 전달!

  fetch_list(search_word="산모", life_array="임신·출산")
  → 임신·출산 생애주기 중 '산모' 검색어 포함 서비스 조회
"""

import logging

from collectors.base import BaseCollector
from config.settings import (
    COLLECT_PAGE_SIZE,
    PUBLIC_API_KEY,
    WELFARE_LOCAL_DETAIL_URL,
    WELFARE_LOCAL_LIST_URL,
)

logger = logging.getLogger(__name__)


class WelfareLocalCollector(BaseCollector):
    """복지로 지자체 복지서비스 수집기."""

    SOURCE_NAME = "welfare_local"

    # ──────────────────────────────────────────────────────────
    # 1. 목록 조회
    # ──────────────────────────────────────────────────────────

    def fetch_list(
        self,
        page: int = 1,
        display: int = None,
        region_name: str = None,
        city_name: str = None,
        srch_key_code: str = None,
        search_word: str = None,
        life_array: str = None,
        target_group: str = None,
        intr_thema: str = None,
        age: str = None,
        sort_order: str = None,
    ) -> list[dict]:
        """
        지자체 복지서비스 목록 조회.

        ┌─────────────────────────────────────────────────────────────────────┐
        │  GET https://apis.data.go.kr/B554287/                              │
        │      LocalGovernmentWelfareInformations/LcgvWelfarelist            │
        └─────────────────────────────────────────────────────────────────────┘

        요청 파라미터
        ─────────────
        serviceKey      (필수) 공공데이터포털 인증키
        pageNo          (선택) 페이지 시작 위치 (기본 1)
        numOfRows       (선택) 출력 건수 (기본 10)

        region_name  → ctpvNm      (선택) 시도명 — 코드 아닌 이름(문자열)으로 전달!
                                           예: '서울특별시', '경기도', '전라남도'
                                           ※ 숫자 코드(11, 31 등)가 아님에 주의
        city_name    → sggNm       (선택) 시군구명 — 역시 문자열
                                           예: '강남구', '수원시', '해남군'
                                           ctpvNm 없이 단독 사용 가능
        search_word  → searchWrd   (선택) 서비스명 검색어
        life_array   → lifeArray   (선택) 생애주기 필터 (콤마 구분 복수 선택)
                                           임신·출산 / 영유아 / 아동 / 청소년
                                           청년 / 중장년 / 노년 / 장애
        target_group → trgterIndvdlArray (선택) 가구유형 필터 (콤마 구분)
        intr_thema   → intrsThemaArray   (선택) 관심주제 필터 (콤마 구분)
        age          → age               (선택) 나이 (숫자, 단위: 세)
        sort_order   → arrgOrd           (선택) 정렬 순서
                                           ※ 유효 값은 API 문서 참조 (미지정 시 기본 정렬)

        [목록 조회에 callTp 파라미터 없음 — 상세 전용 아님]

        응답 구조 (XML → xmltodict → dict)
        ────────────────────────────────
        wantedList
          ├─ totalCount       전체 서비스 수 (예: 4561)
          ├─ pageNo           현재 페이지
          ├─ numOfRows        요청 건수
          ├─ resultCode       결과 코드 (0 = 정상)
          ├─ resultMessage    결과 메시지 (SUCCESS)
          └─ servList[]       복지서비스 목록
               ├─ servId           서비스ID (상세 조회 키, 예: WLF00005649)
               ├─ servNm           서비스명 (예: 산모 산후조리비 지원)
               ├─ ctpvNm           시도명 (예: 전라남도)
               ├─ sggNm            시군구명 (예: 해남군)
               ├─ bizChrDeptNm     사업담당기관명 (예: 전라남도 해남군 보건소)
               ├─ aplyMtdNm        신청방법 (방문 / 인터넷 / 우편 등)
               ├─ srvPvsnNm        지원방법 (현금지급 / 현물지급 등)
               ├─ sprtCycNm        지원주기 (1회성 / 월 / 연 등)
               ├─ intrsThemaNmArray 관심주제명
               ├─ servDgst         서비스 요약 설명
               ├─ servDtlLink      서비스 상세 링크
               ├─ inqNum           조회수
               └─ lastModYmd       최종 수정일 (YYYYMMDD)
        """
        params = {
            "serviceKey": PUBLIC_API_KEY,
            "pageNo":     page,
            "numOfRows":  display or COLLECT_PAGE_SIZE,
        }
        # 선택 필터 — 모두 미지정 시 전체 지자체 서비스 반환
        if region_name:
            params["ctpvNm"] = region_name      # 시도명 (코드 아닌 이름!  예: '서울특별시')
        if city_name:
            params["sggNm"] = city_name         # 시군구명 (예: '강남구')
        if srch_key_code:
            params["srchKeyCode"] = srch_key_code  # 검색분류 (001=제목 002=내용 003=제목+내용)
        if search_word:
            params["searchWrd"] = search_word   # 검색어
        if life_array:
            params["lifeArray"] = life_array    # 생애주기
        if target_group:
            params["trgterIndvdlArray"] = target_group  # 가구유형
        if intr_thema:
            params["intrsThemaArray"] = intr_thema      # 관심주제
        if age:
            params["age"] = age                 # 나이 (숫자)
        if sort_order:
            params["arrgOrd"] = sort_order      # 정렬순서

        raw = self.fetch_xml(WELFARE_LOCAL_LIST_URL, params)

        # XML 구조: <wantedList><servList>...</servList><servList>...
        items = raw.get("wantedList", {}).get("servList", [])
        if isinstance(items, dict):
            items = [items]
        return items if items else []

    # ──────────────────────────────────────────────────────────
    # 2. 상세 조회
    # ──────────────────────────────────────────────────────────

    def fetch_detail(self, service_id: str) -> dict:
        """
        지자체 복지서비스 상세 조회.

        ┌─────────────────────────────────────────────────────────────────────┐
        │  GET https://apis.data.go.kr/B554287/                              │
        │      LocalGovernmentWelfareInformations/LcgvWelfaredetailed        │
        └─────────────────────────────────────────────────────────────────────┘

        요청 파라미터
        ─────────────
        serviceKey  (필수) 공공데이터포털 인증키
        servId      (필수) 서비스ID — 목록 조회의 servList[].servId
        ※ callTp 파라미터 없음 — 중앙부처 상세 API 와 다름에 주의!

        응답 구조 (목록 대비 추가 상세 필드)
        ─────────────────────────────────
        wantedDtl
          ├─ servId         서비스ID
          ├─ servNm         서비스명
          ├─ enfcBgngYmd    시행 시작일 (YYYYMMDD)
          ├─ enfcEndYmd     시행 종료일 (99991231 = 상시)
          ├─ bizChrDeptNm   사업담당기관명
          ├─ ctpvNm         시도명
          ├─ sggNm          시군구명
          ├─ servDgst       서비스 요약
          ├─ lifeNmArray    생애주기명
          ├─ intrsThemaNmArray 관심주제명
          ├─ sprtTrgtCn     지원대상 상세 설명
          ├─ slctCritCn     선정기준 상세 설명
          ├─ alwServCn      지원내용 상세 설명
          ├─ aplyMtdCn      신청방법 상세 설명
          ├─ inqplCtadrList 문의처 목록
          ├─ baslawList     관련 법령 목록
          └─ basfrmList     구비서류 목록
        """
        params = {
            "serviceKey": PUBLIC_API_KEY,
            "servId":     service_id,    # callTp 파라미터 없음 (지자체 전용 스펙)
        }
        raw = self.fetch_xml(WELFARE_LOCAL_DETAIL_URL, params)
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
        지자체 복지서비스 상세 → normalized_text + metadata.

        detail 필드 (LcgvWelfaredetailed 응답):
          servNm, ctpvNm, sggNm, bizChrDeptNm,
          sprtTrgtCn(지원대상), slctCritCn(선정기준),
          alwServCn(지원내용), aplyMtdCn(신청방법),
          inqplCtadrList(문의처), baslawList(관련법령)
        """
        def _list_text(v) -> str:
            if isinstance(v, list):
                return " / ".join(str(i) for i in v if i)
            if isinstance(v, dict):
                return " ".join(str(x) for x in v.values() if x)
            return str(v) if v else ""

        region = f"{detail.get('ctpvNm', '')} {detail.get('sggNm', '')}".strip()
        parts = [
            f"서비스명: {detail.get('servNm', '')}",
            f"지역: {region}",
            f"담당기관: {detail.get('bizChrDeptNm', '')}",
            f"지원대상: {detail.get('sprtTrgtCn', '')}",
            f"선정기준: {detail.get('slctCritCn', '')}",
            f"지원내용: {detail.get('alwServCn', '')}",
            f"신청방법: {detail.get('aplyMtdCn', '')}",
            f"구비서류: {_list_text(detail.get('basfrmList', ''))}",
            f"관련법령: {_list_text(detail.get('baslawList', ''))}",
        ]
        normalized_text = "\n".join(p for p in parts if not p.endswith(": "))

        metadata = {
            "title": detail.get("servNm", ""),
            "region": region,
            "city": detail.get("sggNm", ""),
            "biz_dept": detail.get("bizChrDeptNm", ""),
            "apply_method": detail.get("aplyMtdNm", ""),
            "support_method": detail.get("srvPvsnNm", ""),
            "support_cycle": detail.get("sprtCycNm", ""),
            "life_array": detail.get("lifeNmArray", ""),
            "source_url": detail.get("servDtlLink", ""),
        }
        return normalized_text, metadata

    def build_detail_params(self, external_id: str) -> dict:
        return {"service_id": external_id}
