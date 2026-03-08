"""
에이전트 도메인 스키마 (Pydantic)
- 응답 스키마에서 code_id는 code_name 값도 함께 반환한다.
- model_validator(mode='before')로 ORM 관계(status, role)에서 code_name을 추출한다.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# 에이전트 멤버 스키마
# ─────────────────────────────────────────────────────────────────────────────

class AgentMemberRequest(BaseModel):
    """에이전트 멤버 요청 항목"""
    user_id: str = Field(..., max_length=50, description="사번")
    role_code: str = Field(..., max_length=50, description="역할 코드 (ROLE_OWNER / ROLE_MEMBER)")


class AgentMemberResponse(BaseModel):
    """에이전트 멤버 응답 (role_name 포함)"""
    agent_id: str
    user_id: str
    role_code: str
    role_name: str | None = None          # COMMON_CODES.code_name
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def resolve_code_names(cls, obj: Any) -> Any:
        """ORM 객체일 때 role 관계에서 code_name 추출"""
        if isinstance(obj, dict):
            return obj
        return {
            "agent_id": obj.agent_id,
            "user_id": obj.user_id,
            "role_code": obj.role_code,
            "role_name": obj.role.code_name if (hasattr(obj, "role") and obj.role) else None,
            "created_at": obj.created_at,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 에이전트 신청 스키마
# ─────────────────────────────────────────────────────────────────────────────

class AgentCreateRequest(BaseModel):
    """에이전트 신청 요청 (최초 신청)"""
    agent_name: str = Field(..., max_length=100, description="에이전트명")
    description: str = Field(..., description="에이전트 설명")
    security_pledge: dict[str, Any] = Field(..., description="보안 서약 (JSON)")
    members: list[AgentMemberRequest] = Field(
        default=[], description="참여 멤버 목록 (대표자 포함)"
    )
    requested_by: str = Field(..., max_length=50, description="신청자 사번")


class AgentReapplyRequest(BaseModel):
    """에이전트 재신청 요청 (반려 후 재신청)"""
    agent_name: str = Field(..., max_length=100, description="에이전트명")
    description: str = Field(..., description="수정된 에이전트 설명")
    security_pledge: dict[str, Any] = Field(..., description="보안 서약 (JSON)")
    members: list[AgentMemberRequest] = Field(default=[], description="참여 멤버 목록")
    request_reason: str = Field(..., description="재신청 사유 (보완 내용)")
    requested_by: str = Field(..., max_length=50, description="신청자 사번")


class AgentDeleteRequest(BaseModel):
    """에이전트 삭제 신청 요청"""
    request_reason: str = Field(..., description="삭제 사유")
    requested_by: str = Field(..., max_length=50, description="신청자 사번")


# ─────────────────────────────────────────────────────────────────────────────
# 에이전트 응답 스키마
# ─────────────────────────────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    """
    에이전트 기본 응답 (status_name 포함)
    model_validator가 ORM 관계(status)에서 code_name을 추출하며,
    AgentDetailResponse 상속 시 members 필드도 함께 포함한다.
    """
    agent_id: str
    agent_name: str
    description: str
    status_code: str
    status_name: str | None = None        # COMMON_CODES.code_name
    current_resource: Any | None = None
    security_pledge: Any | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def resolve_code_names(cls, obj: Any) -> Any:
        """
        ORM 객체일 때 status 관계에서 code_name 추출.
        AgentDetailResponse 상속 시 members도 함께 포함 (Pydantic이 중첩 검증 수행).
        """
        if isinstance(obj, dict):
            return obj
        data: dict[str, Any] = {
            "agent_id": obj.agent_id,
            "agent_name": obj.agent_name,
            "description": obj.description,
            "status_code": obj.status_code,
            "status_name": obj.status.code_name if (hasattr(obj, "status") and obj.status) else None,
            "current_resource": obj.current_resource,
            "security_pledge": obj.security_pledge,
            "created_by": obj.created_by,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
        }
        # AgentDetailResponse 용: members가 있으면 포함 (Pydantic이 AgentMemberResponse로 변환)
        if hasattr(obj, "members"):
            data["members"] = obj.members
        return data


class AgentDetailResponse(AgentResponse):
    """에이전트 상세 응답 (멤버 + role_name 포함)"""
    members: list[AgentMemberResponse] = []

    model_config = {"from_attributes": True}
