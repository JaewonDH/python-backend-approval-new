"""
에이전트 Repository
동기/비동기 DB 접근 로직을 담당한다.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from app.models.agent import Agent, AgentMember


class AgentRepository:
    """에이전트 Repository (동기)"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, status_code: str | None = None) -> list[Agent]:
        """에이전트 목록 조회 (상태 코드명, 멤버 역할 코드명 포함 eager loading)"""
        stmt = select(Agent).options(
            selectinload(Agent.status),                              # status_name 용
            selectinload(Agent.members).selectinload(AgentMember.role),  # role_name 용
        )
        if status_code:
            stmt = stmt.where(Agent.status_code == status_code)
        stmt = stmt.order_by(Agent.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, agent_id: str) -> Agent | None:
        """에이전트 ID로 단건 조회 (상태 코드명, 멤버 역할 코드명 포함 eager loading)"""
        stmt = (
            select(Agent)
            .where(Agent.agent_id == agent_id)
            .options(
                selectinload(Agent.status),
                selectinload(Agent.members).selectinload(AgentMember.role),
            )
        )
        return self.db.scalars(stmt).first()

    def create(self, agent: Agent) -> Agent:
        """에이전트 생성"""
        self.db.add(agent)
        self.db.flush()
        return agent

    def update(self, agent: Agent, data: dict) -> Agent:
        """에이전트 필드 업데이트"""
        for key, value in data.items():
            setattr(agent, key, value)
        self.db.flush()
        return agent

    def add_member(self, member: AgentMember) -> AgentMember:
        """에이전트 멤버 추가"""
        self.db.add(member)
        self.db.flush()
        return member

    def get_member(self, agent_id: str, user_id: str) -> AgentMember | None:
        """에이전트 멤버 단건 조회"""
        return self.db.get(AgentMember, (agent_id, user_id))

    def delete_members(self, agent_id: str) -> None:
        """에이전트의 모든 멤버 삭제 (재신청 시 멤버 갱신 목적)"""
        stmt = select(AgentMember).where(AgentMember.agent_id == agent_id)
        members = list(self.db.scalars(stmt).all())
        for member in members:
            self.db.delete(member)
        self.db.flush()


class AsyncAgentRepository:
    """에이전트 Repository (비동기)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, status_code: str | None = None) -> list[Agent]:
        """에이전트 목록 조회 (상태 코드명, 멤버 역할 코드명 포함 eager loading)"""
        stmt = select(Agent).options(
            selectinload(Agent.status),
            selectinload(Agent.members).selectinload(AgentMember.role),
        )
        if status_code:
            stmt = stmt.where(Agent.status_code == status_code)
        stmt = stmt.order_by(Agent.created_at.desc())
        result = await self.db.scalars(stmt)
        return list(result.all())

    async def get_by_id(self, agent_id: str) -> Agent | None:
        """에이전트 ID로 단건 조회 (상태 코드명, 멤버 역할 코드명 포함 eager loading)"""
        stmt = (
            select(Agent)
            .where(Agent.agent_id == agent_id)
            .options(
                selectinload(Agent.status),
                selectinload(Agent.members).selectinload(AgentMember.role),
            )
        )
        result = await self.db.scalars(stmt)
        return result.first()
