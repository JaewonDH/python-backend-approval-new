"""
FastAPI 애플리케이션 진입점
모든 도메인 라우터를 등록하고 앱을 초기화한다.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.core.config import settings

# ── 도메인 라우터 임포트 ───────────────────────────────────────────────────────
from app.domains.common_codes.router import router as common_codes_router
from app.domains.users.router import router as users_router
from app.domains.agents.router import router as agents_router
from app.domains.approvals.router import router as approvals_router

# ── ORM 모델 임포트 (테이블 메타데이터 등록 목적) ──────────────────────────────
import app.models.common_code  # noqa: F401
import app.models.user         # noqa: F401
import app.models.agent        # noqa: F401
import app.models.approval     # noqa: F401


# =============================================================================
# FastAPI 앱 생성
# =============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="에이전트 신청 및 승인 관리 시스템 API",
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# CORS 미들웨어 설정
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 허용 도메인을 명시해야 한다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# 전역 예외 핸들러
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic 유효성 검사 오류 처리"""
    errors = exc.errors()
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in errors
    )
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": detail, "data": None},
    )


# =============================================================================
# 라우터 등록
# =============================================================================

API_PREFIX = "/api/v1"

app.include_router(common_codes_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(agents_router, prefix=API_PREFIX)
app.include_router(approvals_router, prefix=API_PREFIX)


# =============================================================================
# 헬스 체크
# =============================================================================

@app.get("/health", tags=["시스템"])
def health_check():
    """서버 상태 확인"""
    return ApiResponse.ok(message="서버가 정상 동작 중입니다.")


@app.get("/", tags=["시스템"])
def root():
    """루트 엔드포인트"""
    return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION}"}
