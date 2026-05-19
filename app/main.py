# app/main.py
# app/main.py

import hmac
import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.v1.routers import api_router
from app.core.exceptions import (
    database_exception_handler,
    http_exception_handler,
    runtime_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
    value_error_handler,
)
from app.core.logging import setup_logging
from app.core.responses import success_response
from app.db import models  # noqa: F401
from app.db.session import Base, engine, get_db
from app.schemas.common import (
    COMMON_ERROR_RESPONSES,
    ApiResponse,
    DbHealthResult,
    HealthResult,
    PostgisHealthResult,
    RootResult,
)
from app.services.profile_portfolio_draft_service import (
    verify_profile_draft_ocr_runtime_dependencies,
)

load_dotenv(".env.local")
setup_logging()

logger = logging.getLogger(__name__)


def get_root_path() -> str:
    return os.getenv("ROOT_PATH", "").strip()


def get_openapi_server_url() -> str:
    return os.getenv("OPENAPI_SERVER_URL", "/").strip() or "/"


def should_auto_create_db_schema() -> bool:
    return os.getenv("AUTO_CREATE_DB_SCHEMA", "false").lower() == "true"


def should_enable_debug() -> bool:
    return os.getenv("DEBUG", "false").lower() == "true"


def should_require_postgis() -> bool:
    return os.getenv("REQUIRE_POSTGIS", "true").lower() == "true"


def should_require_profile_draft_ocr_dependencies() -> bool:
    return os.getenv("REQUIRE_PROFILE_DRAFT_OCR_DEPENDENCIES", "true").lower() == "true"


def get_internal_api_key() -> str:
    return (os.getenv("INTERNAL_API_KEY") or os.getenv("BRIDGEWORK_FASTAPI_INTERNAL_API_KEY") or "").strip()


def get_internal_api_key_header() -> str:
    return os.getenv("INTERNAL_API_KEY_HEADER", "X-Internal-Api-Key").strip() or "X-Internal-Api-Key"


def get_postgis_version(db: Session) -> str:
    result = db.execute(text("SELECT PostGIS_Version()")).scalar()
    return str(result)


def verify_required_postgis() -> None:
    if not should_require_postgis():
        logger.info("REQUIRE_POSTGIS=false, PostGIS 필수 검사를 건너뜁니다.")
        return

    try:
        with Session(bind=engine) as db:
            version = get_postgis_version(db)
        logger.info("PostGIS 확인 완료: %s", version)
    except DBAPIError as exc:
        logger.exception("REQUIRE_POSTGIS=true 이지만 PostGIS를 사용할 수 없습니다.")
        raise RuntimeError("REQUIRE_POSTGIS=true 이지만 대상 DB에 PostGIS extension이 없거나 사용할 수 없습니다.") from exc


def verify_required_profile_draft_ocr_dependencies() -> None:
    if not should_require_profile_draft_ocr_dependencies():
        logger.warning("REQUIRE_PROFILE_DRAFT_OCR_DEPENDENCIES=false, OCR 의존성 검사를 건너뜁니다.")
        return

    try:
        verify_profile_draft_ocr_runtime_dependencies()
        logger.info("프로필 OCR 런타임 의존성 확인 완료")
    except Exception as exc:
        logger.exception("프로필 OCR 런타임 의존성 검증에 실패했습니다.")
        raise RuntimeError("프로필 OCR 런타임 의존성 검증 실패") from exc


app = FastAPI(
    title="BridgeWork AI Server",
    version="0.1.0",
    debug=should_enable_debug(),
    root_path=get_root_path(),
    root_path_in_servers=False,
)

# 운영 관측 표준에 맞춰 FastAPI HTTP 메트릭을 /metrics로 노출한다.
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app)

verify_required_postgis()
verify_required_profile_draft_ocr_dependencies()

if should_auto_create_db_schema():
    logger.warning("AUTO_CREATE_DB_SCHEMA=true, SQLAlchemy metadata.create_all()을 수행합니다.")
    Base.metadata.create_all(bind=engine)
else:
    logger.info("운영 기본값에 따라 DB 스키마 자동 생성은 비활성화합니다.")

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(RuntimeError, runtime_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
if "*" in origins:
    raise RuntimeError("CORS_ALLOW_ORIGINS must not contain '*' when credentials are enabled.")


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), payment=(), geolocation=()")
    return response


@app.middleware("http")
async def verify_internal_api_key(request: Request, call_next):
    if not request.url.path.startswith("/api/v1/"):
        return await call_next(request)

    expected_key = get_internal_api_key()
    request_id = request.headers.get("X-Request-Id")
    if not expected_key:
        return JSONResponse(
            status_code=503,
            content={
                "code": "INTERNAL_API_KEY_NOT_CONFIGURED",
                "message": "FastAPI 내부 API 인증 설정이 없습니다.",
                "result": {"requestId": request_id},
            },
        )

    provided_key = request.headers.get(get_internal_api_key_header(), "")
    if not hmac.compare_digest(provided_key, expected_key):
        return JSONResponse(
            status_code=401,
            content={
                "code": "UNAUTHORIZED_INTERNAL_API",
                "message": "FastAPI 내부 API 인증에 실패했습니다.",
                "result": {"requestId": request_id},
            },
        )

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
        description=app.description,
    )

    openapi_schema["servers"] = [{"url": get_openapi_server_url()}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get(
    "/",
    response_model=ApiResponse[RootResult],
    responses=COMMON_ERROR_RESPONSES,
)
async def read_root() -> dict[str, object]:
    return success_response({"message": "FastAPI server is running"})


@app.get(
    "/health",
    response_model=ApiResponse[HealthResult],
    responses=COMMON_ERROR_RESPONSES,
)
async def health_check() -> dict[str, object]:
    logger.info("Health check requested")
    return success_response({"status": "ok"})


@app.get(
    "/db-health",
    response_model=ApiResponse[DbHealthResult],
    responses=COMMON_ERROR_RESPONSES,
)
def db_health(db: Session = Depends(get_db)) -> dict[str, object]:
    logger.info("DB Health check requested")
    db.execute(text("SELECT 1"))
    return success_response({"status": "ok", "database": "connected"})


@app.get(
    "/postgis-health",
    response_model=ApiResponse[PostgisHealthResult],
    responses=COMMON_ERROR_RESPONSES,
)
def postgis_health(db: Session = Depends(get_db)) -> dict[str, object]:
    """
    PostgreSQL에 PostGIS extension이 설치되어 있는지 확인합니다.

    이 API는 실제 GIS 거리 계산을 수행하지 않습니다.
    Phase 15에서는 FastAPI가 PostGIS 기능을 사용할 준비가 되었는지만 확인합니다.

    정상 응답 예:
    {
        "status": "ok",
        "postgis": "enabled",
        "version": "3.4 USE_GEOS=..."
    }
    """

    logger.info("PostGIS Health check requested")

    try:
        version = get_postgis_version(db)
    except DBAPIError as exc:
        return success_response(
            {
                "status": "unavailable",
                "postgis": "disabled",
                "reason": str(exc.__cause__ or exc).strip(),
            }
        )

    return success_response(
        {
            "status": "ok",
            "postgis": "enabled",
            "version": version,
        }
    )


app.include_router(api_router)
