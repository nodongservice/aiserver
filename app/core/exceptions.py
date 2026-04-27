# 파일: app/core/exceptions.py
from typing import Any, Optional

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def get_request_id(request: Request) -> Optional[str]:
    """
    요청 추적 ID를 가져옵니다.

    Spring에서 X-Request-Id 헤더를 넘기면 그대로 사용합니다.
    없으면 None을 반환합니다.

    나중에 middleware에서 request_id를 직접 생성하게 되면
    이 함수만 확장하면 됩니다.
    """
    return request.headers.get("X-Request-Id")


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
        "error_code": "...",
        "message": "...",
        "detail": ...,
        "request_id": "..."
    }
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "detail": detail,
            "request_id": request_id,
        },
    )


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
    return build_error_response(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message="요청 값 검증에 실패했습니다.",
        detail=exc.errors(),
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
    else:
        error_code = "HTTP_ERROR"
        message = "HTTP 요청 처리 중 오류가 발생했습니다."

    return build_error_response(
        status_code=status_code,
        error_code=error_code,
        message=message,
        detail=exc.detail,
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
    return build_error_response(
        status_code=500,
        error_code="AI_SERVICE_INTERNAL_ERROR",
        message="FastAPI AI/GIS 서비스 내부 오류가 발생했습니다.",
        detail={
            "exception_type": exc.__class__.__name__,
        },
        request_id=get_request_id(request),
    )
