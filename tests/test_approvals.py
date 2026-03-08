"""
승인 요청 API 테스트
승인, 반려, 취소, 자원 증설 신청 등 승인 도메인 전체 테스트
"""

from starlette.testclient import TestClient


def _get_wait_request(client: TestClient, agent_id: str) -> str:
    """에이전트의 심사대기 요청 ID를 반환하는 헬퍼"""
    approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
    wait_requests = [a for a in approvals if a["req_status_code"] == "REQ_STAT_WAIT"]
    assert len(wait_requests) >= 1, f"에이전트 {agent_id}에 심사대기 요청이 없습니다."
    return wait_requests[0]["request_id"]


class TestApprovalsRead:
    """승인 요청 조회 테스트"""

    def test_get_all_approvals(self, client: TestClient):
        """전체 승인 요청 목록 조회 - 더미 데이터 5건 이상 존재"""
        response = client.get("/api/v1/approvals")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert len(body["data"]) >= 5

    def test_get_approvals_filter_by_status(self, client: TestClient):
        """요청 상태 필터 조회 - 심사대기"""
        response = client.get("/api/v1/approvals?req_status_code=REQ_STAT_WAIT")
        assert response.status_code == 200
        approvals = response.json()["data"]
        for a in approvals:
            assert a["req_status_code"] == "REQ_STAT_WAIT"

    def test_get_approvals_filter_by_category_agent(self, client: TestClient):
        """요청 카테고리 필터 조회 - 에이전트"""
        response = client.get("/api/v1/approvals?req_category_code=REQ_CAT_AGENT")
        assert response.status_code == 200
        approvals = response.json()["data"]
        for a in approvals:
            assert a["req_category_code"] == "REQ_CAT_AGENT"

    def test_get_approvals_filter_by_agent_id(self, client: TestClient):
        """에이전트 ID 필터 조회 - AGT-100 요청 이력"""
        response = client.get("/api/v1/approvals?agent_id=AGT-100")
        assert response.status_code == 200
        approvals = response.json()["data"]
        assert len(approvals) >= 2  # REQ-100-1, REQ-100-2
        for a in approvals:
            assert a["agent_id"] == "AGT-100"

    def test_get_approval_by_id_with_code_names(self, client: TestClient):
        """승인 요청 상세 조회 - code_name(_name 필드) 포함 확인"""
        response = client.get("/api/v1/approvals/REQ-100-1")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["request_id"] == "REQ-100-1"
        # code_name 반환 검증
        assert data["req_category_name"] == "에이전트"
        assert data["req_type_name"] == "신규/추가"
        assert data["req_status_name"] == "반려됨"
        # 스냅샷 포함 확인
        assert data["agent_info"] is not None
        assert data["agent_info"]["req_agent_name"] == "영업 지원 봇"
        assert len(data["member_infos"]) >= 1
        # 멤버 스냅샷의 role_name 확인
        for m in data["member_infos"]:
            assert m["role_name"] is not None

    def test_get_approval_resource_snapshot_with_code_names(self, client: TestClient):
        """자원 증설 승인 요청 상세 조회 - 코드명 및 자원 스냅샷 포함"""
        response = client.get("/api/v1/approvals/REQ-200-1")
        assert response.status_code == 200
        data = response.json()["data"]
        # code_name 반환 검증
        assert data["req_category_name"] == "자원"
        assert data["req_status_name"] == "심사대기"
        assert data["resource_info"] is not None
        assert data["resource_info"]["req_cpu"] == 4
        assert data["resource_info"]["req_gpu"] == 1

    def test_get_approval_not_found(self, client: TestClient):
        """존재하지 않는 승인 요청 조회 - 404 반환"""
        response = client.get("/api/v1/approvals/NOT_EXIST_REQ")
        assert response.status_code == 404


class TestApproveAction:
    """승인 처리 테스트"""

    def test_approve_agent_create_request(self, client: TestClient, created_agent: dict):
        """에이전트 신청 승인 → req_status_name(code_name) 포함 확인"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},
        )
        assert response.status_code == 200
        approval = response.json()["data"]
        assert approval["req_status_code"] == "REQ_STAT_APPROVED"
        assert approval["req_status_name"] == "승인완료"        # code_name 반환 검증
        assert approval["req_category_name"] == "에이전트"       # code_name 반환 검증
        assert approval["req_type_name"] == "신규/추가"           # code_name 반환 검증
        assert approval["processed_by"] == "admin_1"
        assert approval["processed_at"] is not None

        # 에이전트 상태 운영중 확인
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_DEV"

    def test_approve_agent_delete_request(self, client: TestClient, approved_agent: dict):
        """에이전트 삭제 신청 승인 → 에이전트 상태 삭제완료로 전환"""
        agent_id = approved_agent["agent_id"]

        # 삭제 신청
        client.post(
            f"/api/v1/agents/{agent_id}/delete-request",
            json={"request_reason": "테스트 삭제", "requested_by": "user_a"},
        )

        # 삭제 승인 요청 ID 조회
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_2"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["req_status_code"] == "REQ_STAT_APPROVED"

        # 에이전트 상태 삭제완료 확인
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_DELETED"

    def test_approve_resource_request_with_assignment(self, client: TestClient, approved_agent: dict):
        """자원 증설 승인 - 자원 정보 직접 할당"""
        agent_id = approved_agent["agent_id"]

        # 자원 증설 신청
        client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 8,
                "req_memory": "32GB",
                "req_gpu": 2,
                "request_reason": "트래픽 급증",
                "requested_by": "user_a",
            },
        )

        request_id = _get_wait_request(client, agent_id)
        resource_to_assign = {"cpu": 8, "memory": "32GB", "gpu": 2}

        response = client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1", "resource_to_assign": resource_to_assign},
        )
        assert response.status_code == 200

        # 에이전트 현재 자원 갱신 확인
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["current_resource"]["cpu"] == 8
        assert agent["current_resource"]["memory"] == "32GB"

    def test_approve_resource_request_from_snapshot(self, client: TestClient, approved_agent: dict):
        """자원 증설 승인 - 스냅샷 정보로 자동 할당 (resource_to_assign 미전달)"""
        agent_id = approved_agent["agent_id"]

        client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 4,
                "req_memory": "16GB",
                "request_reason": "자동 할당 테스트",
                "requested_by": "user_a",
            },
        )

        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},  # resource_to_assign 없음
        )
        assert response.status_code == 200

        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["current_resource"] is not None
        assert "cpu" in agent["current_resource"]

    def test_approve_already_processed_request(self, client: TestClient, created_agent: dict):
        """이미 처리된 요청 승인 시도 - 400 반환"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        # 1차 승인
        client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},
        )
        # 2차 승인 시도 → 이미 처리됨
        response = client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},
        )
        assert response.status_code == 400

    def test_approve_not_found_request(self, client: TestClient):
        """존재하지 않는 요청 승인 시도 - 404 반환"""
        response = client.post(
            "/api/v1/approvals/NOT_EXIST/approve",
            json={"processed_by": "admin_1"},
        )
        assert response.status_code == 404


class TestRejectAction:
    """반려 처리 테스트"""

    def test_reject_agent_create_request(self, client: TestClient, created_agent: dict):
        """에이전트 신청 반려 → req_status_name(code_name) 포함 확인"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/reject",
            json={"processed_by": "admin_1", "reject_reason": "사용 목적이 불명확합니다."},
        )
        assert response.status_code == 200
        approval = response.json()["data"]
        assert approval["req_status_code"] == "REQ_STAT_REJECTED"
        assert approval["req_status_name"] == "반려됨"           # code_name 반환 검증
        assert approval["reject_reason"] == "사용 목적이 불명확합니다."

        # 에이전트 상태 반려됨 확인
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_REJECTED"

    def test_reject_agent_delete_request_restores_dev(self, client: TestClient, approved_agent: dict):
        """에이전트 삭제 신청 반려 → 에이전트 상태 운영중으로 복원"""
        agent_id = approved_agent["agent_id"]

        # 삭제 신청
        client.post(
            f"/api/v1/agents/{agent_id}/delete-request",
            json={"request_reason": "삭제 사유", "requested_by": "user_a"},
        )
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/reject",
            json={"processed_by": "admin_1", "reject_reason": "삭제 불가. 현재 사용 중인 에이전트입니다."},
        )
        assert response.status_code == 200

        # 에이전트 상태 운영중으로 복원 확인
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_DEV"

    def test_reject_resource_request_keeps_agent_status(self, client: TestClient, approved_agent: dict):
        """자원 증설 반려 → 에이전트 상태 변경 없음 (운영중 유지)"""
        agent_id = approved_agent["agent_id"]

        client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 16,
                "request_reason": "과도한 자원 요청 테스트",
                "requested_by": "user_a",
            },
        )
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/reject",
            json={"processed_by": "admin_2", "reject_reason": "자원 한도 초과입니다."},
        )
        assert response.status_code == 200

        # 에이전트 상태 운영중 유지 확인 (자원 반려이므로 변경 없음)
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_DEV"

    def test_reject_already_processed_request(self, client: TestClient, created_agent: dict):
        """이미 처리된 요청 반려 시도 - 400 반환"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        # 먼저 승인 처리
        client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},
        )
        # 이후 반려 시도
        response = client.post(
            f"/api/v1/approvals/{request_id}/reject",
            json={"processed_by": "admin_1", "reject_reason": "이미 처리됨"},
        )
        assert response.status_code == 400

    def test_reject_missing_reason(self, client: TestClient, created_agent: dict):
        """반려 사유 없이 반려 시도 - 422 반환"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/reject",
            json={"processed_by": "admin_1"},  # reject_reason 누락
        )
        assert response.status_code == 422


class TestCancelAction:
    """취소 처리 테스트"""

    def test_cancel_request_success(self, client: TestClient, created_agent: dict):
        """본인 신청 취소 성공 → req_status_name(code_name) 포함 확인"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/cancel",
            json={"requested_by": "user_a"},
        )
        assert response.status_code == 200
        approval = response.json()["data"]
        assert approval["req_status_code"] == "REQ_STAT_CANCELLED"
        assert approval["req_status_name"] == "요청취소"          # code_name 반환 검증

        # 에이전트 상태 사용자취소 확인
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_CANCELLED"

    def test_cancel_by_other_user_forbidden(self, client: TestClient, created_agent: dict):
        """타인의 요청 취소 시도 - 403 반환"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/cancel",
            json={"requested_by": "user_b"},  # 신청자(user_a)가 아닌 다른 사용자
        )
        assert response.status_code == 403

    def test_cancel_already_cancelled(self, client: TestClient, created_agent: dict):
        """이미 취소된 요청 재취소 시도 - 400 반환"""
        agent_id = created_agent["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        # 1차 취소
        client.post(
            f"/api/v1/approvals/{request_id}/cancel",
            json={"requested_by": "user_a"},
        )
        # 2차 취소 시도
        response = client.post(
            f"/api/v1/approvals/{request_id}/cancel",
            json={"requested_by": "user_a"},
        )
        assert response.status_code == 400

    def test_cancel_resource_request_keeps_agent_dev(self, client: TestClient, approved_agent: dict):
        """자원 증설 요청 취소 → 에이전트 상태 운영중 유지"""
        agent_id = approved_agent["agent_id"]

        client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 4,
                "request_reason": "취소할 자원 신청",
                "requested_by": "user_a",
            },
        )
        request_id = _get_wait_request(client, agent_id)

        response = client.post(
            f"/api/v1/approvals/{request_id}/cancel",
            json={"requested_by": "user_a"},
        )
        assert response.status_code == 200

        # 에이전트 상태 운영중 유지 (자원 취소이므로 변경 없음)
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_DEV"


class TestResourceRequest:
    """자원 증설 신청 테스트"""

    def test_create_resource_request_success(self, client: TestClient, approved_agent: dict):
        """운영중 에이전트 자원 증설 신청 성공"""
        agent_id = approved_agent["agent_id"]

        payload = {
            "req_cpu": 8,
            "req_memory": "32GB",
            "req_gpu": 1,
            "request_reason": "해외 법인 오픈으로 트래픽 급증",
            "requested_by": "user_a",
        }
        response = client.post(f"/api/v1/agents/{agent_id}/resources", json=payload)
        assert response.status_code == 201
        approval = response.json()["data"]
        assert approval["req_category_code"] == "REQ_CAT_RESOURCE"
        assert approval["req_type_code"] == "REQ_TYP_CREATE"
        assert approval["req_status_code"] == "REQ_STAT_WAIT"

    def test_create_resource_request_snapshot_stored(self, client: TestClient, approved_agent: dict):
        """자원 증설 신청 시 REQ_RESOURCE_INFO 스냅샷 저장 확인"""
        agent_id = approved_agent["agent_id"]

        client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 4,
                "req_memory": "16GB",
                "req_gpu": 2,
                "request_reason": "스냅샷 저장 확인 테스트",
                "requested_by": "user_a",
            },
        )

        # 승인 요청 상세에서 스냅샷 확인
        request_id = _get_wait_request(client, agent_id)
        detail = client.get(f"/api/v1/approvals/{request_id}").json()["data"]
        assert detail["resource_info"] is not None
        assert detail["resource_info"]["req_cpu"] == 4
        assert detail["resource_info"]["req_memory"] == "16GB"
        assert detail["resource_info"]["req_gpu"] == 2

    def test_create_resource_request_not_dev_status(self, client: TestClient, created_agent: dict):
        """운영중이 아닌 에이전트(승인대기)에 자원 증설 신청 시도 - 400 반환"""
        agent_id = created_agent["agent_id"]
        assert created_agent["status_code"] == "AGT_STAT_PENDING"

        response = client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 4,
                "request_reason": "잘못된 자원 신청",
                "requested_by": "user_a",
            },
        )
        assert response.status_code == 400

    def test_create_resource_request_agent_not_found(self, client: TestClient):
        """존재하지 않는 에이전트에 자원 증설 신청 - 404 반환"""
        response = client.post(
            "/api/v1/agents/NOT_EXIST/resources",
            json={
                "req_cpu": 4,
                "request_reason": "없는 에이전트 신청",
                "requested_by": "user_a",
            },
        )
        assert response.status_code == 404

    def test_create_resource_request_missing_reason(self, client: TestClient, approved_agent: dict):
        """자원 증설 사유 누락 - 422 반환"""
        agent_id = approved_agent["agent_id"]

        response = client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 4,
                # request_reason 누락
                "requested_by": "user_a",
            },
        )
        assert response.status_code == 422
