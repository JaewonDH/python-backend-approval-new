"""
에이전트 및 에이전트 멤버 ORM 모델
"""

from datetime import datetime
from typing import Any

from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, JSONText


class Agent(Base):
    """에이전트 마스터 테이블 (AGENTS)"""

    __tablename__ = "AGENTS"

    agent_id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="에이전트 ID (UUID)")
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="에이전트명")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="설명")
    status_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("COMMON_CODES.code_id"),
        nullable=False,
        comment="에이전트 상태 코드",
    )
    current_resource: Mapped[Any | None] = mapped_column(
        JSONText, nullable=True, comment="현재 할당 자원 (JSON)"
    )
    security_pledge: Mapped[Any | None] = mapped_column(
        JSONText, nullable=True, comment="보안 서약 (JSON)"
    )
    created_by: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("USERS.user_id"),
        nullable=False,
        comment="신청자 사번",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        comment="생성일시",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        comment="수정일시 (트리거 자동 갱신)",
    )

    # ── 관계 매핑 ──────────────────────────────────────────────────────────
    status: Mapped["CommonCode"] = relationship(  # type: ignore[name-defined]
        "CommonCode", foreign_keys=[status_code]
    )
    creator: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[created_by]
    )
    # members: Mapped[list["AgentMember"]] = relationship(
    #     "AgentMember", back_populates="agent", cascade="all, delete-orphan"
    # )
    members: Mapped[list["AgentMember"]] = relationship(
        "AgentMember", cascade="all, delete-orphan"
    )
    # approval_requests: Mapped[list["ApprovalRequest"]] = relationship(  # type: ignore[name-defined]
    #     "ApprovalRequest", back_populates="agent"
    # )


class AgentMember(Base):
    """에이전트 참여 멤버 테이블 (AGENT_MEMBERS)"""

    __tablename__ = "AGENT_MEMBERS"

    agent_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("AGENTS.agent_id", ondelete="CASCADE"),
        primary_key=True,
        comment="에이전트 ID",
    )
    user_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("USERS.user_id"),
        primary_key=True,
        comment="사번",
    )
    role_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("COMMON_CODES.code_id"),
        nullable=False,
        comment="역할 코드",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        comment="생성일시",
    )

    # ── 관계 매핑 ──────────────────────────────────────────────────────────
    # agent: Mapped["Agent"] = relationship("Agent", back_populates="members")
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
    role: Mapped["CommonCode"] = relationship(  # type: ignore[name-defined]
        "CommonCode", foreign_keys=[role_code]
    )
