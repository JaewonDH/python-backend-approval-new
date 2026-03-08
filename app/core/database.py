"""
데이터베이스 세션 관리 모듈
동기(Sync) / 비동기(Async) 세션을 모두 제공한다.
"""

import json
from typing import Any, Generator, AsyncGenerator

from sqlalchemy import create_engine, Text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import settings


# =============================================================================
# Oracle CLOB IS JSON 커스텀 타입 정의
# =============================================================================

class JSONText(TypeDecorator):
    """
    Oracle CLOB IS JSON 컬럼을 Python dict/list로 변환하는 커스텀 타입
    바인딩 시 JSON 직렬화, 읽기 시 JSON 역직렬화 처리
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        """Python 객체 → JSON 문자열 변환"""
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """JSON 문자열 → Python 객체 변환"""
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value


# =============================================================================
# ORM Base 클래스
# =============================================================================

class Base(DeclarativeBase):
    pass


# =============================================================================
# 동기(Sync) 엔진 및 세션
# =============================================================================

sync_engine = create_engine(
    settings.sync_db_url,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 연결 유효성 자동 확인
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


def get_sync_db() -> Generator[Session, None, None]:
    """동기 DB 세션 의존성 (FastAPI Depends 사용)"""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# 비동기(Async) 엔진 및 세션
# =============================================================================

async_engine = create_async_engine(
    settings.async_db_url,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """비동기 DB 세션 의존성 (FastAPI Depends 사용)"""
    async with AsyncSessionLocal() as session:
        yield session
