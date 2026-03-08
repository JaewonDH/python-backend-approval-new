"""
승인 요청 도메인 스키마 (Pydantic)
- 응답 스키마에서 code_id는 code_name 값도 함께 반환한다.
- model_validator(mode='before')로 ORM 관계에서 code_name을 추출한다.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# 스냅샷 응답 스키마
# ─────────────────────────────────────────────────────────────────────────────

class ReqAgentInfoResponse(BaseModel):
    """에이전트 신청/삭제 정보 스냅샷 응답"""
    request_id: str
    req_agent_name: str
    req_description: str
    request_reason: str | None = None
    req_security_pledge: Any | None = None

    model_config = {"from_attributes": True}


class ReqMemberInfoResponse(BaseModel):
    """멤버 스냅샷 응답 (role_name 포함)"""
    request_id: str
    user_id: str
    role_code: str
    role_name: str | None = None          # COMMON_CODES.code_name

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def resolve_code_names(cls, obj: Any) -> Any:
        """ORM 객체일 때 role 관계에서 code_name 추출"""
        if isinstance(obj, dict):
            return obj
        return {
            "request_id": obj.request_id,
            "user_id": obj.user_id,
            "role_code": obj.role_code,
            "role_name": obj.role.code_name if (hasattr(obj, "role") and obj.role) else None,
        }


class ReqResourceInfoResponse(BaseModel):
    """자원 정보 스냅샷 응답"""
    request_id: str
    req_cpu: int | None = None
    req_memory: str | None = None
    req_gpu: int | None = None
    request_reason: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# 승인 요청 응답 스키마
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalRequestResponse(BaseModel):
    """
    승인 요청 기본 응답 (req_category_name, req_type_name, req_status_name 포함)
    model_validator가 ORM 관계에서 code_name을 추출하며,
    ApprovalRequestDetailResponse 상속 시 스냅샷 필드도 함께 포함한다.
    """
    request_id: str
    agent_id: str
    req_category_code: str
    req_category_name: str | None = None  # COMMON_CODES.code_name
    req_type_code: str
    req_type_name: str | None = None      # COMMON_CODES.code_name
    req_status_code: str
    req_status_name: str | None = None    # COMMON_CODES.code_name
    requested_by: str
    requested_at: datetime
    processed_by: str | None = None
    processed_at: datetime | None = None
    reject_reason: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def resolve_code_names(cls, obj: Any) -> Any:
        """
        ORM 객체일 때 req_category / req_type / req_status 관계에서 code_name 추출.
        ApprovalRequestDetailResponse 상속 시 스냅샷 필드도 함께 포함
        (Pydantic이 각 스냅샷 스키마로 중첩 검증 수행).
        """
        if isinstance(obj, dict):
            return obj
        data: dict[str, Any] = {
            "request_id": obj.request_id,
            "agent_id": obj.agent_id,
            "req_category_code": obj.req_category_code,
            "req_category_name": (
                obj.req_category.code_name
                if (hasattr(obj, "req_category") and obj.req_category)
                else None
            ),
            "req_type_code": obj.req_type_code,
            "req_type_name": (
                obj.req_type.code_name
                if (hasattr(obj, "req_type") and obj.req_type)
                else None
            ),
            "req_status_code": obj.req_status_code,
            "req_status_name": (
                obj.req_status.code_name
                if (hasattr(obj, "req_status") and obj.req_status)
                else None
            ),
            "requested_by": obj.requested_by,
            "requested_at": obj.requested_at,
            "processed_by": obj.processed_by,
            "processed_at": obj.processed_at,
            "reject_reason": obj.reject_reason,
        }
        # ApprovalRequestDetailResponse 용: 스냅샷 필드 포함
        if hasattr(obj, "agent_info"):
            data["agent_info"] = obj.agent_info
        if hasattr(obj, "member_infos"):
            data["member_infos"] = obj.member_infos
        if hasattr(obj, "resource_info"):
            data["resource_info"] = obj.resource_info
        return data


class ApprovalRequestDetailResponse(ApprovalRequestResponse):
    """승인 요청 상세 응답 (스냅샷 + role_name 포함)"""
    agent_info: ReqAgentInfoResponse | None = None
    member_infos: list[ReqMemberInfoResponse] = []
    resource_info: ReqResourceInfoResponse | None = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# 자원 증설 신청 요청 스키마
# ─────────────────────────────────────────────────────────────────────────────

class ResourceRequestCreate(BaseModel):
    """자원 증설 신청 요청"""
    req_cpu: int | None = Field(default=None, ge=0, description="요청 CPU 코어 수")
    req_memory: str | None = Field(default=None, max_length=20, description="요청 메모리 (예: 16GB)")
    req_gpu: int | None = Field(default=None, ge=0, description="요청 GPU 수")
    request_reason: str = Field(..., description="증설 사유")
    requested_by: str = Field(..., max_length=50, description="신청자 사번")


# ─────────────────────────────────────────────────────────────────────────────
# 승인/반려/취소 액션 요청 스키마
# ─────────────────────────────────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    """승인 요청"""
    processed_by: str = Field(..., max_length=50, description="처리자 사번 (관리자)")
    resource_to_assign: dict[str, Any] | None = Field(
        default=None,
        description="자원 증설 승인 시 할당할 자원 정보 (JSON). 예: {cpu: 4, memory: '16GB', gpu: 1}",
    )


class RejectRequest(BaseModel):
    """반려 요청"""
    processed_by: str = Field(..., max_length=50, description="처리자 사번 (관리자)")
    reject_reason: str = Field(..., description="반려 사유")


class CancelRequest(BaseModel):
    """취소 요청"""
    requested_by: str = Field(..., max_length=50, description="취소 요청자 사번")
