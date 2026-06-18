"""
모든 수집기의 공통 기반 클래스
- HTTP GET 요청 + 재시도
- XML / JSON → dict 변환
- Discovery/Targeting/Sync 파이프라인 인터페이스(추상)
"""

import json
import logging
import time
from abc import ABC, abstractmethod

import requests
import xmltodict

from config.settings import REQUEST_DELAY_SECS

logger = logging.getLogger(__name__)

# 공공 API 공통 타임아웃 (초)
_REQUEST_TIMEOUT = 30
# 실패 시 재시도 횟수
_MAX_RETRIES = 3


class BaseCollector(ABC):
    """수집기 추상 기반 클래스."""

    # 하위 클래스에서 반드시 지정 (파이프라인 source 식별자)
    SOURCE_NAME: str = ""

    def fetch_xml(self, url: str, params: dict) -> dict:
        """
        GET 요청 후 XML 응답을 dict 로 파싱하여 반환.

        Parameters
        ----------
        url    : API 엔드포인트
        params : 쿼리 파라미터 (serviceKey, pageNo 등)

        Returns
        -------
        dict : xmltodict 로 파싱된 응답 전체

        Raises
        ------
        RuntimeError : 재시도 횟수 초과 시
        """
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.debug("[%s] GET %s params=%s", self.SOURCE_NAME, url, params)
                resp = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT)
                resp.raise_for_status()

                # xmltodict 는 XML → OrderedDict 로 변환
                # force_list: 단건 응답도 항상 리스트로 받아 처리 일관성 유지
                parsed = xmltodict.parse(resp.text)
                return parsed

            except requests.RequestException as exc:
                logger.warning(
                    "[%s] 요청 실패 (시도 %d/%d): %s",
                    self.SOURCE_NAME, attempt, _MAX_RETRIES, exc,
                )
                if attempt == _MAX_RETRIES:
                    raise RuntimeError(
                        f"[{self.SOURCE_NAME}] {url} 요청 {_MAX_RETRIES}회 실패"
                    ) from exc
                # 재시도 시 data.go.kr 500은 보통 키 문제 — 무한 루프 방지
                if hasattr(exc, "response") and exc.response is not None:
                    sc = exc.response.status_code
                    if sc in (401, 403, 500):
                        raise RuntimeError(
                            f"[{self.SOURCE_NAME}] {url} → HTTP {sc}. "
                            "serviceKey 가 올바른지 확인하세요 (data.go.kr 마이페이지)."
                        ) from exc
                time.sleep(2 ** attempt)  # 1초, 2초, 4초 백오프

    def fetch_json(self, url: str, params: dict) -> dict:
        """
        GET 요청 후 JSON 응답을 dict 로 반환.

        Parameters
        ----------
        url    : API 엔드포인트
        params : 쿼리 파라미터

        Returns
        -------
        dict : JSON 파싱 결과
        """
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.debug("[%s] GET %s params=%s", self.SOURCE_NAME, url, params)
                resp = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()

            except requests.RequestException as exc:
                logger.warning(
                    "[%s] 요청 실패 (시도 %d/%d): %s",
                    self.SOURCE_NAME, attempt, _MAX_RETRIES, exc,
                )
                if attempt == _MAX_RETRIES:
                    raise RuntimeError(
                        f"[{self.SOURCE_NAME}] {url} 요청 {_MAX_RETRIES}회 실패"
                    ) from exc
                time.sleep(2 ** attempt)

    @staticmethod
    def to_json_serializable(obj) -> dict:
        """
        xmltodict 의 OrderedDict 를 JSON 직렬화 가능한 일반 dict 로 변환.
        JSONB 컬럼 저장 전 반드시 호출.
        """
        return json.loads(json.dumps(obj))

    def throttle(self):
        """공공 API 속도 제한 준수용 딜레이."""
        time.sleep(REQUEST_DELAY_SECS)

    # ── Discovery / Targeting / Sync 파이프라인 인터페이스 ──────────

    # False 이면 상세 API 없음 (small_loan) — sync 시 list_payload 사용
    HAS_DETAIL_API: bool = True

    @abstractmethod
    def get_external_id(self, item: dict) -> str:
        """목록 item 에서 API 고유 식별자 추출 (DB upsert 키)."""

    @abstractmethod
    def get_title(self, item: dict) -> str:
        """목록 item 에서 표시용 제목 추출."""

    @abstractmethod
    def normalize_list_item(self, item: dict) -> dict:
        """목록 item 을 collection_items.list_payload 용 dict 로 정규화."""

    @abstractmethod
    def normalize_detail(self, detail: dict) -> tuple[str, dict]:
        """
        상세 API 응답을 (normalized_text, metadata) 로 변환.
        - normalized_text : RAG/검색용 평문 (조문·지원내용·상품정보 등)
        - metadata        : 구조화 정보 dict (제목·기관·날짜·분류·URL 등)
        """

    @abstractmethod
    def build_detail_params(self, external_id: str) -> dict:
        """external_id 를 fetch_detail() 호출 인자로 변환."""
