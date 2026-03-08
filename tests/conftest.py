"""
pytest 픽스처 정의
- db_session: 각 테스트마다 savepoint 트랜잭션을 시작하고 완료 후 롤백하여 DB 상태를 보전
- client: DB 의존성을 테스트 세션으로 교체한 FastAPI TestClient
"""

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.core.database import get_sync_db, sync_engine
from app.main import app


@pytest.fixture(scope="function")
def db_session():
    """
    테스트용 DB 세션
    - 외부 트랜잭션을 시작하고 내부에서는 savepoint로 처리
    - service 레이어의 commit()은 savepoint를 릴리즈하고 재생성하는 수준에서 동작
    - 테스트 종료 후 외부 트랜잭션을 롤백하여 모든 변경사항을 되돌림
    """
    connection = sync_engine.connect()
    trans = connection.begin()
    session = Session(connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session):
    """
    FastAPI TestClient 픽스처
    DB 의존성(get_sync_db)을 테스트 세션으로 교체하여 실제 Oracle DB를 사용하되
    각 테스트 종료 후 변경사항이 롤백되도록 보장
    """
    def override_get_sync_db():
        yield db_session

    app.dependency_overrides[get_sync_db] = override_get_sync_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼 픽스처
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def created_agent(client: TestClient) -> dict:
    """
    테스트용 에이전트를 신청하고 반환하는 픽스처
    기존 더미 데이터(user_a, ROLE_OWNER)를 신청자로 사용
    """
    payload = {
        "agent_name": "픽스처 테스트 에이전트",
        "description": "픽스처에서 생성된 테스트용 에이전트입니다.",
        "security_pledge": {"is_agreed": True},
        "members": [{"user_id": "user_a", "role_code": "ROLE_OWNER"}],
        "requested_by": "user_a",
    }
    response = client.post("/api/v1/agents", json=payload)
    assert response.status_code == 201
    return response.json()["data"]


@pytest.fixture
def approved_agent(client: TestClient, created_agent: dict) -> dict:
    """
    신청된 에이전트를 승인하여 운영중 상태로 만드는 픽스처
    """
    agent_id = created_agent["agent_id"]
    # 해당 에이전트의 대기 중인 요청 조회
    approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
    request_id = next(
        r["request_id"] for r in approvals if r["req_status_code"] == "REQ_STAT_WAIT"
    )
    # 승인 처리
    client.post(
        f"/api/v1/approvals/{request_id}/approve",
        json={"processed_by": "admin_1"},
    )
    # 최신 에이전트 정보 반환
    return client.get(f"/api/v1/agents/{agent_id}").json()["data"]


@pytest.fixture
def rejected_agent(client: TestClient, created_agent: dict) -> dict:
    """
    신청된 에이전트를 반려하여 반려됨 상태로 만드는 픽스처
    """
    agent_id = created_agent["agent_id"]
    approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
    request_id = next(
        r["request_id"] for r in approvals if r["req_status_code"] == "REQ_STAT_WAIT"
    )
    client.post(
        f"/api/v1/approvals/{request_id}/reject",
        json={"processed_by": "admin_1", "reject_reason": "테스트 반려 사유입니다."},
    )
    return client.get(f"/api/v1/agents/{agent_id}").json()["data"]
