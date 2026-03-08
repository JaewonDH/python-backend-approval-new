"""
공통 예외 클래스 정의
"""

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """리소스를 찾을 수 없을 때 발생하는 예외"""

    def __init__(self, detail: str = "리소스를 찾을 수 없습니다."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestError(HTTPException):
    """잘못된 요청일 때 발생하는 예외"""

    def __init__(self, detail: str = "잘못된 요청입니다."):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ForbiddenError(HTTPException):
    """권한이 없을 때 발생하는 예외"""

    def __init__(self, detail: str = "권한이 없습니다."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictError(HTTPException):
    """중복/충돌이 발생했을 때 사용하는 예외"""

    def __init__(self, detail: str = "충돌이 발생했습니다."):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
