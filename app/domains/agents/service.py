"""
에이전트 Service
에이전트 신청, 재신청, 삭제 신청 등 핵심 비즈니스 로직을 처리한다.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestError, NotFoundError
from app.domains.agents.repository import AgentRepository
from app.domains.agents.schemas import (
    AgentCreateRequest,
    AgentDeleteRequest,
    AgentReapplyRequest,
)
from app.models.agent import Agent, AgentMember
from app.models.approval import ApprovalRequest, ReqAgentInfo, ReqMemberInfo

# ── 공통 코드 상수 ─────────────────────────────────────────────────────────────
AGT_STAT_PENDING = "AGT_STAT_PENDING"       # 에이전트 승인대기
AGT_STAT_REJECTED = "AGT_STAT_REJECTED"    # 반려됨
AGT_STAT_DEL_PENDING = "AGT_STAT_DEL_PENDING"  # 삭제심사중

REQ_CAT_AGENT = "REQ_CAT_AGENT"            # 요청 카테고리: 에이전트
REQ_TYP_CREATE = "REQ_TYP_CREATE"          # 요청 유형: 신규
REQ_TYP_RECREATE = "REQ_TYP_RECREATE"      # 요청 유형: 재신청
REQ_TYP_DELETE = "REQ_TYP_DELETE"          # 요청 유형: 삭제
REQ_STAT_WAIT = "REQ_STAT_WAIT"            # 요청 상태: 심사대기


class AgentService:
    """에이전트 서비스 (동기)"""

    def __init__(self, db: Session):
        self.repo = AgentRepository(db)
        self.db = db

    def get_all(self, status_code: str | None = None) -> list[Agent]:
        """에이전트 목록 조회"""
        return self.repo.get_all(status_code=status_code)

    def get_by_id(self, agent_id: str) -> Agent:
        """에이전트 상세 조회 (없으면 404)"""
        agent = self.repo.get_by_id(agent_id)
        if not agent:
            raise NotFoundError(f"에이전트를 찾을 수 없습니다. agent_id={agent_id}")
        return agent

    # ── 에이전트 신청 ─────────────────────────────────────────────────────────

    def create_agent(self, body: AgentCreateRequest) -> tuple[Agent, ApprovalRequest]:
        """
        에이전트 최초 신청 처리
        1) AGENTS 레코드 생성 (상태: 승인대기)
        2) AGENT_MEMBERS 레코드 생성
        3) APPROVAL_REQUESTS 레코드 생성 (신규 타입)
        4) REQ_AGENT_INFO 스냅샷 저장
        5) REQ_MEMBERS_INFO 스냅샷 저장
        """
        agent_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        # 1) 에이전트 생성
        agent = Agent(
            agent_id=agent_id,
            agent_name=body.agent_name,
            description=body.description,
            status_code=AGT_STAT_PENDING,
            security_pledge=body.security_pledge,
            created_by=body.requested_by,
        )
        self.repo.create(agent)

        # 2) 멤버 생성
        for m in body.members:
            member = AgentMember(
                agent_id=agent_id,
                user_id=m.user_id,
                role_code=m.role_code,
            )
            self.repo.add_member(member)

        # 3) 승인 요청 생성
        approval = ApprovalRequest(
            request_id=request_id,
            agent_id=agent_id,
            req_category_code=REQ_CAT_AGENT,
            req_type_code=REQ_TYP_CREATE,
            req_status_code=REQ_STAT_WAIT,
            requested_by=body.requested_by,
        )
        self.db.add(approval)
        self.db.flush()

        # 4) 에이전트 정보 스냅샷
        agent_info = ReqAgentInfo(
            request_id=request_id,
            req_agent_name=body.agent_name,
            req_description=body.description,
            req_security_pledge=body.security_pledge,
        )
        self.db.add(agent_info)

        # 5) 멤버 스냅샷
        for m in body.members:
            member_snapshot = ReqMemberInfo(
                request_id=request_id,
                user_id=m.user_id,
                role_code=m.role_code,
            )
            self.db.add(member_snapshot)

        self.db.commit()
        # commit 후 eager loading 포함하여 재조회 (code_name 반환을 위해)
        agent = self.repo.get_by_id(agent_id)
        return agent, approval

    # ── 에이전트 재신청 ───────────────────────────────────────────────────────

    def reapply_agent(
        self, agent_id: str, body: AgentReapplyRequest
    ) -> tuple[Agent, ApprovalRequest]:
        """
        반려된 에이전트 재신청 처리
        1) 에이전트 정보 및 상태 업데이트 (승인대기로 복귀)
        2) 기존 멤버 삭제 후 재등록
        3) APPROVAL_REQUESTS 레코드 생성 (재신청 타입)
        4) 스냅샷 저장
        """
        agent = self.get_by_id(agent_id)

        # 반려 상태일 때만 재신청 가능
        if agent.status_code != AGT_STAT_REJECTED:
            raise BadRequestError(
                f"반려 상태의 에이전트만 재신청할 수 있습니다. 현재 상태: {agent.status_code}"
            )

        request_id = str(uuid.uuid4())

        # 1) 에이전트 정보 및 상태 업데이트
        self.repo.update(
            agent,
            {
                "agent_name": body.agent_name,
                "description": body.description,
                "security_pledge": body.security_pledge,
                "status_code": AGT_STAT_PENDING,
            },
        )

        # 2) 멤버 갱신
        self.repo.delete_members(agent_id)
        for m in body.members:
            member = AgentMember(
                agent_id=agent_id,
                user_id=m.user_id,
                role_code=m.role_code,
            )
            self.repo.add_member(member)

        # 3) 재신청 승인 요청 생성
        approval = ApprovalRequest(
            request_id=request_id,
            agent_id=agent_id,
            req_category_code=REQ_CAT_AGENT,
            req_type_code=REQ_TYP_RECREATE,
            req_status_code=REQ_STAT_WAIT,
            requested_by=body.requested_by,
        )
        self.db.add(approval)
        self.db.flush()

        # 4) 스냅샷 저장
        agent_info = ReqAgentInfo(
            request_id=request_id,
            req_agent_name=body.agent_name,
            req_description=body.description,
            request_reason=body.request_reason,
            req_security_pledge=body.security_pledge,
        )
        self.db.add(agent_info)

        for m in body.members:
            member_snapshot = ReqMemberInfo(
                request_id=request_id,
                user_id=m.user_id,
                role_code=m.role_code,
            )
            self.db.add(member_snapshot)

        self.db.commit()
        # commit 후 eager loading 포함하여 재조회 (code_name 반환을 위해)
        agent = self.repo.get_by_id(agent_id)
        return agent, approval

    # ── 에이전트 삭제 신청 ────────────────────────────────────────────────────

    def request_delete_agent(
        self, agent_id: str, body: AgentDeleteRequest
    ) -> tuple[Agent, ApprovalRequest]:
        """
        운영 중 에이전트 삭제 신청 처리
        1) 에이전트 상태 → 삭제심사중
        2) APPROVAL_REQUESTS 레코드 생성 (삭제 타입)
        3) REQ_AGENT_INFO 스냅샷 저장
        """
        agent = self.get_by_id(agent_id)

        # 운영중(DEV) 또는 운영 가능 상태 확인
        allowed_statuses = {"AGT_STAT_DEV"}
        if agent.status_code not in allowed_statuses:
            raise BadRequestError(
                f"운영 중인 에이전트만 삭제 신청할 수 있습니다. 현재 상태: {agent.status_code}"
            )

        request_id = str(uuid.uuid4())

        # 1) 에이전트 상태 변경
        self.repo.update(agent, {"status_code": AGT_STAT_DEL_PENDING})

        # 2) 삭제 승인 요청 생성
        approval = ApprovalRequest(
            request_id=request_id,
            agent_id=agent_id,
            req_category_code=REQ_CAT_AGENT,
            req_type_code=REQ_TYP_DELETE,
            req_status_code=REQ_STAT_WAIT,
            requested_by=body.requested_by,
        )
        self.db.add(approval)
        self.db.flush()

        # 3) 에이전트 정보 스냅샷
        agent_info = ReqAgentInfo(
            request_id=request_id,
            req_agent_name=agent.agent_name,
            req_description=agent.description,
            request_reason=body.request_reason,
        )
        self.db.add(agent_info)

        self.db.commit()
        # commit 후 eager loading 포함하여 재조회 (code_name 반환을 위해)
        agent = self.repo.get_by_id(agent_id)
        return agent, approval
