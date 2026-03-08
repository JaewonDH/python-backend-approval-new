"""
공통 코드 라우터
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.core.database import get_sync_db
from app.domains.common_codes.schemas import (
    CommonCodeCreate,
    CommonCodeResponse,
    CommonCodeUpdate,
)
from app.domains.common_codes.service import CommonCodeService

router = APIRouter(prefix="/common-codes", tags=["공통 코드"])


def get_service(db: Session = Depends(get_sync_db)) -> CommonCodeService:
    return CommonCodeService(db)


@router.get("", response_model=ApiResponse[list[CommonCodeResponse]])
def get_all_codes(
    is_active: str | None = Query(default=None, description="활성 여부 필터 (Y/N)"),
    service: CommonCodeService = Depends(get_service),
):
    """전체 공통 코드 목록 조회"""
    codes = service.get_all(is_active=is_active)
    return ApiResponse.ok(data=[CommonCodeResponse.model_validate(c) for c in codes])


@router.get("/groups/{group_code}", response_model=ApiResponse[list[CommonCodeResponse]])
def get_codes_by_group(
    group_code: str,
    service: CommonCodeService = Depends(get_service),
):
    """그룹별 공통 코드 조회"""
    codes = service.get_by_group(group_code=group_code)
    return ApiResponse.ok(data=[CommonCodeResponse.model_validate(c) for c in codes])


@router.get("/{code_id}", response_model=ApiResponse[CommonCodeResponse])
def get_code(
    code_id: str,
    service: CommonCodeService = Depends(get_service),
):
    """공통 코드 단건 조회"""
    code = service.get_by_id(code_id)
    return ApiResponse.ok(data=CommonCodeResponse.model_validate(code))


@router.post("", response_model=ApiResponse[CommonCodeResponse], status_code=201)
def create_code(
    body: CommonCodeCreate,
    service: CommonCodeService = Depends(get_service),
):
    """공통 코드 생성"""
    code = service.create(body)
    return ApiResponse.ok(data=CommonCodeResponse.model_validate(code), message="공통 코드가 생성되었습니다.")


@router.put("/{code_id}", response_model=ApiResponse[CommonCodeResponse])
def update_code(
    code_id: str,
    body: CommonCodeUpdate,
    service: CommonCodeService = Depends(get_service),
):
    """공통 코드 수정"""
    code = service.update(code_id, body)
    return ApiResponse.ok(data=CommonCodeResponse.model_validate(code), message="공통 코드가 수정되었습니다.")


@router.delete("/{code_id}", response_model=ApiResponse[None])
def delete_code(
    code_id: str,
    service: CommonCodeService = Depends(get_service),
):
    """공통 코드 삭제"""
    service.delete(code_id)
    return ApiResponse.ok(message="공통 코드가 삭제되었습니다.")
