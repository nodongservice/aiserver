# 파일: app/core/exceptions.py
import logging
import re
from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

REDACTED_VALUE = "[REDACTED]"
SENSITIVE_TEXT_PATTERNS = (
    (
        re.compile(r"\b(bearer|basic)\s+[a-z0-9._~+/=-]+", re.IGNORECASE),
        lambda match: f"{match.group(1)} {REDACTED_VALUE}",
    ),
    (
        re.compile(
            r"([?&](?:code|token|access_token|refresh_token|signupToken|withdrawalCancelToken|serviceKey|apiKey|apikey|key|secret|password)=)[^&\s]+",
            re.IGNORECASE,
        ),
        lambda match: f"{match.group(1)}{REDACTED_VALUE}",
    ),
    (
        re.compile(r"(//[^/\s:@]+:)[^@\s/]+(@)"),
        lambda match: f"{match.group(1)}{REDACTED_VALUE}{match.group(2)}",
    ),
    (
        re.compile(r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b"),
        lambda _match: REDACTED_VALUE,
    ),
    (
        re.compile(
            r"\b(password|passwd|token|accessToken|refreshToken|signupToken|withdrawalCancelToken|secret|credential|api[-_]?key|serviceKey|session|jwt)\s*[:=]\s*([^\s,;]+)",
            re.IGNORECASE,
        ),
        lambda match: f"{match.group(1)}={REDACTED_VALUE}",
    ),
)


def sanitize_log_value(value: Any) -> str:
    text = str(value)
    for pattern, replacement in SENSITIVE_TEXT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.replace("\n", " ").replace("\r", " ").strip()


def get_request_id(request: Request) -> Optional[str]:
    """
    요청 추적 ID를 가져옵니다.

    Spring에서 X-Request-Id 헤더를 넘기면 그대로 사용합니다.
    없으면 None을 반환합니다.

    나중에 middleware에서 request_id를 직접 생성하게 되면
    이 함수만 확장하면 됩니다.
    """
    return request.headers.get("X-Request-Id")


def get_request_log_context(request: Request) -> str:
    """
    터미널 로그에서 요청을 추적하기 위한 공통 문맥입니다.
    """
    client = request.client.host if request.client else "-"
    return f"method={request.method} path={request.url.path} client={client} request_id={get_request_id(request) or '-'}"


def log_handled_exception(
    *,
    request: Request,
    exc: Exception,
    status_code: int,
    error_code: str,
    message: str,
    include_traceback: bool = True,
) -> None:
    """
    클라이언트 응답은 공통 포맷으로 유지하고, 서버 로그에는 원인 파악용
    요청 문맥과 traceback을 남깁니다.
    """
    log_message = "%s status_code=%s error_code=%s exception_type=%s reason=%r %s" % (
        message,
        status_code,
        error_code,
        exc.__class__.__name__,
        sanitize_log_value(exc),
        get_request_log_context(request),
    )
    if include_traceback:
        logger.error(log_message)
    else:
        logger.warning(log_message)


def log_database_exception(request: Request, exc: SQLAlchemyError) -> None:
    """
    SQLAlchemy 예외는 운영 로그에 SQL 파라미터나 사용자 입력값이 남지 않도록
    예외 유형과 요청 문맥만 기록합니다.
    """
    orig = getattr(exc, "orig", None)

    logger.error(
        ("데이터베이스 처리 중 오류가 발생했습니다. status_code=503 error_code=DATABASE_ERROR exception_type=%s dbapi_exception_type=%s reason=%r %s"),
        exc.__class__.__name__,
        orig.__class__.__name__ if orig is not None else "-",
        sanitize_log_value(orig or exc),
        get_request_log_context(request),
    )


def build_error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    detail: Any = None,
    request_id: Optional[str] = None,
) -> JSONResponse:
    """
    Spring이 처리하기 쉬운 공통 에러 응답을 생성합니다.

    모든 에러 응답은 아래 구조를 따릅니다.

    {
        "code": "...",
        "message": "...",
        "result": {
            "detail": ...,
            "requestId": "..."
        }
    }
    """
    result = {
        "detail": detail,
        "requestId": request_id,
    }
    return JSONResponse(
        status_code=status_code,
        content={
            "code": error_code,
            "message": message,
            "result": result,
        },
    )


def build_safe_error_detail(
    exc: Exception,
    *,
    include_reason: bool = False,
) -> dict[str, str]:
    detail = {"exception_type": exc.__class__.__name__}
    if include_reason:
        detail["reason"] = sanitize_log_value(exc)
    return detail


def build_safe_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    safe_errors = []
    for error in exc.errors():
        safe_errors.append({key: value for key, value in error.items() if key not in {"input", "ctx"}})
    return safe_errors


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    FastAPI 요청 검증 실패 처리입니다.

    예:
    - 필수 필드 누락
    - 타입 오류
    - JSON 구조 불일치

    기존 FastAPI 기본 422 응답 대신,
    Spring 연동용 공통 포맷으로 반환합니다.
    """
    logger.warning(
        "요청 값 검증에 실패했습니다. status_code=422 error_code=VALIDATION_ERROR errors=%s %s",
        build_safe_validation_errors(exc),
        get_request_log_context(request),
    )
    return build_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="요청 값 검증에 실패했습니다.",
        detail=build_safe_validation_errors(exc),
        request_id=get_request_id(request),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    FastAPI/Starlette HTTPException 처리입니다.

    예:
    - 404 Not Found
    - 401 Unauthorized
    - 403 Forbidden
    """
    status_code = exc.status_code

    if status_code == 404:
        error_code = "NOT_FOUND"
        message = "요청한 API 또는 리소스를 찾을 수 없습니다."
    elif status_code == 401:
        error_code = "UNAUTHORIZED_INTERNAL_REQUEST"
        message = "내부 API 인증에 실패했습니다."
    elif status_code == 403:
        error_code = "FORBIDDEN_INTERNAL_REQUEST"
        message = "내부 API 접근 권한이 없습니다."
    elif status_code == 422:
        error_code = "VALIDATION_ERROR"
        message = "요청 값 검증에 실패했습니다."
    else:
        error_code = f"HTTP_{status_code}"
        message = "HTTP 요청 처리 중 오류가 발생했습니다."

    logger.warning(
        "%s status_code=%s error_code=%s detail=%r %s",
        message,
        status_code,
        error_code,
        sanitize_log_value(exc.detail),
        get_request_log_context(request),
    )
    return build_error_response(
        status_code=status_code,
        error_code=error_code,
        message=message,
        detail=exc.detail,
        request_id=get_request_id(request),
    )


async def value_error_handler(
    request: Request,
    exc: ValueError,
) -> JSONResponse:
    """
    서비스 계층의 잘못된 값 오류를 처리합니다.
    """
    log_handled_exception(
        request=request,
        exc=exc,
        status_code=400,
        error_code="BAD_REQUEST",
        message="요청 값을 처리할 수 없습니다.",
    )
    return build_error_response(
        status_code=400,
        error_code="BAD_REQUEST",
        message="요청 값을 처리할 수 없습니다.",
        detail=build_safe_error_detail(exc),
        request_id=get_request_id(request),
    )


async def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    """
    DB 조회/연결 오류를 처리합니다.
    """
    log_database_exception(request, exc)
    return build_error_response(
        status_code=503,
        error_code="DATABASE_ERROR",
        message="데이터베이스 처리 중 오류가 발생했습니다.",
        detail={"exception_type": exc.__class__.__name__},
        request_id=get_request_id(request),
    )


async def runtime_exception_handler(
    request: Request,
    exc: RuntimeError,
) -> JSONResponse:
    """
    실행 환경 또는 내부 서비스 상태 오류를 처리합니다.
    """
    log_handled_exception(
        request=request,
        exc=exc,
        status_code=500,
        error_code="AI_SERVICE_RUNTIME_ERROR",
        message="FastAPI AI/GIS 서비스 실행 중 오류가 발생했습니다.",
    )
    return build_error_response(
        status_code=500,
        error_code="AI_SERVICE_RUNTIME_ERROR",
        message="FastAPI AI/GIS 서비스 실행 중 오류가 발생했습니다.",
        detail=build_safe_error_detail(exc),
        request_id=get_request_id(request),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    예상하지 못한 서버 내부 오류 처리입니다.

    운영 환경에서는 detail에 내부 예외 메시지를 그대로 노출하지 않는 것이 좋습니다.
    지금은 Spring 연동 테스트를 위해 예외 타입만 간단히 내려줍니다.
    """
    log_handled_exception(
        request=request,
        exc=exc,
        status_code=500,
        error_code="AI_SERVICE_INTERNAL_ERROR",
        message="FastAPI AI/GIS 서비스 내부 오류가 발생했습니다.",
    )
    return build_error_response(
        status_code=500,
        error_code="AI_SERVICE_INTERNAL_ERROR",
        message="FastAPI AI/GIS 서비스 내부 오류가 발생했습니다.",
        detail={
            "exception_type": exc.__class__.__name__,
        },
        request_id=get_request_id(request),
    )
