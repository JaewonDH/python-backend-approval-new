"""
사용자 API 테스트
더미 데이터(user_a~d, admin_1~2)를 기반으로 조회 테스트 수행
생성/수정/삭제는 롤백으로 원상 복구
"""

from starlette.testclient import TestClient


class TestUsersRead:
    """사용자 조회 테스트"""

    def test_get_all_users_success(self, client: TestClient):
        """전체 사용자 목록 조회 - 더미 6명 이상 존재"""
        response = client.get("/api/v1/users")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        users = body["data"]
        assert len(users) >= 6  # 더미 데이터: user_a~d, admin_1~2

    def test_get_users_by_role_user(self, client: TestClient):
        """USER 역할 사용자만 조회"""
        response = client.get("/api/v1/users?system_role=USER")
        assert response.status_code == 200
        users = response.json()["data"]
        assert len(users) >= 4  # user_a~d
        for user in users:
            assert user["system_role"] == "USER"

    def test_get_users_by_role_admin(self, client: TestClient):
        """ADMIN 역할 사용자만 조회"""
        response = client.get("/api/v1/users?system_role=ADMIN")
        assert response.status_code == 200
        users = response.json()["data"]
        assert len(users) >= 2  # admin_1~2
        for user in users:
            assert user["system_role"] == "ADMIN"

    def test_get_user_by_id_success(self, client: TestClient):
        """특정 사용자 조회 - 더미 데이터 user_a 사용"""
        response = client.get("/api/v1/users/user_a")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user_id"] == "user_a"
        assert data["user_name"] == "김사원"
        assert data["system_role"] == "USER"

    def test_get_admin_user_by_id(self, client: TestClient):
        """관리자 사용자 조회 - 더미 데이터 admin_1 사용"""
        response = client.get("/api/v1/users/admin_1")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user_id"] == "admin_1"
        assert data["system_role"] == "ADMIN"

    def test_get_user_not_found(self, client: TestClient):
        """존재하지 않는 사용자 조회 - 404 반환"""
        response = client.get("/api/v1/users/NOT_EXIST_USER")
        assert response.status_code == 404


class TestUsersWrite:
    """사용자 생성/수정/삭제 테스트"""

    def test_create_user_success(self, client: TestClient):
        """사용자 생성 성공"""
        payload = {
            "user_id": "test_user_new",
            "user_name": "테스트사원",
            "department": "테스트팀",
            "email": "test@company.com",
            "system_role": "USER",
        }
        response = client.post("/api/v1/users", json=payload)
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["user_id"] == "test_user_new"
        assert data["user_name"] == "테스트사원"
        assert data["email"] == "test@company.com"

    def test_create_admin_user_success(self, client: TestClient):
        """관리자 사용자 생성 성공"""
        payload = {
            "user_id": "test_admin_new",
            "user_name": "테스트관리자",
            "department": "IT팀",
            "email": "testadmin@company.com",
            "system_role": "ADMIN",
        }
        response = client.post("/api/v1/users", json=payload)
        assert response.status_code == 201
        assert response.json()["data"]["system_role"] == "ADMIN"

    def test_create_user_duplicate_id(self, client: TestClient):
        """이미 존재하는 사번으로 생성 시도 - 409 반환"""
        payload = {
            "user_id": "user_a",  # 이미 존재하는 사번
            "user_name": "중복 테스트",
            "system_role": "USER",
        }
        response = client.post("/api/v1/users", json=payload)
        assert response.status_code == 409

    def test_create_user_invalid_role(self, client: TestClient):
        """잘못된 system_role 값으로 생성 시도 - 422 반환"""
        payload = {
            "user_id": "test_invalid_role",
            "user_name": "잘못된역할",
            "system_role": "SUPERADMIN",  # 유효하지 않은 역할
        }
        response = client.post("/api/v1/users", json=payload)
        assert response.status_code == 422

    def test_update_user_success(self, client: TestClient):
        """사용자 정보 수정 성공"""
        # 테스트 사용자 생성
        client.post(
            "/api/v1/users",
            json={
                "user_id": "test_update_user",
                "user_name": "수정전이름",
                "system_role": "USER",
            },
        )
        # 수정 요청
        response = client.put(
            "/api/v1/users/test_update_user",
            json={"user_name": "수정후이름", "department": "신규팀"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user_name"] == "수정후이름"
        assert data["department"] == "신규팀"

    def test_update_user_not_found(self, client: TestClient):
        """존재하지 않는 사용자 수정 시도 - 404 반환"""
        response = client.put(
            "/api/v1/users/NOT_EXIST",
            json={"user_name": "수정시도"},
        )
        assert response.status_code == 404

    def test_delete_user_success(self, client: TestClient):
        """사용자 삭제 성공"""
        # 테스트 사용자 생성
        client.post(
            "/api/v1/users",
            json={
                "user_id": "test_delete_user",
                "user_name": "삭제대상",
                "system_role": "USER",
            },
        )
        # 삭제
        response = client.delete("/api/v1/users/test_delete_user")
        assert response.status_code == 200

        # 삭제 후 조회 시 404 확인
        check = client.get("/api/v1/users/test_delete_user")
        assert check.status_code == 404

    def test_delete_user_not_found(self, client: TestClient):
        """존재하지 않는 사용자 삭제 시도 - 404 반환"""
        response = client.delete("/api/v1/users/NOT_EXIST_USER_DEL")
        assert response.status_code == 404
