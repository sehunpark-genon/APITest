"""
법제처 국가법령정보 Open API — 현행법령 수집기
==============================================
API 가이드 : https://open.law.go.kr/LSO/openApi/guideResult.do
인증키 발급 : https://open.law.go.kr → 오픈API → 이용신청 → OC 키 발급

제공 메서드 (services 파이프라인이 사용)
---------------------------------------
- fetch_list()        현행법령 목록 조회 (lawSearch.do, target=law)
- fetch_detail()      법령 본문 조회 (lawService.do, target=law) — 조문·항·호·부칙
- get_external_id()   법령일련번호(MST) 추출 (= collection_items.external_id)
- get_title()         법령명한글 추출
- normalize_detail()  본문 → (normalized_text, metadata)

→ Discovery/Targeting/Sync 단계는 services.discovery / targeting / sync 참고.

중요 주의사항
-------------
- 검색범위: search=1(법령명, 기본) / search=2(본문검색)
- 별표·서식: 응답 내 HWP/PDF 링크 포함 시 별도 파일 수집 필요 (미구현)
- 일일 호출량: open.law.go.kr 에서 발급받은 계정 기준 적용
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


class LawTextCollector(BaseCollector):
    SOURCE_NAME = "law_text"

    # ──────────────────────────────────────────────────────────
    # 1. 목록 조회
    # ──────────────────────────────────────────────────────────

    def fetch_list(
        self,
        page: int = 1,
        display: int = None,
        query: str = None,
        search: int = 1,
        nw: str = None,
        sort: str = None,
        ef_yd: str = None,
        anc_yd: str = None,
        anc_no: str = None,
        date: str = None,
        rr_cls_cd: str = None,
        nb: str = None,
        org: str = None,
        knd: str = None,
        gana: str = None,
        lid: str = None,
    ) -> list[dict]:
        """
        현행법령 목록 조회.

        ┌─────────────────────────────────────────────────────────┐
        │  GET https://www.law.go.kr/DRF/lawSearch.do            │
        └─────────────────────────────────────────────────────────┘

        요청 파라미터 (법제처 lawSearch.do target=law 전체 스펙)
        ──────────────────────────────────────────────────────────
        고정값 (코드에서 자동 지정)
          OC       (필수) 법제처 Open API 인증키 (.env LAW_OC_KEY)
          target   (필수) 'law' = 현행법령
          type     (필수) 'XML'  (xmltodict 파싱용)

        호출자 지정 가능 파라미터
          page       페이지 번호 (기본 1)
          display    페이지당 결과 수 (기본 20, 최대 100)
          query      법령명 검색어 (예: '근로기준법', '소득세')
          search     검색범위. 1=법령명(기본), 2=본문검색
          nw         연혁/시행예정/현행 구분
                       1=연혁, 2=시행예정, 3=현행 (생략 시 전체)
                       조합 가능: '1,3' = 연혁+현행
          sort       정렬옵션
                       lasc=법령오름차순(기본) / ldes=법령내림차순
                       dasc=공포일자오름차순 / ddes=공포일자내림차순
                       nasc=공포번호오름차순 / ndes=공포번호내림차순
                       efasc=시행일자오름차순 / efdes=시행일자내림차순
          ef_yd      시행일자 범위 검색 (efYd, 예: '20090101~20090130')
          anc_yd     공포일자 범위 검색 (ancYd, 예: '20090101~20090130')
          anc_no     공포번호 범위 검색 (ancNo, 예: '306~400')
          date       공포일자 단일 검색 (YYYYMMDD)
          rr_cls_cd  법령 제개정 종류 코드 (rrClsCd)
                       300201=제정 300202=일부개정 300203=전부개정
                       300204=폐지 300205=폐지제정 300206=일괄개정
                       300207=일괄폐지 300209=타법개정 300210=타법폐지
                       300208=기타
          nb         공포번호 검색 (숫자)
          org        소관부처코드 (예: '1741000'=고용노동부)
          knd        법령종류 코드 (법제처 코드표 참조)
          gana       사전식 검색 (ga, na, da …)
          lid        법령ID (LID, 예: '830')

        응답 구조 (XML → xmltodict → dict)
        ────────────────────────────────
        LawSearch
          ├─ totalCnt       전체 법령 수
          ├─ page           현재 페이지
          ├─ numOfRows      요청 건수
          ├─ resultCode     결과 코드 (00 = 정상)
          ├─ resultMsg      결과 메시지
          └─ law[@id][]     법령 목록
               ├─ 법령일련번호   MST 값 (본문 조회 키)
               ├─ 법령ID        법령 고유 ID
               ├─ 법령명한글     법령 전체 명칭
               ├─ 법령약칭명     약칭 (예: 소득세법)
               ├─ 공포일자       YYYYMMDD 형식
               ├─ 공포번호       관보 번호
               ├─ 시행일자       YYYYMMDD 형식
               ├─ 소관부처명     부처명 (예: 기획재정부)
               ├─ 소관부처코드   부처 코드
               ├─ 법령구분명     법률/대통령령/총리령/부령/훈령/예규 등
               ├─ 제개정구분명   제정/개정/타법개정 등
               └─ 법령상세링크   본문 조회 URL 템플릿
        """
        params = {
            "OC":      LAW_OC_KEY,
            "target":  "law",
            "type":    "XML",
            "search":  search,                       # 1=법령명(기본), 2=본문검색
            "page":    page,
            "display": display or COLLECT_PAGE_SIZE,  # 페이지당 결과 수
        }
        if query:
            params["query"] = query       # 법령명/본문 검색어 (빈값이면 전체 조회)
        if nw:
            params["nw"] = nw             # 연혁(1)/시행예정(2)/현행(3)
        if sort:
            params["sort"] = sort         # 정렬옵션 (lasc/ddes/efdes 등)
        if ef_yd:
            params["efYd"] = ef_yd        # 시행일자 범위 (YYYYMMDD~YYYYMMDD)
        if anc_yd:
            params["ancYd"] = anc_yd      # 공포일자 범위
        if anc_no:
            params["ancNo"] = anc_no      # 공포번호 범위
        if date:
            params["date"] = date         # 공포일자 단일 검색
        if rr_cls_cd:
            params["rrClsCd"] = rr_cls_cd  # 제개정 종류 코드
        if nb:
            params["nb"] = nb             # 공포번호
        if org:
            params["org"] = org           # 소관부처코드 필터
        if knd:
            params["knd"] = knd           # 법령종류 코드
        if gana:
            params["gana"] = gana         # 사전식 검색
        if lid:
            params["LID"] = lid           # 법령ID

        raw = self.fetch_xml(LAW_SEARCH_URL, params)

        # XML 구조: <LawSearch><law id="1">...</law><law id="2">...</law>
        # xmltodict 는 복수 항목을 list, 단건을 dict 로 반환
        laws = raw.get("LawSearch", {}).get("law", [])
        if isinstance(laws, dict):
            laws = [laws]
        return laws if laws else []

    # ──────────────────────────────────────────────────────────
    # 2. 본문 조회
    # ──────────────────────────────────────────────────────────

    def fetch_detail(self, law_msn: str, ef_date: str = None) -> dict:
        """
        법령 본문 상세 조회.

        ┌─────────────────────────────────────────────────────────┐
        │  GET https://www.law.go.kr/DRF/lawService.do           │
        └─────────────────────────────────────────────────────────┘

        요청 파라미터
        ─────────────
        OC       (필수) 법제처 Open API 인증키
        target   (필수) 'law' (현행법령)
        MST      (필수) 법령일련번호 — 목록 조회에서 확보한 값
        type     (필수) 응답 형식
                         XML  = XML 구조 (본 수집기 사용)
                         JSON = JSON
                         HTML = 브라우저 렌더링용 HTML
        mobileYn (선택) 모바일 최적화 여부 (Y / N, 기본 N)
        efYd     (선택) 시행일자 기준 조회 (YYYYMMDD)
                         특정 날짜 기준으로 시행 중인 버전 조회 시 사용
                         생략 시 현재 시행 버전 반환

        응답 구조 (XML → xmltodict → dict)
        ────────────────────────────────
        법령[@법령키]
          ├─ 기본정보
          │    ├─ 법령ID / 공포일자 / 공포번호
          │    ├─ 법종구분     법률/대통령령/부령 등
          │    ├─ 법령명_한글  전체 법령명
          │    ├─ 법령명약칭   약칭
          │    ├─ 소관부처     부처명
          │    ├─ 시행일자     현재 시행 버전 시행일
          │    └─ 제개정구분   제정/일부개정/전부개정 등
          ├─ 조문
          │    └─ 조문단위[]   각 조 단위
          │         ├─ 조문번호      (1, 2, 3...)
          │         ├─ 조문제목      (예: 목적, 정의, 적용범위)
          │         ├─ 조문시행일자  해당 조문의 시행일
          │         ├─ 조문내용      조문 본문 (HTML 태그 포함 가능)
          │         ├─ 항[]          1항, 2항, ...
          │         ├─ 호[]          1호, 2호, ...
          │         └─ 목[]          가목, 나목, ...
          ├─ 부칙
          │    └─ 부칙단위[]   부칙 조항
          └─ 별표편집여부      Y = 별표/서식 파일 존재 (HWP/PDF 링크 별도 수집 필요)
        """
        params = {
            "OC":     LAW_OC_KEY,
            "target": "law",
            "MST":    law_msn,
            "type":   "XML",
        }
        if ef_date:
            params["efYd"] = ef_date      # 특정 시행일자 기준 버전 조회

        return self.fetch_xml(LAW_SERVICE_URL, params)

    # ──────────────────────────────────────────────────────────
    # 3. Discovery / Sync 파이프라인 인터페이스
    # ──────────────────────────────────────────────────────────

    def get_external_id(self, item: dict) -> str:
        return item.get("법령일련번호", "")

    def get_title(self, item: dict) -> str:
        return item.get("법령명한글", "")

    def normalize_list_item(self, item: dict) -> dict:
        """목록 응답 item 그대로 반환 (필드 누락 없이 보존)."""
        return self.to_json_serializable(item)

    def normalize_detail(self, detail: dict) -> tuple[str, dict]:
        """
        법령 본문 → normalized_text (조문 텍스트) + metadata.

        detail 구조 (lawService.do XML → xmltodict):
          법령
            기본정보: 법령명_한글, 소관부처, 시행일자, 공포일자, 법종구분
            조문
              조문단위[]: 조문번호, 조문제목, 조문내용, 항[], 호[], 목[]
            부칙
              부칙단위[]: 부칙내용
        """
        law = detail.get("법령", {})
        basic = law.get("기본정보", {})

        def _str(v) -> str:
            if isinstance(v, dict):
                return v.get("#text", "") or v.get("@value", "")
            return str(v) if v else ""

        title = _str(basic.get("법령명_한글") or basic.get("법령명한글"))
        dept = _str(basic.get("소관부처"))
        enforcement = _str(basic.get("시행일자"))
        promulgation = _str(basic.get("공포일자"))
        law_type = _str(basic.get("법종구분"))

        parts = [f"법령명: {title}", f"소관부처: {dept}",
                 f"시행일자: {enforcement}", f"공포일자: {promulgation}"]

        # 조문 추출
        articles = law.get("조문", {}).get("조문단위", [])
        if isinstance(articles, dict):
            articles = [articles]
        for art in articles or []:
            num = _str(art.get("조문번호"))
            art_title = _str(art.get("조문제목"))
            content = _str(art.get("조문내용"))
            parts.append(f"\n제{num}조 {art_title}")
            if content:
                parts.append(content)
            # 항
            for hang in ([art.get("항")] if isinstance(art.get("항"), dict) else (art.get("항") or [])):
                if isinstance(hang, dict):
                    parts.append("  " + _str(hang.get("항내용")))

        # 부칙
        addenda = law.get("부칙", {}).get("부칙단위", [])
        if isinstance(addenda, dict):
            addenda = [addenda]
        for add in addenda or []:
            if isinstance(add, dict):
                parts.append(_str(add.get("부칙내용")))

        normalized_text = "\n".join(p for p in parts if p)
        metadata = {
            "title": title,
            "law_id": _str(basic.get("법령ID")),
            "department": dept,
            "law_type": law_type,
            "enforcement_date": enforcement,
            "promulgation_date": promulgation,
            "source_url": _str(basic.get("법령상세링크")),
        }
        return normalized_text, metadata

    def build_detail_params(self, external_id: str) -> dict:
        return {"law_msn": external_id}
