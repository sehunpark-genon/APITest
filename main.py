"""
DMZ 수집 파이프라인 CLI
=======================
FastAPI(api.app) 서버 없이 터미널/배치(cron)에서 3단계 파이프라인을 실행한다.
HTTP 엔드포인트와 동일한 services 레이어(discover / register_targets / sync_details)를 호출한다.

사용법:
  uv run python main.py SOURCE STAGE [옵션]

  SOURCE : law_text | precedent | welfare_central | welfare_local | small_loan
  STAGE  : discover | targets | sync | all   (all = discover→targets→sync)

필터(--filter key=value, 복수)는 각 수집기 fetch_list() 파라미터명을 사용한다.
  law_text        : query, search, display, page, nw, sort, ef_yd, anc_yd, anc_no,
                    date, rr_cls_cd, nb, org, knd, gana, lid
  precedent       : query, search, display, court_org, court_name, ref_law, sort,
                    date, prnc_yd, case_no, data_src_nm, prec_type, gana
  welfare_central : search_word, srch_key_code, life_array, target_group, intr_thema,
                    age, online_apply_yn, order_by, display
  welfare_local   : region_name, city_name, search_word, srch_key_code, life_array,
                    target_group, intr_thema, age, sort_order, display
  small_loan      : irt_ctg, usge, inst_ctg, rsd_area, tgt_fltr, prd_ctg, display

예시:
  uv run python main.py law_text discover --filter query=근로기준법 --filter search=1
  uv run python main.py law_text targets --register-all
  uv run python main.py law_text sync --limit 20
  uv run python main.py law_text sync --force            # 이미 수집된 대상도 재수집
  uv run python main.py small_loan all --filter usge=생계  # 일괄 (discover→targets→sync)
"""

import argparse
import logging
import sys

from db.connection import get_connection
from db.schema import ensure_schema
from collectors.law_text.collector import LawTextCollector
from collectors.precedent.collector import PrecedentCollector
from collectors.welfare.central_collector import WelfareCentralCollector
from collectors.welfare.local_collector import WelfareLocalCollector
from collectors.small_loan.collector import SmallLoanCollector
from services.discovery import discover
from services.targeting import register_targets
from services.sync import sync_details

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")

COLLECTORS = {
    "law_text":        LawTextCollector,
    "precedent":       PrecedentCollector,
    "welfare_central": WelfareCentralCollector,
    "welfare_local":   WelfareLocalCollector,
    "small_loan":      SmallLoanCollector,
}


def parse_filters(filter_args: list[str]) -> dict:
    """--filter "key=value" 인자를 dict 로 변환 (모두 문자열)."""
    result = {}
    for f in filter_args or []:
        if "=" not in f:
            logger.warning("필터 형식 오류 (key=value 형식이어야 함): %s", f)
            continue
        key, _, value = f.partition("=")
        result[key.strip()] = value.strip()
    return result


def main():
    parser = argparse.ArgumentParser(
        description="DMZ 수집 파이프라인 CLI (discover / targets / sync)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", choices=list(COLLECTORS.keys()),
                        help="수집 도메인")
    parser.add_argument("stage", choices=["discover", "targets", "sync", "all"],
                        help="실행 단계 (all = discover→targets→sync)")
    parser.add_argument("--filter", action="append", dest="filters", metavar="KEY=VALUE",
                        help="discover 검색 필터 (key=value, 복수 가능)")
    parser.add_argument("--limit", type=int, default=None,
                        help="targets/sync 처리 최대 건수")
    parser.add_argument("--register-all", action="store_true",
                        help="targets: collection_items 전체 재등록")
    parser.add_argument("--force", action="store_true",
                        help="sync: 이미 수집된 대상도 상세 재호출 (force_resync)")
    parser.add_argument("--include-synced", action="store_true",
                        help="sync: pending 제한 해제 (전체 대상)")
    parser.add_argument("--stale-days", type=int, default=None,
                        help="sync: 마지막 동기화가 N일 경과한 대상도 재수집")
    args = parser.parse_args()

    source = args.source
    filters = parse_filters(args.filters)
    collector = COLLECTORS[source]()

    try:
        ensure_schema()
    except Exception as e:
        logger.error("DB 연결/스키마 실패: %s", e)
        logger.error("Docker 컨테이너 실행 여부 확인: docker compose up -d")
        sys.exit(1)

    conn = get_connection()
    fetched = 0
    try:
        if args.stage in ("discover", "all"):
            r = discover(source, collector, filters, conn)
            fetched = r.fetched_count
            logger.info("[discover] 수신 %d / 신규 %d / 갱신 %d",
                        r.fetched_count, r.inserted_count, r.updated_count)

        if args.stage in ("targets", "all"):
            r = register_targets(source, conn, limit=args.limit,
                                 register_all=(args.register_all or args.stage == "all"))
            logger.info("[targets] 신규 등록 %d / 스킵 %d / 전체 %d",
                        r.registered_count, r.skipped_count, r.target_count)

        if args.stage in ("sync", "all"):
            limit = args.limit or (fetched if args.stage == "all" else 5)
            r = sync_details(source, collector, conn,
                             limit=limit or 5,
                             pending_only=not args.include_synced,
                             force_resync=args.force,
                             stale_after_days=args.stale_days)
            logger.info("[sync] 처리 %d (신규 %d / 변경 %d / 동일 %d / 실패 %d) — "
                        "전체 target %d, 잔여 pending %d",
                        r.synced_count, r.inserted_count, r.updated_count,
                        r.unchanged_count, r.failed_count,
                        r.target_count, r.pending_count)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
