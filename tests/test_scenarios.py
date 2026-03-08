"""
E2E 시나리오 테스트
DDL에 명시된 4가지 시나리오를 API 호출 순서대로 재현하여 전체 흐름을 검증한다.
"""

from starlette.testclient import TestClient


def _get_wait_request(client: TestClient, agent_id: str) -> str:
    """에이전트의 심사대기 요청 ID를 반환하는 헬퍼"""
    approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
    wait_requests = [a for a in approvals if a["req_status_code"] == "REQ_STAT_WAIT"]
    assert len(wait_requests) >= 1
    return wait_requests[0]["request_id"]


class TestScenario1_RejectAndReapply:
    """
    시나리오 1: 반려 후 재신청 및 최종 승인
    흐름: 에이전트 신청 → 관리자 반려 → 사용자 재신청 → 관리자 최종 승인
    """

    def test_full_flow_reject_and_reapply(self, client: TestClient):
        """반려 후 재신청 전체 흐름 테스트"""

        # ── Step 1: 에이전트 최초 신청 ──────────────────────────────────────────
        create_resp = client.post(
            "/api/v1/agents",
            json={
                "agent_name": "시나리오1 영업 지원 봇",
                "description": "영업팀 문서 요약용",
                "security_pledge": {"is_agreed": True},
                "members": [{"user_id": "user_a", "role_code": "ROLE_OWNER"}],
                "requested_by": "user_a",
            },
        )
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["data"]["agent_id"]
        assert create_resp.json()["data"]["status_code"] == "AGT_STAT_PENDING"

        # ── Step 2: 관리자 반려 처리 ─────────────────────────────────────────
        request_id_1 = _get_wait_request(client, agent_id)
        reject_resp = client.post(
            f"/api/v1/approvals/{request_id_1}/reject",
            json={
                "processed_by": "admin_1",
                "reject_reason": "사용 목적과 프롬프트를 상세히 적어주세요.",
            },
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["data"]["req_status_code"] == "REQ_STAT_REJECTED"

        # 에이전트 상태 반려됨 확인
        agent_state = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent_state["status_code"] == "AGT_STAT_REJECTED"

        # ── Step 3: 사용자 재신청 ────────────────────────────────────────────
        reapply_resp = client.post(
            f"/api/v1/agents/{agent_id}/reapply",
            json={
                "agent_name": "시나리오1 영업 지원 봇",
                "description": "영업팀의 월간 보고서 및 미팅 회의록을 요약하는 전용 챗봇입니다.",
                "security_pledge": {"is_agreed": True},
                "members": [{"user_id": "user_a", "role_code": "ROLE_OWNER"}],
                "request_reason": "설명 상세 보완하여 재신청",
                "requested_by": "user_a",
            },
        )
        assert reapply_resp.status_code == 201
        assert reapply_resp.json()["data"]["status_code"] == "AGT_STAT_PENDING"

        # 재신청 요청 타입 확인
        request_id_2 = _get_wait_request(client, agent_id)
        reapply_detail = client.get(f"/api/v1/approvals/{request_id_2}").json()["data"]
        assert reapply_detail["req_type_code"] == "REQ_TYP_RECREATE"
        assert reapply_detail["agent_info"]["request_reason"] == "설명 상세 보완하여 재신청"

        # ── Step 4: 관리자 최종 승인 ─────────────────────────────────────────
        approve_resp = client.post(
            f"/api/v1/approvals/{request_id_2}/approve",
            json={"processed_by": "admin_1"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["data"]["req_status_code"] == "REQ_STAT_APPROVED"

        # 최종 에이전트 상태 운영중 확인
        final_agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert final_agent["status_code"] == "AGT_STAT_DEV"

        # 승인 이력 2건 확인 (1차 반려 + 2차 승인)
        all_approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
        assert len(all_approvals) == 2
        statuses = {a["req_status_code"] for a in all_approvals}
        assert "REQ_STAT_REJECTED" in statuses
        assert "REQ_STAT_APPROVED" in statuses


class TestScenario2_ResourceIncrease:
    """
    시나리오 2: 운영 중 자원 증설 신청 및 승인
    흐름: 에이전트 신청 → 승인(운영중) → 자원 증설 신청 → 자원 증설 승인
    """

    def test_full_flow_resource_increase(self, client: TestClient):
        """자원 증설 신청 전체 흐름 테스트"""

        # ── Step 1: 에이전트 신청 및 승인 ──────────────────────────────────────
        create_resp = client.post(
            "/api/v1/agents",
            json={
                "agent_name": "시나리오2 글로벌 번역 봇",
                "description": "다국어 번역 봇",
                "security_pledge": {"is_agreed": True},
                "members": [{"user_id": "user_b", "role_code": "ROLE_OWNER"}],
                "requested_by": "user_b",
            },
        )
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["data"]["agent_id"]

        # 승인
        request_id = _get_wait_request(client, agent_id)
        client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},
        )
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_DEV"

        # ── Step 2: 자원 증설 신청 ───────────────────────────────────────────
        resource_resp = client.post(
            f"/api/v1/agents/{agent_id}/resources",
            json={
                "req_cpu": 4,
                "req_gpu": 1,
                "request_reason": "해외 법인 오픈으로 트래픽 급증하여 GPU 추가 요청합니다.",
                "requested_by": "user_b",
            },
        )
        assert resource_resp.status_code == 201
        resource_approval = resource_resp.json()["data"]
        assert resource_approval["req_category_code"] == "REQ_CAT_RESOURCE"

        # ── Step 3: 자원 증설 승인 ───────────────────────────────────────────
        resource_request_id = _get_wait_request(client, agent_id)
        approve_resp = client.post(
            f"/api/v1/approvals/{resource_request_id}/approve",
            json={
                "processed_by": "admin_1",
                "resource_to_assign": {"cpu": 4, "gpu": 1},
            },
        )
        assert approve_resp.status_code == 200

        # 에이전트 자원 정보 업데이트 확인
        final_agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert final_agent["status_code"] == "AGT_STAT_DEV"  # 상태 유지
        assert final_agent["current_resource"]["gpu"] == 1


class TestScenario3_UserCancel:
    """
    시나리오 3: 사용자의 자의적 신청 취소
    흐름: 에이전트 신청 → 사용자 직접 취소
    """

    def test_full_flow_user_cancel(self, client: TestClient):
        """사용자 신청 취소 전체 흐름 테스트"""

        # ── Step 1: 에이전트 신청 ──────────────────────────────────────────────
        create_resp = client.post(
            "/api/v1/agents",
            json={
                "agent_name": "시나리오3 테스트 봇",
                "description": "잘못 신청함",
                "security_pledge": {"is_agreed": True},
                "members": [{"user_id": "user_c", "role_code": "ROLE_OWNER"}],
                "requested_by": "user_c",
            },
        )
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["data"]["agent_id"]

        # ── Step 2: 사용자 취소 ───────────────────────────────────────────────
        request_id = _get_wait_request(client, agent_id)
        cancel_resp = client.post(
            f"/api/v1/approvals/{request_id}/cancel",
            json={"requested_by": "user_c"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["data"]["req_status_code"] == "REQ_STAT_CANCELLED"

        # 에이전트 상태 사용자취소 확인
        final_agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert final_agent["status_code"] == "AGT_STAT_CANCELLED"

    def test_cancel_by_wrong_user_forbidden(self, client: TestClient):
        """다른 사용자가 취소 시도 시 403 반환 확인"""

        create_resp = client.post(
            "/api/v1/agents",
            json={
                "agent_name": "취소 권한 테스트 봇",
                "description": "취소 권한 검증 테스트용",
                "security_pledge": {"is_agreed": True},
                "members": [{"user_id": "user_c", "role_code": "ROLE_OWNER"}],
                "requested_by": "user_c",
            },
        )
        agent_id = create_resp.json()["data"]["agent_id"]
        request_id = _get_wait_request(client, agent_id)

        # 다른 사용자가 취소 시도
        cancel_resp = client.post(
            f"/api/v1/approvals/{request_id}/cancel",
            json={"requested_by": "user_d"},  # 신청자(user_c)가 아님
        )
        assert cancel_resp.status_code == 403

        # 에이전트 상태 여전히 승인대기
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_PENDING"


class TestScenario4_AgentDelete:
    """
    시나리오 4: 운영 중 에이전트 완전 삭제
    흐름: 에이전트 신청 → 승인(운영중) → 삭제 신청 → 삭제 승인
    """

    def test_full_flow_agent_complete_delete(self, client: TestClient):
        """에이전트 완전 삭제 전체 흐름 테스트"""

        # ── Step 1: 에이전트 신청 ──────────────────────────────────────────────
        create_resp = client.post(
            "/api/v1/agents",
            json={
                "agent_name": "시나리오4 구형 날씨 봇",
                "description": "안 쓰는 봇",
                "security_pledge": {"is_agreed": True},
                "members": [{"user_id": "user_d", "role_code": "ROLE_OWNER"}],
                "requested_by": "user_d",
            },
        )
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["data"]["agent_id"]

        # ── Step 2: 에이전트 운영 승인 ───────────────────────────────────────
        request_id = _get_wait_request(client, agent_id)
        client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},
        )
        agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert agent["status_code"] == "AGT_STAT_DEV"

        # ── Step 3: 삭제 신청 ────────────────────────────────────────────────
        delete_req_resp = client.post(
            f"/api/v1/agents/{agent_id}/delete-request",
            json={
                "request_reason": "V2 버전이 출시되어 기존 봇은 삭제합니다.",
                "requested_by": "user_d",
            },
        )
        assert delete_req_resp.status_code == 201
        assert delete_req_resp.json()["data"]["status_code"] == "AGT_STAT_DEL_PENDING"

        # 삭제 요청 스냅샷 확인
        delete_request_id = _get_wait_request(client, agent_id)
        delete_detail = client.get(f"/api/v1/approvals/{delete_request_id}").json()["data"]
        assert delete_detail["req_type_code"] == "REQ_TYP_DELETE"
        assert delete_detail["agent_info"]["request_reason"] == "V2 버전이 출시되어 기존 봇은 삭제합니다."

        # ── Step 4: 삭제 최종 승인 ───────────────────────────────────────────
        approve_delete_resp = client.post(
            f"/api/v1/approvals/{delete_request_id}/approve",
            json={"processed_by": "admin_2"},
        )
        assert approve_delete_resp.status_code == 200
        assert approve_delete_resp.json()["data"]["req_status_code"] == "REQ_STAT_APPROVED"

        # 에이전트 최종 상태 삭제완료 확인
        final_agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert final_agent["status_code"] == "AGT_STAT_DELETED"

        # 전체 이력 2건 (신청 승인 + 삭제 승인)
        all_approvals = client.get(f"/api/v1/approvals?agent_id={agent_id}").json()["data"]
        assert len(all_approvals) == 2
        approved_count = sum(1 for a in all_approvals if a["req_status_code"] == "REQ_STAT_APPROVED")
        assert approved_count == 2

    def test_delete_request_reject_restores_to_dev(self, client: TestClient):
        """삭제 신청 반려 시 에이전트 운영중 상태로 복원"""

        # 에이전트 생성 및 승인
        create_resp = client.post(
            "/api/v1/agents",
            json={
                "agent_name": "삭제반려 테스트 봇",
                "description": "삭제 반려 후 복원 테스트용",
                "security_pledge": {"is_agreed": True},
                "members": [{"user_id": "user_d", "role_code": "ROLE_OWNER"}],
                "requested_by": "user_d",
            },
        )
        agent_id = create_resp.json()["data"]["agent_id"]

        request_id = _get_wait_request(client, agent_id)
        client.post(
            f"/api/v1/approvals/{request_id}/approve",
            json={"processed_by": "admin_1"},
        )

        # 삭제 신청
        client.post(
            f"/api/v1/agents/{agent_id}/delete-request",
            json={"request_reason": "삭제 신청", "requested_by": "user_d"},
        )
        delete_request_id = _get_wait_request(client, agent_id)

        # 삭제 반려 → 운영중 복원
        reject_resp = client.post(
            f"/api/v1/approvals/{delete_request_id}/reject",
            json={
                "processed_by": "admin_1",
                "reject_reason": "해당 에이전트는 아직 사용 중입니다.",
            },
        )
        assert reject_resp.status_code == 200

        # 운영중 상태 복원 확인
        final_agent = client.get(f"/api/v1/agents/{agent_id}").json()["data"]
        assert final_agent["status_code"] == "AGT_STAT_DEV"
