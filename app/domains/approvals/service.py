"""
승인 요청 Service
승인, 반려, 취소, 자원 증설 신청 등 승인 관련 핵심 비즈니스 로직을 처리한다.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.domains.approvals.repository import ApprovalRepository
from app.domains.approvals.schemas import (
    ApproveRequest,
    CancelRequest,
    RejectRequest,
    ResourceRequestCreate,
)
from app.models.agent import Agent
from app.models.approval import ApprovalRequest, ReqResourceInfo

# ── 공통 코드 상수 ─────────────────────────────────────────────────────────────
# 에이전트 상태
AGT_STAT_PENDING = "AGT_STAT_PENDING"
AGT_STAT_DEV = "AGT_STAT_DEV"
AGT_STAT_REJECTED = "AGT_STAT_REJECTED"
AGT_STAT_CANCELLED = "AGT_STAT_CANCELLED"
AGT_STAT_DEL_PENDING = "AGT_STAT_DEL_PENDING"
AGT_STAT_DELETED = "AGT_STAT_DELETED"

# 요청 카테고리
REQ_CAT_AGENT = "REQ_CAT_AGENT"
REQ_CAT_RESOURCE = "REQ_CAT_RESOURCE"

# 요청 유형
REQ_TYP_CREATE = "REQ_TYP_CREATE"
REQ_TYP_RECREATE = "REQ_TYP_RECREATE"
REQ_TYP_DELETE = "REQ_TYP_DELETE"

# 요청 상태
REQ_STAT_WAIT = "REQ_STAT_WAIT"
REQ_STAT_APPROVED = "REQ_STAT_APPROVED"
REQ_STAT_REJECTED = "REQ_STAT_REJECTED"
REQ_STAT_CANCELLED = "REQ_STAT_CANCELLED"


class ApprovalService:
    """승인 요청 서비스 (동기)"""

    def __init__(self, db: Session):
        self.repo = ApprovalRepository(db)
        self.db = db

    def get_all(
        self,
        req_status_code: str | None = None,
        req_category_code: str | None = None,
        agent_id: str | None = None,
    ) -> list[ApprovalRequest]:
        """승인 요청 목록 조회 (필터 지원)"""
        return self.repo.get_all(
            req_status_code=req_status_code,
            req_category_code=req_category_code,
            agent_id=agent_id,
        )

    def get_by_id(self, request_id: str) -> ApprovalRequest:
        """승인 요청 단건 조회 (없으면 404)"""
        req = self.repo.get_by_id(request_id)
        if not req:
            raise NotFoundError(f"승인 요청을 찾을 수 없습니다. request_id={request_id}")
        return req

    # ── 자원 증설 신청 ────────────────────────────────────────────────────────

    def create_resource_request(
        self, agent_id: str, body: ResourceRequestCreate
    ) -> ApprovalRequest:
        """
        자원 증설 신청 처리
        1) 에이전트가 운영 중인지 확인
        2) APPROVAL_REQUESTS 레코드 생성 (자원 카테고리)
        3) REQ_RESOURCE_INFO 스냅샷 저장
        """
        # 에이전트 조회
        agent: Agent | None = self.db.get(Agent, agent_id)
        if not agent:
            raise NotFoundError(f"에이전트를 찾을 수 없습니다. agent_id={agent_id}")
        if agent.status_code != AGT_STAT_DEV:
            raise BadRequestError(
                f"운영 중인 에이전트만 자원 증설을 신청할 수 있습니다. 현재 상태: {agent.status_code}"
            )

        request_id = str(uuid.uuid4())

        # 승인 요청 생성
        approval = ApprovalRequest(
            request_id=request_id,
            agent_id=agent_id,
            req_category_code=REQ_CAT_RESOURCE,
            req_type_code=REQ_TYP_CREATE,
            req_status_code=REQ_STAT_WAIT,
            requested_by=body.requested_by,
        )
        self.db.add(approval)
        self.db.flush()

        # 자원 정보 스냅샷 저장
        resource_info = ReqResourceInfo(
            request_id=request_id,
            req_cpu=body.req_cpu,
            req_memory=body.req_memory,
            req_gpu=body.req_gpu,
            request_reason=body.request_reason,
        )
        self.repo.add_resource_info(resource_info)

        self.db.commit()
        # commit 후 eager loading 포함하여 재조회 (code_name 반환을 위해)
        return self.repo.get_by_id(request_id)

    # ── 승인 처리 ─────────────────────────────────────────────────────────────

    def approve(self, request_id: str, body: ApproveRequest) -> ApprovalRequest:
        """
        승인 처리
        요청 카테고리/유형에 따라 에이전트 상태를 함께 변경한다.
        - 에이전트 신청/재신청 승인 → 에이전트 상태: 운영중
        - 에이전트 삭제 승인 → 에이전트 상태: 삭제완료
        - 자원 증설 승인 → 에이전트 current_resource 업데이트
        """
        req = self.get_by_id(request_id)
        self._assert_wait_status(req)

        now = datetime.now(tz=timezone.utc)

        # 에이전트 상태 변경 처리
        agent: Agent | None = self.db.get(Agent, req.agent_id)
        if agent is None:
            raise NotFoundError(f"에이전트를 찾을 수 없습니다. agent_id={req.agent_id}")

        if req.req_category_code == REQ_CAT_AGENT:
            if req.req_type_code in (REQ_TYP_CREATE, REQ_TYP_RECREATE):
                # 신청/재신청 승인 → 운영중으로 전환
                agent.status_code = AGT_STAT_DEV
            elif req.req_type_code == REQ_TYP_DELETE:
                # 삭제 신청 승인 → 삭제완료
                agent.status_code = AGT_STAT_DELETED

        elif req.req_category_code == REQ_CAT_RESOURCE:
            # 자원 증설 승인 → current_resource 업데이트
            if body.resource_to_assign:
                agent.current_resource = body.resource_to_assign
            else:
                # 신청 스냅샷 정보를 기반으로 자원 할당
                if req.resource_info:
                    resource_data = {}
                    if req.resource_info.req_cpu is not None:
                        resource_data["cpu"] = req.resource_info.req_cpu
                    if req.resource_info.req_memory is not None:
                        resource_data["memory"] = req.resource_info.req_memory
                    if req.resource_info.req_gpu is not None:
                        resource_data["gpu"] = req.resource_info.req_gpu
                    # 기존 자원과 병합
                    existing = agent.current_resource or {}
                    agent.current_resource = {**existing, **resource_data}

        self.db.flush()

        # 승인 요청 상태 업데이트
        self.repo.update(
            req,
            {
                "req_status_code": REQ_STAT_APPROVED,
                "processed_by": body.processed_by,
                "processed_at": now,
            },
        )

        self.db.commit()
        # commit 후 eager loading 포함하여 재조회 (code_name 반환을 위해)
        return self.repo.get_by_id(request_id)

    # ── 반려 처리 ─────────────────────────────────────────────────────────────

    def reject(self, request_id: str, body: RejectRequest) -> ApprovalRequest:
        """
        반려 처리
        요청 카테고리/유형에 따라 에이전트 상태를 롤백한다.
        - 에이전트 신청/재신청 반려 → 에이전트 상태: 반려됨
        - 에이전트 삭제 반려 → 에이전트 상태: 운영중(복원)
        - 자원 증설 반려 → 에이전트 상태 변경 없음
        """
        req = self.get_by_id(request_id)
        self._assert_wait_status(req)

        now = datetime.now(tz=timezone.utc)

        # 에이전트 상태 롤백
        agent: Agent | None = self.db.get(Agent, req.agent_id)
        if agent is None:
            raise NotFoundError(f"에이전트를 찾을 수 없습니다. agent_id={req.agent_id}")

        if req.req_category_code == REQ_CAT_AGENT:
            if req.req_type_code in (REQ_TYP_CREATE, REQ_TYP_RECREATE):
                # 신청/재신청 반려 → 반려 상태
                agent.status_code = AGT_STAT_REJECTED
            elif req.req_type_code == REQ_TYP_DELETE:
                # 삭제 신청 반려 → 운영중으로 복원
                agent.status_code = AGT_STAT_DEV

        # 자원 증설 반려는 에이전트 상태 변경 없음
        self.db.flush()

        # 반려 요청 상태 업데이트
        self.repo.update(
            req,
            {
                "req_status_code": REQ_STAT_REJECTED,
                "processed_by": body.processed_by,
                "processed_at": now,
                "reject_reason": body.reject_reason,
            },
        )

        self.db.commit()
        # commit 후 eager loading 포함하여 재조회 (code_name 반환을 위해)
        return self.repo.get_by_id(request_id)

    # ── 취소 처리 ─────────────────────────────────────────────────────────────

    def cancel(self, request_id: str, body: CancelRequest) -> ApprovalRequest:
        """
        사용자 취소 처리
        - 에이전트 신청 취소 → 에이전트 상태: 사용자취소
        - 자원 증설 취소 → 에이전트 상태 변경 없음
        """
        req = self.get_by_id(request_id)
        self._assert_wait_status(req)

        # 취소 요청자가 신청자와 동일한지 확인
        if req.requested_by != body.requested_by:
            raise ForbiddenError("신청자만 취소할 수 있습니다.")

        now = datetime.now(tz=timezone.utc)

        # 에이전트 상태 변경 (에이전트 카테고리 신청일 경우)
        if req.req_category_code == REQ_CAT_AGENT:
            agent: Agent | None = self.db.get(Agent, req.agent_id)
            if agent:
                agent.status_code = AGT_STAT_CANCELLED
            self.db.flush()

        # 취소 처리
        self.repo.update(
            req,
            {
                "req_status_code": REQ_STAT_CANCELLED,
                "processed_at": now,
            },
        )

        self.db.commit()
        # commit 후 eager loading 포함하여 재조회 (code_name 반환을 위해)
        return self.repo.get_by_id(request_id)

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

    def _assert_wait_status(self, req: ApprovalRequest) -> None:
        """심사대기 상태가 아니면 예외 발생"""
        if req.req_status_code != REQ_STAT_WAIT:
            raise BadRequestError(
                f"심사대기 상태의 요청만 처리할 수 있습니다. 현재 상태: {req.req_status_code}"
            )
