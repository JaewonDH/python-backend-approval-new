"""
에이전트 API 테스트
에이전트 신청, 재신청, 삭제 신청 등 에이전트 도메인 전체 테스트
"""

from starlette.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# 테스트 공통 요청 페이로드 상수
# ─────────────────────────────────────────────────────────────────────────────

AGENT_CREATE_PAYLOAD = {
    "agent_name": "테스트 에이전트",
    "description": "테스트용 에이전트 상세 설명입니다.",
    "security_pledge": {"is_agreed": True, "pledger": "user_a"},
    "members": [
        {"user_id": "user_a", "role_code": "ROLE_OWNER"},
        {"user_id": "user_b", "role_code": "ROLE_MEMBER"},
    ],
    "requested_by": "user_a",
}


class TestAgentsRead:
    """에이전트 조회 테스트"""

    def test_get_all_agents(self, client: TestClient):
        """전체 에이전트 목록 조회 - 더미 데이터 4건 이상 존재"""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert len(body["data"]) >= 4

    def test_get_agents_by_status_dev(self, client: TestClient):
        """운영중 에이전트 필터링 조회"""
        response = client.get("/api/v1/agents?status_code=AGT_STAT_DEV")
        assert response.status_code == 200
        agents = response.json()["data"]
        for agent in agents:
            assert agent["status_code"] == "AGT_STAT_DEV"

    def test_get_agents_by_status_cancelled(self, client: TestClient):
        """사용자취소 에이전트 필터링 조회 - AGT-300"""
        response = client.get("/api/v1/agents?status_code=AGT_STAT_CANCELLED")
        assert response.status_code == 200
        agents = response.json()["data"]
        assert len(agents) >= 1

    def test_get_agent_by_id_success(self, client: TestClient):
        """에이전트 상세 조회 - 더미 데이터 AGT-100 (운영중)"""
        response = client.get("/api/v1/agents/AGT-100")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["agent_id"] == "AGT-100"
        assert data["agent_name"] == "영업 지원 봇"
        assert data["status_code"] == "AGT_STAT_DEV"
        # code_name 반환 검증
        assert data["status_name"] == "운영중"
        assert "members" in data

    def test_get_agent_by_id_includes_members_with_role_name(self, client: TestClient):
        """에이전트 상세 조회 시 멤버 role_name 포함 확인"""
        response = client.get("/api/v1/agents/AGT-100")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["members"]) >= 1
        owner = data["members"][0]
        assert "role_code" in owner
        # role_name(code_name) 반환 검증
        assert owner["role_name"] is not None
        assert owner["role_name"] in ("대표(Owner)", "팀원(Member)")

    def test_get_agent_not_found(self, client: TestClient):
        """존재하지 않는 에이전트 조회 - 404 반환"""
        response = client.get("/api/v1/agents/NOT_EXIST_AGENT")
        assert response.status_code == 404


class TestAgentCreate:
    """에이전트 신청 테스트"""

    def test_create_agent_success(self, client: TestClient):
        """에이전트 신청 성공 - status_name(code_name) 포함 확인"""
        response = client.post("/api/v1/agents", json=AGENT_CREATE_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True

        agent = body["data"]
        assert agent["agent_name"] == "테스트 에이전트"
        assert agent["status_code"] == "AGT_STAT_PENDING"  # 신청 직후 승인대기 상태
        assert agent["status_name"] == "승인대기"             # code_name 반환 검증
        assert agent["created_by"] == "user_a"

    def test_create_agent_includes_members_with_role_name(self, client: TestClient):
        """에이전트 신청 시 멤버 role_name(code_name) 포함 확인"""
        response = client.post("/api/v1/agents", json=AGENT_CREATE_PAYLOAD)
        assert response.status_code == 201
        members = response.json()["data"]["members"]
        assert len(members) == 2
        member_ids = [m["user_id"] for m in members]
        assert "user_a" in member_ids
        assert "user_b" in member_ids
        # 모든 멤버에 role_name 포함 확인
        for m in members:
            assert m["role_name"] is not None

    def test_create_agent_creates_approval_request(self, client: TestClient):
        """에이전트 신청 시 승인 요청이 자동 생성됨"""
        response = client.post("/api/v1/agents", json=AGENT_CREATE_PAYLOAD)
        assert response.status_code == 201
        agent_id = response.json()["data"]["agent_id"]

        # 생성된 승인 요청 확인
        approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
        assert len(approvals) == 1
        approval = approvals[0]
        assert approval["req_category_code"] == "REQ_CAT_AGENT"
        assert approval["req_type_code"] == "REQ_TYP_CREATE"
        assert approval["req_status_code"] == "REQ_STAT_WAIT"

    def test_create_agent_security_pledge_stored(self, client: TestClient):
        """에이전트 신청 시 보안 서약 JSON이 저장됨"""
        response = client.post("/api/v1/agents", json=AGENT_CREATE_PAYLOAD)
        agent = response.json()["data"]
        assert agent["security_pledge"]["is_agreed"] is True

    def test_create_agent_missing_required_field(self, client: TestClient):
        """필수 필드 누락 - 422 반환"""
        payload = {
            "agent_name": "이름만 있는 에이전트",
            # description, security_pledge, requested_by 누락
        }
        response = client.post("/api/v1/agents", json=payload)
        assert response.status_code == 422


class TestAgentReapply:
    """에이전트 재신청 테스트"""

    def test_reapply_agent_success(self, client: TestClient, rejected_agent: dict):
        """반려된 에이전트 재신청 성공"""
        agent_id = rejected_agent["agent_id"]
        assert rejected_agent["status_code"] == "AGT_STAT_REJECTED"

        payload = {
            "agent_name": "재신청 에이전트 (보완)",
            "description": "반려 지적 사항을 반영하여 설명을 상세하게 보완하였습니다.",
            "security_pledge": {"is_agreed": True},
            "members": [{"user_id": "user_a", "role_code": "ROLE_OWNER"}],
            "request_reason": "관리자 지적 사항 반영 완료",
            "requested_by": "user_a",
        }
        response = client.post(f"/api/v1/agents/{agent_id}/reapply", json=payload)
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status_code"] == "AGT_STAT_PENDING"  # 재신청 후 승인대기
        assert data["description"] == "반려 지적 사항을 반영하여 설명을 상세하게 보완하였습니다."

    def test_reapply_agent_creates_recreate_request(self, client: TestClient, rejected_agent: dict):
        """재신청 시 REQ_TYP_RECREATE 타입 승인 요청 생성 확인"""
        agent_id = rejected_agent["agent_id"]
        payload = {
            "agent_name": "재신청 에이전트",
            "description": "보완된 설명",
            "security_pledge": {"is_agreed": True},
            "members": [{"user_id": "user_a", "role_code": "ROLE_OWNER"}],
            "request_reason": "보완 완료",
            "requested_by": "user_a",
        }
        client.post(f"/api/v1/agents/{agent_id}/reapply", json=payload)

        approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
        recreate_requests = [a for a in approvals if a["req_type_code"] == "REQ_TYP_RECREATE"]
        assert len(recreate_requests) == 1
        assert recreate_requests[0]["req_status_code"] == "REQ_STAT_WAIT"

    def test_reapply_agent_invalid_state_pending(self, client: TestClient, created_agent: dict):
        """승인대기 상태 에이전트 재신청 시도 - 400 반환"""
        agent_id = created_agent["agent_id"]
        assert created_agent["status_code"] == "AGT_STAT_PENDING"

        payload = {
            "agent_name": "잘못된 재신청",
            "description": "승인대기 상태에서 재신청 불가",
            "security_pledge": {"is_agreed": True},
            "members": [{"user_id": "user_a", "role_code": "ROLE_OWNER"}],
            "request_reason": "잘못된 재신청 시도",
            "requested_by": "user_a",
        }
        response = client.post(f"/api/v1/agents/{agent_id}/reapply", json=payload)
        assert response.status_code == 400

    def test_reapply_agent_not_found(self, client: TestClient):
        """존재하지 않는 에이전트 재신청 - 404 반환"""
        payload = {
            "agent_name": "없는 에이전트 재신청",
            "description": "설명",
            "security_pledge": {"is_agreed": True},
            "members": [],
            "request_reason": "사유",
            "requested_by": "user_a",
        }
        response = client.post("/api/v1/agents/NOT_EXIST/reapply", json=payload)
        assert response.status_code == 404


class TestAgentDeleteRequest:
    """에이전트 삭제 신청 테스트"""

    def test_request_delete_agent_success(self, client: TestClient, approved_agent: dict):
        """운영중 에이전트 삭제 신청 성공"""
        agent_id = approved_agent["agent_id"]
        assert approved_agent["status_code"] == "AGT_STAT_DEV"

        payload = {
            "request_reason": "V2 버전 출시로 기존 에이전트 삭제 요청",
            "requested_by": "user_a",
        }
        response = client.post(f"/api/v1/agents/{agent_id}/delete-request", json=payload)
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status_code"] == "AGT_STAT_DEL_PENDING"  # 삭제 심사중

    def test_request_delete_creates_delete_approval(self, client: TestClient, approved_agent: dict):
        """삭제 신청 시 REQ_TYP_DELETE 타입 승인 요청 생성 확인"""
        agent_id = approved_agent["agent_id"]
        client.post(
            f"/api/v1/agents/{agent_id}/delete-request",
            json={"request_reason": "삭제 사유", "requested_by": "user_a"},
        )

        approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
        delete_requests = [a for a in approvals if a["req_type_code"] == "REQ_TYP_DELETE"]
        assert len(delete_requests) == 1
        assert delete_requests[0]["req_status_code"] == "REQ_STAT_WAIT"

    def test_request_delete_invalid_state_pending(self, client: TestClient, created_agent: dict):
        """승인대기 상태 에이전트 삭제 신청 시도 - 400 반환"""
        agent_id = created_agent["agent_id"]
        assert created_agent["status_code"] == "AGT_STAT_PENDING"

        payload = {
            "request_reason": "잘못된 삭제 신청",
            "requested_by": "user_a",
        }
        response = client.post(f"/api/v1/agents/{agent_id}/delete-request", json=payload)
        assert response.status_code == 400

    def test_request_delete_not_found(self, client: TestClient):
        """존재하지 않는 에이전트 삭제 신청 - 404 반환"""
        response = client.post(
            "/api/v1/agents/NOT_EXIST/delete-request",
            json={"request_reason": "사유", "requested_by": "user_a"},
        )
        assert response.status_code == 404
