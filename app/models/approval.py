"""
승인 요청 및 스냅샷 ORM 모델
- APPROVAL_REQUESTS  : 통합 승인 요청 헤더
- REQ_AGENT_INFO     : 에이전트 신청/삭제 스냅샷
- REQ_MEMBERS_INFO   : 멤버 스냅샷
- REQ_RESOURCE_INFO  : 자원 증설 스냅샷
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, String, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, JSONText


class ApprovalRequest(Base):
    """통합 승인 요청 이력 테이블 (APPROVAL_REQUESTS)"""

    __tablename__ = "APPROVAL_REQUESTS"

    request_id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="요청 ID (UUID)")
    agent_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("AGENTS.agent_id", ondelete="CASCADE"),
        nullable=False,
        comment="에이전트 ID",
    )
    req_category_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("COMMON_CODES.code_id"),
        nullable=False,
        comment="요청 카테고리 (REQ_CAT_AGENT / REQ_CAT_RESOURCE)",
    )
    req_type_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("COMMON_CODES.code_id"),
        nullable=False,
        comment="요청 유형 (CREATE / RECREATE / DELETE)",
    )
    req_status_code: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("COMMON_CODES.code_id"),
        nullable=False,
        comment="요청 상태 (WAIT / APPROVED / REJECTED / CANCELLED)",
    )
    requested_by: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("USERS.user_id"),
        nullable=False,
        comment="신청자 사번",
    )
    requested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        comment="신청일시",
    )
    processed_by: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("USERS.user_id"),
        nullable=True,
        comment="처리자 사번",
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP, nullable=True, comment="처리일시"
    )
    reject_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="반려 사유"
    )

    # ── 관계 매핑 ──────────────────────────────────────────────────────────
    agent: Mapped["Agent"] = relationship(  # type: ignore[name-defined]
        "Agent", back_populates="approval_requests"
    )
    req_category: Mapped["CommonCode"] = relationship(  # type: ignore[name-defined]
        "CommonCode", foreign_keys=[req_category_code]
    )
    req_type: Mapped["CommonCode"] = relationship(  # type: ignore[name-defined]
        "CommonCode", foreign_keys=[req_type_code]
    )
    req_status: Mapped["CommonCode"] = relationship(  # type: ignore[name-defined]
        "CommonCode", foreign_keys=[req_status_code]
    )
    requester: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[requested_by]
    )
    processor: Mapped["User | None"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[processed_by]
    )
    # 스냅샷 관계 (1:1)
    agent_info: Mapped["ReqAgentInfo | None"] = relationship(
        "ReqAgentInfo", back_populates="request", uselist=False
    )
    member_infos: Mapped[list["ReqMemberInfo"]] = relationship(
        "ReqMemberInfo", back_populates="request"
    )
    resource_info: Mapped["ReqResourceInfo | None"] = relationship(
        "ReqResourceInfo", back_populates="request", uselist=False
    )


class ReqAgentInfo(Base):
    """에이전트 신청/삭제 정보 스냅샷 (REQ_AGENT_INFO)"""

    __tablename__ = "REQ_AGENT_INFO"

    request_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("APPROVAL_REQUESTS.request_id", ondelete="CASCADE"),
        primary_key=True,
        comment="요청 ID",
    )
    req_agent_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="신청 에이전트명")
    req_description: Mapped[str] = mapped_column(Text, nullable=False, comment="신청 설명")
    request_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="신청 사유")
    req_security_pledge: Mapped[Any | None] = mapped_column(
        JSONText, nullable=True, comment="보안 서약 스냅샷 (JSON)"
    )

    # ── 관계 매핑 ──────────────────────────────────────────────────────────
    request: Mapped["ApprovalRequest"] = relationship(
        "ApprovalRequest", back_populates="agent_info"
    )


class ReqMemberInfo(Base):
    """멤버 스냅샷 테이블 (REQ_MEMBERS_INFO)"""

    __tablename__ = "REQ_MEMBERS_INFO"

    request_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("APPROVAL_REQUESTS.request_id", ondelete="CASCADE"),
        primary_key=True,
        comment="요청 ID",
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

    # ── 관계 매핑 ──────────────────────────────────────────────────────────
    request: Mapped["ApprovalRequest"] = relationship(
        "ApprovalRequest", back_populates="member_infos"
    )
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
    role: Mapped["CommonCode"] = relationship("CommonCode")  # type: ignore[name-defined]


class ReqResourceInfo(Base):
    """자원 정보 스냅샷 테이블 (REQ_RESOURCE_INFO)"""

    __tablename__ = "REQ_RESOURCE_INFO"

    request_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("APPROVAL_REQUESTS.request_id", ondelete="CASCADE"),
        primary_key=True,
        comment="요청 ID",
    )
    req_cpu: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="요청 CPU 코어 수")
    req_memory: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="요청 메모리")
    req_gpu: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="요청 GPU 수")
    request_reason: Mapped[str] = mapped_column(Text, nullable=False, comment="요청 사유")

    # ── 관계 매핑 ──────────────────────────────────────────────────────────
    request: Mapped["ApprovalRequest"] = relationship(
        "ApprovalRequest", back_populates="resource_info"
    )
