"""
공통 API 응답 스키마 정의
일관된 응답 형식을 유지하기 위해 제네릭 래퍼를 사용한다.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """표준 API 응답 래퍼"""

    success: bool = True
    message: str = "처리되었습니다."
    data: T | None = None

    @classmethod
    def ok(cls, data: T | None = None, message: str = "처리되었습니다.") -> "ApiResponse[T]":
        """성공 응답 생성"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error(cls, message: str = "처리 중 오류가 발생했습니다.") -> "ApiResponse[None]":
        """실패 응답 생성"""
        return cls(success=False, message=message, data=None)


class PageInfo(BaseModel):
    """페이지 정보"""

    total: int
    page: int
    size: int
    total_pages: int


class PagedResponse(BaseModel, Generic[T]):
    """페이지네이션 포함 API 응답"""

    success: bool = True
    message: str = "처리되었습니다."
    data: list[T] = []
    page_info: PageInfo | None = None
