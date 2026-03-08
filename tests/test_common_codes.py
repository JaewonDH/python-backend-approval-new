"""
공통 코드 API 테스트
기존 더미 데이터를 기반으로 조회 테스트 수행,
생성/수정/삭제는 테스트 후 롤백으로 원상 복구
"""

import pytest
from starlette.testclient import TestClient


class TestCommonCodesRead:
    """공통 코드 조회 테스트"""

    def test_get_all_codes_success(self, client: TestClient):
        """전체 공통 코드 목록 조회 - 더미 데이터가 존재해야 함"""
        response = client.get("/api/v1/common-codes")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert len(body["data"]) > 0

    def test_get_all_codes_active_filter(self, client: TestClient):
        """활성 코드만 필터링하여 조회"""
        response = client.get("/api/v1/common-codes?is_active=Y")
        assert response.status_code == 200
        codes = response.json()["data"]
        # 모든 결과가 is_active=Y 인지 확인
        for code in codes:
            assert code["is_active"] == "Y"

    def test_get_codes_by_group_agt_stat(self, client: TestClient):
        """에이전트 상태 그룹 코드 조회"""
        response = client.get("/api/v1/common-codes/groups/AGT_STAT")
        assert response.status_code == 200
        codes = response.json()["data"]
        assert len(codes) > 0
        # 모든 코드가 AGT_STAT 그룹인지 확인
        for code in codes:
            assert code["group_code"] == "AGT_STAT"

    def test_get_codes_by_group_role(self, client: TestClient):
        """역할 그룹 코드 조회 (ROLE_OWNER, ROLE_MEMBER 포함)"""
        response = client.get("/api/v1/common-codes/groups/ROLE")
        assert response.status_code == 200
        codes = response.json()["data"]
        code_ids = [c["code_id"] for c in codes]
        assert "ROLE_OWNER" in code_ids
        assert "ROLE_MEMBER" in code_ids

    def test_get_codes_by_group_empty(self, client: TestClient):
        """존재하지 않는 그룹 조회 - 빈 목록 반환"""
        response = client.get("/api/v1/common-codes/groups/NOT_EXIST_GROUP")
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_get_code_by_id_success(self, client: TestClient):
        """특정 공통 코드 단건 조회"""
        response = client.get("/api/v1/common-codes/AGT_STAT_DEV")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["code_id"] == "AGT_STAT_DEV"
        assert data["group_code"] == "AGT_STAT"
        assert data["code_name"] == "운영중"

    def test_get_code_by_id_not_found(self, client: TestClient):
        """존재하지 않는 코드 조회 - 404 반환"""
        response = client.get("/api/v1/common-codes/NOT_EXIST_CODE")
        assert response.status_code == 404


class TestCommonCodesWrite:
    """공통 코드 생성/수정/삭제 테스트"""

    def test_create_code_success(self, client: TestClient):
        """공통 코드 생성 성공"""
        payload = {
            "code_id": "TEST_CODE_NEW",
            "group_code": "TEST_GROUP",
            "code_name": "테스트 코드명",
            "sort_order": 1,
            "is_active": "Y",
            "description": "테스트 코드 설명",
        }
        response = client.post("/api/v1/common-codes", json=payload)
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["code_id"] == "TEST_CODE_NEW"
        assert data["code_name"] == "테스트 코드명"
        assert data["group_code"] == "TEST_GROUP"

    def test_create_code_duplicate_id(self, client: TestClient):
        """이미 존재하는 코드 ID로 생성 시도 - 409 반환"""
        payload = {
            "code_id": "AGT_STAT_DEV",  # 이미 존재하는 코드
            "group_code": "TEST",
            "code_name": "중복 테스트",
        }
        response = client.post("/api/v1/common-codes", json=payload)
        assert response.status_code == 409

    def test_create_code_missing_required_field(self, client: TestClient):
        """필수 필드 누락 시 422 반환"""
        payload = {
            "code_id": "TEST_MISSING",
            # code_name 누락
            "group_code": "TEST",
        }
        response = client.post("/api/v1/common-codes", json=payload)
        assert response.status_code == 422

    def test_update_code_success(self, client: TestClient):
        """공통 코드 수정 성공"""
        # 테스트 코드 생성
        client.post(
            "/api/v1/common-codes",
            json={
                "code_id": "TEST_UPDATE",
                "group_code": "TEST",
                "code_name": "수정 전",
            },
        )
        # 수정 요청
        response = client.put(
            "/api/v1/common-codes/TEST_UPDATE",
            json={"code_name": "수정 후", "description": "수정 완료"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["code_name"] == "수정 후"
        assert data["description"] == "수정 완료"

    def test_update_code_not_found(self, client: TestClient):
        """존재하지 않는 코드 수정 시도 - 404 반환"""
        response = client.put(
            "/api/v1/common-codes/NOT_EXIST",
            json={"code_name": "수정 시도"},
        )
        assert response.status_code == 404

    def test_delete_code_success(self, client: TestClient):
        """공통 코드 삭제 성공"""
        # 테스트 코드 생성
        client.post(
            "/api/v1/common-codes",
            json={
                "code_id": "TEST_DELETE",
                "group_code": "TEST",
                "code_name": "삭제 테스트",
            },
        )
        # 삭제
        response = client.delete("/api/v1/common-codes/TEST_DELETE")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # 삭제 후 조회 시 404 확인
        check = client.get("/api/v1/common-codes/TEST_DELETE")
        assert check.status_code == 404

    def test_delete_code_not_found(self, client: TestClient):
        """존재하지 않는 코드 삭제 시도 - 404 반환"""
        response = client.delete("/api/v1/common-codes/NOT_EXIST_DEL")
        assert response.status_code == 404
