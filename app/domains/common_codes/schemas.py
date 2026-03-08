"""
공통 코드 도메인 스키마 (Pydantic)
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CommonCodeBase(BaseModel):
    group_code: str = Field(..., max_length=50, description="그룹 코드")
    code_name: str = Field(..., max_length=100, description="코드명")
    sort_order: int = Field(default=0, description="정렬 순서")
    is_active: str = Field(default="Y", pattern="^[YN]$", description="활성 여부 (Y/N)")
    description: str | None = Field(default=None, max_length=255, description="설명")


class CommonCodeCreate(CommonCodeBase):
    """공통 코드 생성 요청"""
    code_id: str = Field(..., max_length=50, description="코드 ID")


class CommonCodeUpdate(BaseModel):
    """공통 코드 수정 요청"""
    code_name: str | None = Field(default=None, max_length=100)
    sort_order: int | None = None
    is_active: str | None = Field(default=None, pattern="^[YN]$")
    description: str | None = Field(default=None, max_length=255)


class CommonCodeResponse(CommonCodeBase):
    """공통 코드 응답"""
    code_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
