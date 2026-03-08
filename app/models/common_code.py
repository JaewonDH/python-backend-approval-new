"""
공통 코드 ORM 모델
"""

from datetime import datetime

from sqlalchemy import String, Integer, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CommonCode(Base):
    """공통 코드 테이블 (COMMON_CODES)"""

    __tablename__ = "COMMON_CODES"

    code_id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="코드 ID")
    group_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="그룹 코드")
    code_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="코드명")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="정렬 순서")
    is_active: Mapped[str] = mapped_column(String(1), default="Y", comment="활성 여부 (Y/N)")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="설명")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        comment="생성일시",
    )
