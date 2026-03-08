"""
Oracle DB 초기화 스크립트
테이블 생성 및 더미 데이터를 삽입한다.
프로젝트 루트에서 실행: py -3.12 scripts/init_db.py
"""

import oracledb

# ─────────────────────────────────────────────────────────────────────────────
# DB 접속 정보
# ─────────────────────────────────────────────────────────────────────────────

HOST = "localhost"
PORT = 1521
SERVICE = "FREEPDB1"
USER = "myuser"
PASSWORD = "mypassword"

# ─────────────────────────────────────────────────────────────────────────────
# DDL / DML 구문 목록 (순서 중요)
# ─────────────────────────────────────────────────────────────────────────────

DROP_STATEMENTS = [
    "DROP TRIGGER TRG_AGENTS_UPDATED_AT",
    "DROP TABLE REQ_RESOURCE_INFO CASCADE CONSTRAINTS",
    "DROP TABLE REQ_MEMBERS_INFO CASCADE CONSTRAINTS",
    "DROP TABLE REQ_AGENT_INFO CASCADE CONSTRAINTS",
    "DROP TABLE APPROVAL_REQUESTS CASCADE CONSTRAINTS",
    "DROP TABLE AGENT_MEMBERS CASCADE CONSTRAINTS",
    "DROP TABLE AGENTS CASCADE CONSTRAINTS",
    "DROP TABLE USERS CASCADE CONSTRAINTS",
    "DROP TABLE COMMON_CODES CASCADE CONSTRAINTS",
]

CREATE_STATEMENTS = [
    # 공통 코드 테이블
    """
    CREATE TABLE COMMON_CODES (
        code_id      VARCHAR2(50)  PRIMARY KEY,
        group_code   VARCHAR2(50)  NOT NULL,
        code_name    VARCHAR2(100) NOT NULL,
        sort_order   NUMBER        DEFAULT 0,
        is_active    VARCHAR2(1)   DEFAULT 'Y' CHECK (is_active IN ('Y', 'N')),
        description  VARCHAR2(255),
        created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP NOT NULL
    )
    """,
    # 사용자 마스터 테이블
    """
    CREATE TABLE USERS (
        user_id      VARCHAR2(50)  PRIMARY KEY,
        user_name    VARCHAR2(100) NOT NULL,
        department   VARCHAR2(100),
        email        VARCHAR2(100),
        system_role  VARCHAR2(20)  DEFAULT 'USER'
                         CHECK (system_role IN ('USER', 'ADMIN')),
        created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP NOT NULL
    )
    """,
    # 에이전트 마스터 테이블
    """
    CREATE TABLE AGENTS (
        agent_id         VARCHAR2(50)  PRIMARY KEY,
        agent_name       VARCHAR2(100) NOT NULL,
        description      CLOB          NOT NULL,
        status_code      VARCHAR2(50)  NOT NULL,
        current_resource CLOB          CHECK (current_resource IS JSON),
        security_pledge  CLOB          CHECK (security_pledge IS JSON),
        created_by       VARCHAR2(50)  NOT NULL,
        created_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP NOT NULL,
        CONSTRAINT fk_agents_status  FOREIGN KEY (status_code)  REFERENCES COMMON_CODES(code_id),
        CONSTRAINT fk_agents_creator FOREIGN KEY (created_by)   REFERENCES USERS(user_id)
    )
    """,
    # updated_at 자동 갱신 트리거
    """
    CREATE OR REPLACE TRIGGER TRG_AGENTS_UPDATED_AT
    BEFORE UPDATE ON AGENTS
    FOR EACH ROW
    BEGIN
        :NEW.updated_at := CURRENT_TIMESTAMP;
    END;
    """,
    # 에이전트 참여 멤버 테이블
    """
    CREATE TABLE AGENT_MEMBERS (
        agent_id   VARCHAR2(50) NOT NULL,
        user_id    VARCHAR2(50) NOT NULL,
        role_code  VARCHAR2(50) NOT NULL,
        created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP NOT NULL,
        PRIMARY KEY (agent_id, user_id),
        CONSTRAINT fk_members_agent FOREIGN KEY (agent_id)   REFERENCES AGENTS(agent_id)       ON DELETE CASCADE,
        CONSTRAINT fk_members_role  FOREIGN KEY (role_code)  REFERENCES COMMON_CODES(code_id),
        CONSTRAINT fk_members_user  FOREIGN KEY (user_id)    REFERENCES USERS(user_id)
    )
    """,
    # 통합 승인 요청 이력
    """
    CREATE TABLE APPROVAL_REQUESTS (
        request_id        VARCHAR2(50) PRIMARY KEY,
        agent_id          VARCHAR2(50) NOT NULL,
        req_category_code VARCHAR2(50) NOT NULL,
        req_type_code     VARCHAR2(50) NOT NULL,
        req_status_code   VARCHAR2(50) NOT NULL,
        requested_by      VARCHAR2(50) NOT NULL,
        requested_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP NOT NULL,
        processed_by      VARCHAR2(50),
        processed_at      TIMESTAMP,
        reject_reason     CLOB,
        CONSTRAINT fk_req_agent    FOREIGN KEY (agent_id)          REFERENCES AGENTS(agent_id)       ON DELETE CASCADE,
        CONSTRAINT fk_req_cat      FOREIGN KEY (req_category_code) REFERENCES COMMON_CODES(code_id),
        CONSTRAINT fk_req_typ      FOREIGN KEY (req_type_code)     REFERENCES COMMON_CODES(code_id),
        CONSTRAINT fk_req_stat     FOREIGN KEY (req_status_code)   REFERENCES COMMON_CODES(code_id),
        CONSTRAINT fk_req_req_by   FOREIGN KEY (requested_by)      REFERENCES USERS(user_id),
        CONSTRAINT fk_req_proc_by  FOREIGN KEY (processed_by)      REFERENCES USERS(user_id)
    )
    """,
    # 인덱스
    "CREATE INDEX IDX_APPROVAL_SEARCH ON APPROVAL_REQUESTS (req_status_code, req_category_code, req_type_code)",
    "CREATE INDEX IDX_APPROVAL_AGENT  ON APPROVAL_REQUESTS (agent_id, requested_at DESC)",
    # 에이전트 신청/삭제 정보 스냅샷
    """
    CREATE TABLE REQ_AGENT_INFO (
        request_id       VARCHAR2(50)  PRIMARY KEY,
        req_agent_name   VARCHAR2(100) NOT NULL,
        req_description  CLOB          NOT NULL,
        request_reason   CLOB,
        req_security_pledge CLOB       CHECK (req_security_pledge IS JSON),
        CONSTRAINT fk_info_req FOREIGN KEY (request_id) REFERENCES APPROVAL_REQUESTS(request_id) ON DELETE CASCADE
    )
    """,
    # 멤버 스냅샷
    """
    CREATE TABLE REQ_MEMBERS_INFO (
        request_id VARCHAR2(50) NOT NULL,
        user_id    VARCHAR2(50) NOT NULL,
        role_code  VARCHAR2(50) NOT NULL,
        PRIMARY KEY (request_id, user_id),
        CONSTRAINT fk_mem_info_req  FOREIGN KEY (request_id) REFERENCES APPROVAL_REQUESTS(request_id) ON DELETE CASCADE,
        CONSTRAINT fk_mem_info_role FOREIGN KEY (role_code)  REFERENCES COMMON_CODES(code_id),
        CONSTRAINT fk_mem_info_user FOREIGN KEY (user_id)    REFERENCES USERS(user_id)
    )
    """,
    # 자원 정보 스냅샷
    """
    CREATE TABLE REQ_RESOURCE_INFO (
        request_id     VARCHAR2(50) PRIMARY KEY,
        req_cpu        NUMBER,
        req_memory     VARCHAR2(20),
        req_gpu        NUMBER,
        request_reason CLOB         NOT NULL,
        CONSTRAINT fk_res_info_req FOREIGN KEY (request_id) REFERENCES APPROVAL_REQUESTS(request_id) ON DELETE CASCADE
    )
    """,
]

INSERT_STATEMENTS = [
    # 공통 코드 - 에이전트 상태
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('AGT_STAT_PENDING',     'AGT_STAT', '승인대기',   1)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('AGT_STAT_DEV',         'AGT_STAT', '운영중',     2)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('AGT_STAT_REJECTED',    'AGT_STAT', '반려됨',     3)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('AGT_STAT_CANCELLED',   'AGT_STAT', '사용자취소', 4)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('AGT_STAT_DEL_PENDING', 'AGT_STAT', '삭제심사중', 5)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('AGT_STAT_DELETED',     'AGT_STAT', '삭제완료',   6)",
    # 공통 코드 - 역할
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('ROLE_OWNER',  'ROLE', '대표(Owner)',   1)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('ROLE_MEMBER', 'ROLE', '팀원(Member)', 2)",
    # 공통 코드 - 요청 카테고리
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_CAT_AGENT',    'REQ_CAT', '에이전트', 1)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_CAT_RESOURCE', 'REQ_CAT', '자원',     2)",
    # 공통 코드 - 요청 유형
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_TYP_CREATE',   'REQ_TYP', '신규/추가', 1)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_TYP_RECREATE', 'REQ_TYP', '재신청',   2)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_TYP_DELETE',   'REQ_TYP', '삭제/축소', 3)",
    # 공통 코드 - 요청 상태
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_STAT_WAIT',      'REQ_STAT', '심사대기',   1)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_STAT_APPROVED',  'REQ_STAT', '승인완료',   2)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_STAT_REJECTED',  'REQ_STAT', '반려됨',     3)",
    "INSERT INTO COMMON_CODES (code_id, group_code, code_name, sort_order) VALUES ('REQ_STAT_CANCELLED', 'REQ_STAT', '요청취소',   4)",
    # 사용자
    "INSERT INTO USERS (user_id, user_name, department, email, system_role) VALUES ('user_a', '김사원', '영업1팀',   'user_a@company.com', 'USER')",
    "INSERT INTO USERS (user_id, user_name, department, email, system_role) VALUES ('user_b', '이대리', '해외사업팀', 'user_b@company.com', 'USER')",
    "INSERT INTO USERS (user_id, user_name, department, email, system_role) VALUES ('user_c', '박과장', '기획팀',    'user_c@company.com', 'USER')",
    "INSERT INTO USERS (user_id, user_name, department, email, system_role) VALUES ('user_d', '정차장', '개발팀',    'user_d@company.com', 'USER')",
    "INSERT INTO USERS (user_id, user_name, department, email, system_role) VALUES ('admin_1', '최관리', 'IT인프라팀', 'admin_1@company.com', 'ADMIN')",
    "INSERT INTO USERS (user_id, user_name, department, email, system_role) VALUES ('admin_2', '강보안', '정보보안팀', 'admin_2@company.com', 'ADMIN')",
    # ── 시나리오 1: 반려 후 재신청 및 최종 승인 ──────────────────────────────
    "INSERT INTO AGENTS (agent_id, agent_name, description, status_code, security_pledge, created_by, created_at) VALUES ('AGT-100', '영업 지원 봇', '영업팀 보고서 요약 챗봇입니다.', 'AGT_STAT_DEV', '{\"is_agreed\": true}', 'user_a', TO_TIMESTAMP('2026-03-09 09:00:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "UPDATE AGENTS SET current_resource = '{\"cpu\": 2, \"memory\": \"8GB\"}' WHERE agent_id = 'AGT-100'",
    "INSERT INTO AGENT_MEMBERS (agent_id, user_id, role_code) VALUES ('AGT-100', 'user_a', 'ROLE_OWNER')",
    "INSERT INTO APPROVAL_REQUESTS (request_id, agent_id, req_category_code, req_type_code, req_status_code, requested_by, requested_at, processed_by, processed_at, reject_reason) VALUES ('REQ-100-1', 'AGT-100', 'REQ_CAT_AGENT', 'REQ_TYP_CREATE', 'REQ_STAT_REJECTED', 'user_a', TO_TIMESTAMP('2026-03-09 09:00:00', 'YYYY-MM-DD HH24:MI:SS'), 'admin_1', TO_TIMESTAMP('2026-03-09 09:30:00', 'YYYY-MM-DD HH24:MI:SS'), '사용 목적과 프롬프트를 상세히 적어주세요.')",
    "INSERT INTO REQ_AGENT_INFO (request_id, req_agent_name, req_description, req_security_pledge) VALUES ('REQ-100-1', '영업 지원 봇', '영업팀 문서 요약용', '{\"is_agreed\": true}')",
    "INSERT INTO REQ_MEMBERS_INFO (request_id, user_id, role_code) VALUES ('REQ-100-1', 'user_a', 'ROLE_OWNER')",
    "INSERT INTO APPROVAL_REQUESTS (request_id, agent_id, req_category_code, req_type_code, req_status_code, requested_by, requested_at, processed_by, processed_at) VALUES ('REQ-100-2', 'AGT-100', 'REQ_CAT_AGENT', 'REQ_TYP_RECREATE', 'REQ_STAT_APPROVED', 'user_a', TO_TIMESTAMP('2026-03-09 10:00:00', 'YYYY-MM-DD HH24:MI:SS'), 'admin_1', TO_TIMESTAMP('2026-03-09 10:30:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "INSERT INTO REQ_AGENT_INFO (request_id, req_agent_name, req_description, request_reason, req_security_pledge) VALUES ('REQ-100-2', '영업 지원 봇', '영업팀 보고서 요약 챗봇입니다.', '설명 상세 보완하여 재신청', '{\"is_agreed\": true}')",
    "INSERT INTO REQ_MEMBERS_INFO (request_id, user_id, role_code) VALUES ('REQ-100-2', 'user_a', 'ROLE_OWNER')",
    # ── 시나리오 2: 운영 중 자원 증설 신청 ──────────────────────────────────
    "INSERT INTO AGENTS (agent_id, agent_name, description, status_code, current_resource, created_by, created_at) VALUES ('AGT-200', '글로벌 번역 봇', '다국어 번역 봇', 'AGT_STAT_DEV', '{\"cpu\": 2, \"gpu\": 0}', 'user_b', TO_TIMESTAMP('2026-01-01 09:00:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "INSERT INTO AGENT_MEMBERS (agent_id, user_id, role_code) VALUES ('AGT-200', 'user_b', 'ROLE_OWNER')",
    "INSERT INTO APPROVAL_REQUESTS (request_id, agent_id, req_category_code, req_type_code, req_status_code, requested_by, requested_at) VALUES ('REQ-200-1', 'AGT-200', 'REQ_CAT_RESOURCE', 'REQ_TYP_CREATE', 'REQ_STAT_WAIT', 'user_b', TO_TIMESTAMP('2026-03-09 13:00:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "INSERT INTO REQ_RESOURCE_INFO (request_id, req_cpu, req_gpu, request_reason) VALUES ('REQ-200-1', 4, 1, '해외 법인 오픈으로 트래픽 급증하여 GPU 추가 요청합니다.')",
    # ── 시나리오 3: 사용자의 자의적 신청 취소 ────────────────────────────────
    "INSERT INTO AGENTS (agent_id, agent_name, description, status_code, created_by, created_at) VALUES ('AGT-300', '테스트 봇', '잘못 신청함', 'AGT_STAT_CANCELLED', 'user_c', TO_TIMESTAMP('2026-03-09 15:00:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "INSERT INTO APPROVAL_REQUESTS (request_id, agent_id, req_category_code, req_type_code, req_status_code, requested_by, requested_at, processed_at) VALUES ('REQ-300-1', 'AGT-300', 'REQ_CAT_AGENT', 'REQ_TYP_CREATE', 'REQ_STAT_CANCELLED', 'user_c', TO_TIMESTAMP('2026-03-09 15:00:00', 'YYYY-MM-DD HH24:MI:SS'), TO_TIMESTAMP('2026-03-09 15:10:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "INSERT INTO REQ_AGENT_INFO (request_id, req_agent_name, req_description) VALUES ('REQ-300-1', '테스트 봇', '잘못 신청함')",
    # ── 시나리오 4: 운영 중 에이전트 완전 삭제 ───────────────────────────────
    "INSERT INTO AGENTS (agent_id, agent_name, description, status_code, created_by, created_at) VALUES ('AGT-400', '구형 날씨 봇', '안 쓰는 봇', 'AGT_STAT_DEL_PENDING', 'user_d', TO_TIMESTAMP('2025-10-01 09:00:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "INSERT INTO AGENT_MEMBERS (agent_id, user_id, role_code) VALUES ('AGT-400', 'user_d', 'ROLE_OWNER')",
    "INSERT INTO APPROVAL_REQUESTS (request_id, agent_id, req_category_code, req_type_code, req_status_code, requested_by, requested_at) VALUES ('REQ-400-1', 'AGT-400', 'REQ_CAT_AGENT', 'REQ_TYP_DELETE', 'REQ_STAT_WAIT', 'user_d', TO_TIMESTAMP('2026-03-09 16:00:00', 'YYYY-MM-DD HH24:MI:SS'))",
    "INSERT INTO REQ_AGENT_INFO (request_id, req_agent_name, req_description, request_reason) VALUES ('REQ-400-1', '구형 날씨 봇', '안 쓰는 봇', 'V2 버전이 출시되어 기존 봇은 삭제합니다.')",
]


def run_sql(cursor: oracledb.Cursor, sql: str, ignore_errors: tuple = ()) -> bool:
    """SQL 실행. ignore_errors 코드 목록에 해당하는 오류는 무시한다."""
    sql = sql.strip()
    if not sql:
        return True
    try:
        cursor.execute(sql)
        return True
    except oracledb.DatabaseError as e:
        (error,) = e.args
        if any(str(ignore_code) in str(error.code) for ignore_code in ignore_errors):
            return True
        print(f"  [오류] {error.code}: {error.message.strip()}")
        print(f"  SQL: {sql[:80]}...")
        return False


def main() -> None:
    dsn = f"{HOST}:{PORT}/{SERVICE}"
    print(f"Oracle DB 접속 중: {USER}@{dsn}")

    with oracledb.connect(user=USER, password=PASSWORD, dsn=dsn) as conn:
        cursor = conn.cursor()

        # ── Step 1: 기존 테이블 삭제 ──────────────────────────────────────
        print("\n[1/3] 기존 테이블/트리거 삭제 중...")
        for stmt in DROP_STATEMENTS:
            # ORA-00942 (테이블 없음), ORA-04080 (트리거 없음) 무시
            run_sql(cursor, stmt, ignore_errors=(942, 4080))

        # ── Step 2: 테이블 생성 ───────────────────────────────────────────
        print("\n[2/3] 테이블 생성 중...")
        for stmt in CREATE_STATEMENTS:
            ok = run_sql(cursor, stmt)
            if not ok:
                conn.rollback()
                raise SystemExit("테이블 생성 실패. 초기화를 중단합니다.")

        # ── Step 3: 더미 데이터 삽입 ─────────────────────────────────────
        print("\n[3/3] 더미 데이터 삽입 중...")
        for stmt in INSERT_STATEMENTS:
            ok = run_sql(cursor, stmt)
            if not ok:
                conn.rollback()
                raise SystemExit("데이터 삽입 실패. 초기화를 중단합니다.")

        conn.commit()
        print("\nDB 초기화 완료!")


if __name__ == "__main__":
    main()
