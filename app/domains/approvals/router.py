"""
승인 요청 라우터
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.core.database import get_sync_db
from app.domains.approvals.schemas import (
    ApprovalRequestDetailResponse,
    ApprovalRequestResponse,
    ApproveRequest,
    CancelRequest,
    RejectRequest,
    ResourceRequestCreate,
)
from app.domains.approvals.service import ApprovalService

router = APIRouter(tags=["승인 요청"])


def get_service(db: Session = Depends(get_sync_db)) -> ApprovalService:
    return ApprovalService(db)


# ─────────────────────────────────────────────────────────────────────────────
# 승인 요청 CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/approvals", response_model=ApiResponse[list[ApprovalRequestDetailResponse]])
def get_approvals(
    req_status_code: str | None = Query(default=None, description="요청 상태 필터"),
    req_category_code: str | None = Query(default=None, description="요청 카테고리 필터"),
    agent_id: str | None = Query(default=None, description="에이전트 ID 필터"),
    service: ApprovalService = Depends(get_service),
):
    """승인 요청 목록 조회"""
    approvals = service.get_all(
        req_status_code=req_status_code,
        req_category_code=req_category_code,
        agent_id=agent_id,
    )
    return ApiResponse.ok(
        data=[ApprovalRequestDetailResponse.model_validate(a) for a in approvals]
    )


@router.get("/approvals/{request_id}", response_model=ApiResponse[ApprovalRequestDetailResponse])
def get_approval(
    request_id: str,
    service: ApprovalService = Depends(get_service),
):
    """승인 요청 단건 상세 조회"""
    approval = service.get_by_id(request_id)
    return ApiResponse.ok(data=ApprovalRequestDetailResponse.model_validate(approval))


# ─────────────────────────────────────────────────────────────────────────────
# 자원 증설 신청 (에이전트 하위 엔드포인트)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/agents/{agent_id}/resources",
    response_model=ApiResponse[ApprovalRequestResponse],
    status_code=201,
)
def create_resource_request(
    agent_id: str,
    body: ResourceRequestCreate,
    service: ApprovalService = Depends(get_service),
):
    """
    자원 증설 신청
    - 운영 중인 에이전트에 대한 CPU/메모리/GPU 증설 요청
    - APPROVAL_REQUESTS (자원 카테고리) + REQ_RESOURCE_INFO 생성
    """
    approval = service.create_resource_request(agent_id, body)
    return ApiResponse.ok(
        data=ApprovalRequestResponse.model_validate(approval),
        message=f"자원 증설 신청이 접수되었습니다. 요청 ID: {approval.request_id}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 승인 / 반려 / 취소 액션
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/approvals/{request_id}/approve",
    response_model=ApiResponse[ApprovalRequestResponse],
)
def approve_request(
    request_id: str,
    body: ApproveRequest,
    service: ApprovalService = Depends(get_service),
):
    """
    승인 처리 (관리자)
    - 에이전트 신청/재신청 → 운영중 전환
    - 에이전트 삭제 신청 → 삭제완료
    - 자원 증설 → 자원 정보 업데이트
    """
    approval = service.approve(request_id, body)
    return ApiResponse.ok(
        data=ApprovalRequestResponse.model_validate(approval),
        message="승인 처리되었습니다.",
    )


@router.post(
    "/approvals/{request_id}/reject",
    response_model=ApiResponse[ApprovalRequestResponse],
)
def reject_request(
    request_id: str,
    body: RejectRequest,
    service: ApprovalService = Depends(get_service),
):
    """
    반려 처리 (관리자)
    - 에이전트 신청/재신청 반려 → 반려됨
    - 에이전트 삭제 반려 → 운영중 복원
    - 자원 증설 반려 → 에이전트 상태 변경 없음
    """
    approval = service.reject(request_id, body)
    return ApiResponse.ok(
        data=ApprovalRequestResponse.model_validate(approval),
        message="반려 처리되었습니다.",
    )


@router.post(
    "/approvals/{request_id}/cancel",
    response_model=ApiResponse[ApprovalRequestResponse],
)
def cancel_request(
    request_id: str,
    body: CancelRequest,
    service: ApprovalService = Depends(get_service),
):
    """
    취소 처리 (사용자 본인)
    - 에이전트 신청 취소 → 사용자취소
    - 자원 증설 취소 → 에이전트 상태 변경 없음
    """
    approval = service.cancel(request_id, body)
    return ApiResponse.ok(
        data=ApprovalRequestResponse.model_validate(approval),
        message="요청이 취소되었습니다.",
    )
