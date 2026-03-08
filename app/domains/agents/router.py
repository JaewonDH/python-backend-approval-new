"""
에이전트 라우터
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.core.database import get_sync_db
from app.domains.agents.schemas import (
    AgentCreateRequest,
    AgentDeleteRequest,
    AgentDetailResponse,
    AgentMemberResponse,
    AgentReapplyRequest,
    AgentResponse,
)
from app.domains.agents.service import AgentService
from app.domains.approvals.schemas import ApprovalRequestResponse

router = APIRouter(prefix="/agents", tags=["에이전트"])


def get_service(db: Session = Depends(get_sync_db)) -> AgentService:
    return AgentService(db)


@router.get("", response_model=ApiResponse[list[AgentResponse]])
def get_agents(
    status_code: str | None = Query(default=None, description="상태 코드 필터"),
    service: AgentService = Depends(get_service),
):
    """에이전트 목록 조회"""
    agents = service.get_all(status_code=status_code)
    return ApiResponse.ok(data=[AgentResponse.model_validate(a) for a in agents])


@router.get("/{agent_id}", response_model=ApiResponse[AgentDetailResponse])
def get_agent(
    agent_id: str,
    service: AgentService = Depends(get_service),
):
    """에이전트 상세 조회 (멤버 포함)"""
    agent = service.get_by_id(agent_id)
    return ApiResponse.ok(data=AgentDetailResponse.model_validate(agent))


@router.post("", response_model=ApiResponse[AgentDetailResponse], status_code=201)
def create_agent(
    body: AgentCreateRequest,
    service: AgentService = Depends(get_service),
):
    """
    에이전트 신청 (최초)
    - AGENTS 생성, AGENT_MEMBERS 생성
    - APPROVAL_REQUESTS (신규) + REQ_AGENT_INFO + REQ_MEMBERS_INFO 생성
    """
    agent, approval = service.create_agent(body)
    return ApiResponse.ok(
        data=AgentDetailResponse.model_validate(agent),
        message=f"에이전트 신청이 접수되었습니다. 요청 ID: {approval.request_id}",
    )


@router.post("/{agent_id}/reapply", response_model=ApiResponse[AgentDetailResponse], status_code=201)
def reapply_agent(
    agent_id: str,
    body: AgentReapplyRequest,
    service: AgentService = Depends(get_service),
):
    """
    에이전트 재신청 (반려 후)
    - 에이전트 정보 및 멤버 갱신
    - APPROVAL_REQUESTS (재신청) + 스냅샷 생성
    """
    agent, approval = service.reapply_agent(agent_id, body)
    return ApiResponse.ok(
        data=AgentDetailResponse.model_validate(agent),
        message=f"에이전트 재신청이 접수되었습니다. 요청 ID: {approval.request_id}",
    )


@router.post("/{agent_id}/delete-request", response_model=ApiResponse[AgentResponse], status_code=201)
def request_delete_agent(
    agent_id: str,
    body: AgentDeleteRequest,
    service: AgentService = Depends(get_service),
):
    """
    에이전트 삭제 신청
    - 에이전트 상태 → 삭제심사중
    - APPROVAL_REQUESTS (삭제) + REQ_AGENT_INFO 생성
    """
    agent, approval = service.request_delete_agent(agent_id, body)
    return ApiResponse.ok(
        data=AgentResponse.model_validate(agent),
        message=f"에이전트 삭제 신청이 접수되었습니다. 요청 ID: {approval.request_id}",
    )
