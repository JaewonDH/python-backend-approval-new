"""
공통 코드 Repository
동기/비동기 DB 접근 로직을 담당한다.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.common_code import CommonCode


class CommonCodeRepository:
    """공통 코드 Repository (동기)"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, is_active: str | None = None) -> list[CommonCode]:
        """전체 공통 코드 조회"""
        stmt = select(CommonCode)
        if is_active:
            stmt = stmt.where(CommonCode.is_active == is_active)
        stmt = stmt.order_by(CommonCode.group_code, CommonCode.sort_order)
        return list(self.db.scalars(stmt).all())

    def get_by_group(self, group_code: str, is_active: str = "Y") -> list[CommonCode]:
        """그룹 코드별 공통 코드 조회"""
        stmt = (
            select(CommonCode)
            .where(CommonCode.group_code == group_code)
            .where(CommonCode.is_active == is_active)
            .order_by(CommonCode.sort_order)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, code_id: str) -> CommonCode | None:
        """코드 ID로 단건 조회"""
        return self.db.get(CommonCode, code_id)

    def create(self, code: CommonCode) -> CommonCode:
        """공통 코드 생성"""
        self.db.add(code)
        self.db.flush()
        return code

    def update(self, code: CommonCode, data: dict) -> CommonCode:
        """공통 코드 수정"""
        for key, value in data.items():
            if value is not None:
                setattr(code, key, value)
        self.db.flush()
        return code

    def delete(self, code: CommonCode) -> None:
        """공통 코드 삭제"""
        self.db.delete(code)
        self.db.flush()


class AsyncCommonCodeRepository:
    """공통 코드 Repository (비동기)"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, is_active: str | None = None) -> list[CommonCode]:
        """전체 공통 코드 조회"""
        stmt = select(CommonCode)
        if is_active:
            stmt = stmt.where(CommonCode.is_active == is_active)
        stmt = stmt.order_by(CommonCode.group_code, CommonCode.sort_order)
        result = await self.db.scalars(stmt)
        return list(result.all())

    async def get_by_group(self, group_code: str, is_active: str = "Y") -> list[CommonCode]:
        """그룹 코드별 공통 코드 조회"""
        stmt = (
            select(CommonCode)
            .where(CommonCode.group_code == group_code)
            .where(CommonCode.is_active == is_active)
            .order_by(CommonCode.sort_order)
        )
        result = await self.db.scalars(stmt)
        return list(result.all())

    async def get_by_id(self, code_id: str) -> CommonCode | None:
        """코드 ID로 단건 조회"""
        return await self.db.get(CommonCode, code_id)

    async def create(self, code: CommonCode) -> CommonCode:
        """공통 코드 생성"""
        self.db.add(code)
        await self.db.flush()
        return code
