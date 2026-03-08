"""
공통 코드 Service
비즈니스 로직을 담당한다.
"""

from sqlalchemy.orm import Session

from app.common.exceptions import ConflictError, NotFoundError
from app.domains.common_codes.repository import CommonCodeRepository
from app.domains.common_codes.schemas import CommonCodeCreate, CommonCodeUpdate
from app.models.common_code import CommonCode


class CommonCodeService:
    """공통 코드 서비스 (동기)"""

    def __init__(self, db: Session):
        self.repo = CommonCodeRepository(db)
        self.db = db

    def get_all(self, is_active: str | None = None) -> list[CommonCode]:
        """전체 공통 코드 목록 반환"""
        return self.repo.get_all(is_active=is_active)

    def get_by_group(self, group_code: str) -> list[CommonCode]:
        """그룹별 활성 공통 코드 목록 반환"""
        return self.repo.get_by_group(group_code=group_code)

    def get_by_id(self, code_id: str) -> CommonCode:
        """코드 ID로 단건 조회 (없으면 404)"""
        code = self.repo.get_by_id(code_id)
        if not code:
            raise NotFoundError(f"공통 코드를 찾을 수 없습니다. code_id={code_id}")
        return code

    def create(self, body: CommonCodeCreate) -> CommonCode:
        """공통 코드 생성 (중복 확인 포함)"""
        existing = self.repo.get_by_id(body.code_id)
        if existing:
            raise ConflictError(f"이미 존재하는 코드 ID입니다. code_id={body.code_id}")
        code = CommonCode(**body.model_dump())
        self.repo.create(code)
        self.db.commit()
        self.db.refresh(code)
        return code

    def update(self, code_id: str, body: CommonCodeUpdate) -> CommonCode:
        """공통 코드 수정"""
        code = self.get_by_id(code_id)
        updated = self.repo.update(code, body.model_dump(exclude_none=True))
        self.db.commit()
        self.db.refresh(updated)
        return updated

    def delete(self, code_id: str) -> None:
        """공통 코드 삭제"""
        code = self.get_by_id(code_id)
        self.repo.delete(code)
        self.db.commit()
