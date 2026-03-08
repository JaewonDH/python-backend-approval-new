"""
헬스 체크 및 루트 엔드포인트 테스트
"""

from starlette.testclient import TestClient


class TestHealthCheck:
    """서버 상태 확인 테스트"""

    def test_root(self, client: TestClient):
        """루트 엔드포인트 응답 확인"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_health(self, client: TestClient):
        """헬스 체크 엔드포인트 응답 확인"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "정상" in data["message"]
