"""
환경 변수 기반 설정 로더
.env 파일에서 값을 읽어 프로젝트 전체에 공유
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------
# PostgreSQL 연결 정보
# ----------------------------------------------------------
DB_HOST     = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT     = int(os.getenv("POSTGRES_PORT", "5432"))
DB_USER     = os.getenv("POSTGRES_USER", "apitest")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "apitest1234")
DB_NAME     = os.getenv("POSTGRES_DB", "api_collect")

# ----------------------------------------------------------
# 공공데이터포털 공통 API 키 (복지로, 서민금융진흥원)
# ----------------------------------------------------------
PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY", "")

# ----------------------------------------------------------
# 법제처 Open API OC 키 (현행법령, 판례)
# ----------------------------------------------------------
LAW_OC_KEY = os.getenv("LAW_OC_KEY", "")

# ----------------------------------------------------------
# 수집 제어
# ----------------------------------------------------------
COLLECT_PAGE_SIZE  = int(os.getenv("COLLECT_PAGE_SIZE", "10"))   # display 미지정 시 기본 페이지 크기
REQUEST_DELAY_SECS = float(os.getenv("REQUEST_DELAY_SECONDS", "0.5"))

# ----------------------------------------------------------
# API 엔드포인트 상수
# ----------------------------------------------------------

# 법제처 국가법령정보 Open API
LAW_SEARCH_URL  = "https://www.law.go.kr/DRF/lawSearch.do"   # 목록 조회
LAW_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"  # 본문 조회

# 공공데이터포털 복지로 — 중앙부처 (NationalWelfareInformationsV001)
WELFARE_CENTRAL_LIST_URL   = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001"
WELFARE_CENTRAL_DETAIL_URL = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfaredetailedV001"

# 공공데이터포털 복지로 — 지자체 (LocalGovernmentWelfareInformations)
WELFARE_LOCAL_LIST_URL   = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist"
WELFARE_LOCAL_DETAIL_URL = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfaredetailed"

# 공공데이터포털 서민금융진흥원 — 대출상품한눈에 정보조회 서비스
SMALL_LOAN_URL = "https://apis.data.go.kr/B553701/LoanProductSearchingInfo/LoanProductSearchingInfo/getLoanProductSearchingInfo"
