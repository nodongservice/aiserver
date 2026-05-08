from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: str
    message: str
    result: Optional[T] = None


class ErrorResult(BaseModel):
    detail: Optional[Any] = None
    requestId: Optional[str] = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    result: ErrorResult


class RootResult(BaseModel):
    message: str


class HealthResult(BaseModel):
    status: str


class DbHealthResult(BaseModel):
    status: str
    database: str


class PostgisHealthResult(BaseModel):
    status: str
    postgis: str
    version: Optional[str] = None
    reason: Optional[str] = None


COMMON_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "잘못된 요청 값"},
    401: {"model": ErrorResponse, "description": "내부 API 인증 실패"},
    403: {"model": ErrorResponse, "description": "내부 API 접근 권한 없음"},
    404: {"model": ErrorResponse, "description": "API 또는 리소스 없음"},
    422: {"model": ErrorResponse, "description": "요청 값 검증 실패"},
    500: {"model": ErrorResponse, "description": "AI/GIS 서비스 내부 오류"},
    503: {"model": ErrorResponse, "description": "데이터베이스 처리 오류"},
}
