"""
사용자(임직원) ORM 모델
"""

from datetime import datetime

from sqlalchemy import String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """사용자(임직원 및 관리자) 마스터 테이블 (USERS)"""

    __tablename__ = "USERS"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="사번 (PK)")
    user_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="이름")
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="소속 부서")
    email: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="이메일")
    system_role: Mapped[str] = mapped_column(
        String(20),
        default="USER",
        comment="시스템 권한 (USER/ADMIN)",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        comment="생성일시",
    )
