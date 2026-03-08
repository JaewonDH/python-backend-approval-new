"""
승인 요청 Repository
동기/비동기 DB 접근 로직을 담당한다.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.models.approval import ApprovalRequest, ReqMemberInfo, ReqResourceInfo


class ApprovalRepository:
    """승인 요청 Repository (동기)"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(
        self,
        req_status_code: str | None = None,
        req_category_code: str | None = None,
        agent_id: str | None = None,
    ) -> list[ApprovalRequest]:
        """승인 요청 목록 조회 (코드명, 스냅샷 포함 eager loading)"""
        stmt = select(ApprovalRequest).options(
            selectinload(ApprovalRequest.req_category),                          # req_category_name 용
            selectinload(ApprovalRequest.req_type),                              # req_type_name 용
            selectinload(ApprovalRequest.req_status),                            # req_status_name 용
            selectinload(ApprovalRequest.agent_info),
            selectinload(ApprovalRequest.member_infos).selectinload(ReqMemberInfo.role),  # role_name 용
            selectinload(ApprovalRequest.resource_info),
        )
        if req_status_code:
            stmt = stmt.where(ApprovalRequest.req_status_code == req_status_code)
        if req_category_code:
            stmt = stmt.where(ApprovalRequest.req_category_code == req_category_code)
        if agent_id:
            stmt = stmt.where(ApprovalRequest.agent_id == agent_id)
        stmt = stmt.order_by(ApprovalRequest.requested_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, request_id: str) -> ApprovalRequest | None:
        """요청 ID로 단건 조회 (코드명, 스냅샷 포함 eager loading)"""
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.request_id == request_id)
            .options(
                selectinload(ApprovalRequest.req_category),
                selectinload(ApprovalRequest.req_type),
                selectinload(ApprovalRequest.req_status),
                selectinload(ApprovalRequest.agent_info),
                selectinload(ApprovalRequest.member_infos).selectinload(ReqMemberInfo.role),
                selectinload(ApprovalRequest.resource_info),
            )
        )
        return self.db.scalars(stmt).first()

    def update(self, request: ApprovalRequest, data: dict) -> ApprovalRequest:
        """승인 요청 필드 업데이트"""
        for key, value in data.items():
            setattr(request, key, value)
        self.db.flush()
        return request

    def add_resource_info(self, resource_info: ReqResourceInfo) -> ReqResourceInfo:
        """자원 정보 스냅샷 추가"""
        self.db.add(resource_info)
        self.db.flush()
        return resource_info


class AsyncApprovalRepository:
    """승인 요청 Repository (비동기)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        req_status_code: str | None = None,
        req_category_code: str | None = None,
        agent_id: str | None = None,
    ) -> list[ApprovalRequest]:
        """승인 요청 목록 조회 (코드명, 스냅샷 포함 eager loading)"""
        stmt = select(ApprovalRequest).options(
            selectinload(ApprovalRequest.req_category),
            selectinload(ApprovalRequest.req_type),
            selectinload(ApprovalRequest.req_status),
            selectinload(ApprovalRequest.agent_info),
            selectinload(ApprovalRequest.member_infos).selectinload(ReqMemberInfo.role),
            selectinload(ApprovalRequest.resource_info),
        )
        if req_status_code:
            stmt = stmt.where(ApprovalRequest.req_status_code == req_status_code)
        if req_category_code:
            stmt = stmt.where(ApprovalRequest.req_category_code == req_category_code)
        if agent_id:
            stmt = stmt.where(ApprovalRequest.agent_id == agent_id)
        stmt = stmt.order_by(ApprovalRequest.requested_at.desc())
        result = await self.db.scalars(stmt)
        return list(result.all())

    async def get_by_id(self, request_id: str) -> ApprovalRequest | None:
        """요청 ID로 단건 조회 (코드명, 스냅샷 포함 eager loading)"""
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.request_id == request_id)
            .options(
                selectinload(ApprovalRequest.req_category),
                selectinload(ApprovalRequest.req_type),
                selectinload(ApprovalRequest.req_status),
                selectinload(ApprovalRequest.agent_info),
                selectinload(ApprovalRequest.member_infos).selectinload(ReqMemberInfo.role),
                selectinload(ApprovalRequest.resource_info),
            )
        )
        result = await self.db.scalars(stmt)
        return result.first()
