-- ============================================================
-- DMZ 수집 파이프라인 스키마
-- Discovery → Targeting → Sync 3단계 (외부망 → DMZ, Diff 전 원본 저장)
-- docker-entrypoint-initdb.d 로 컨테이너 최초 기동 시 자동 실행
-- (앱 기동 시 db.schema.ensure_schema() 가 동일 DDL 을 재확인)
-- ============================================================

-- ----------------------------------------------------------
-- 1. Discovery — 목록 API 후보 저장
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS collection_items (
    id               SERIAL PRIMARY KEY,
    source           VARCHAR(50)  NOT NULL,         -- law_text / precedent / welfare_* / small_loan
    external_id      VARCHAR(200) NOT NULL,         -- 법령MST, servId, seq 등 API 식별자
    title            TEXT,                          -- 법령명/서비스명/상품명 등
    list_payload     JSONB        NOT NULL,         -- 목록 API 응답 item 전체 (원본 보존)
    discovered_query JSONB,                         -- 실제 사용한 검색 조건 (null 제외)
    status           VARCHAR(20)  DEFAULT 'ACTIVE', -- ACTIVE / INACTIVE
    last_seen_at     TIMESTAMP    DEFAULT NOW(),
    created_at       TIMESTAMP    DEFAULT NOW(),
    updated_at       TIMESTAMP    DEFAULT NOW(),
    UNIQUE (source, external_id)
);

-- ----------------------------------------------------------
-- 2. Targeting — 정기 상세 수집 대상 마스터
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS collection_targets (
    id               SERIAL PRIMARY KEY,
    source           VARCHAR(50)  NOT NULL,
    external_id      VARCHAR(200) NOT NULL,
    title            TEXT,
    status           VARCHAR(20)  DEFAULT 'ACTIVE',  -- ACTIVE / PAUSED
    collect_detail   BOOLEAN      DEFAULT TRUE,       -- 상세 수집 여부
    last_detail_collected_at TIMESTAMP,               -- 마지막 sync 시각 (NULL=미수집)
    created_at       TIMESTAMP    DEFAULT NOW(),
    updated_at       TIMESTAMP    DEFAULT NOW(),
    UNIQUE (source, external_id)
);

-- ----------------------------------------------------------
-- 3. Sync — 상세 API 본문 저장 (RAG/검색 대상, 최신본)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id               SERIAL PRIMARY KEY,
    source           VARCHAR(50)  NOT NULL,
    external_id      VARCHAR(200) NOT NULL,
    title            TEXT,
    content_hash     VARCHAR(64),                   -- SHA256(normalized_text) — 변경 감지용
    raw_payload      JSONB        NOT NULL,          -- 상세 API 응답 원본 전체
    normalized_text  TEXT,                           -- RAG/검색용 정규화 본문
    metadata         JSONB,                          -- 제목·기관·날짜·분류·URL 등 구조화 메타
    version          INTEGER      DEFAULT 1,
    created_at       TIMESTAMP    DEFAULT NOW(),
    updated_at       TIMESTAMP    DEFAULT NOW(),
    UNIQUE (source, external_id)
);

-- ----------------------------------------------------------
-- 4. 변경 이력 — content_hash 가 달라진 경우 이전 버전 보존
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_versions (
    id               SERIAL PRIMARY KEY,
    document_id      INTEGER      REFERENCES documents(id),
    source           VARCHAR(50),
    external_id      VARCHAR(200),
    content_hash     VARCHAR(64),
    raw_payload      JSONB,
    normalized_text  TEXT,
    metadata         JSONB,
    version          INTEGER,
    created_at       TIMESTAMP    DEFAULT NOW()
);
