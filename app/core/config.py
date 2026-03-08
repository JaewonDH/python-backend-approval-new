"""
애플리케이션 설정 모듈
환경 변수를 읽어 설정값을 관리한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 데이터베이스 접속 정보
    DB_HOST: str = "localhost"
    DB_PORT: int = 1521
    DB_SERVICE: str = "FREEPDB1"
    DB_USERNAME: str = "myuser"
    DB_PASSWORD: str = "mypassword"

    # 애플리케이션 기본 설정
    APP_NAME: str = "Approval System API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    @property
    def sync_db_url(self) -> str:
        """동기 DB 접속 URL"""
        return (
            f"oracle+oracledb://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/?service_name={self.DB_SERVICE}"
        )

    @property
    def async_db_url(self) -> str:
        """비동기 DB 접속 URL"""
        return (
            f"oracle+oracledb_async://{self.DB_USERNAME}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/?service_name={self.DB_SERVICE}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# 싱글턴 설정 인스턴스
settings = Settings()
