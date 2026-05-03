# app/main.py
# app/main.py

import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.routers import api_router
from app.core.exceptions import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.db import models  # noqa: F401
from app.db.session import Base, engine, get_db

load_dotenv(".env.local")
setup_logging()

logger = logging.getLogger(__name__)


def should_auto_create_db_schema() -> bool:
    return os.getenv("AUTO_CREATE_DB_SCHEMA", "false").lower() == "true"


def should_require_postgis() -> bool:
    return os.getenv("REQUIRE_POSTGIS", "true").lower() == "true"


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
        raise RuntimeError(
            "REQUIRE_POSTGIS=true 이지만 대상 DB에 PostGIS extension이 없거나 사용할 수 없습니다."
        ) from exc


app = FastAPI(
    title="BridgeWork AI Server",
    version="0.1.0",
)

verify_required_postgis()

if should_auto_create_db_schema():
    logger.warning("AUTO_CREATE_DB_SCHEMA=true, SQLAlchemy metadata.create_all()을 수행합니다.")
    Base.metadata.create_all(bind=engine)
else:
    logger.info("운영 기본값에 따라 DB 스키마 자동 생성은 비활성화합니다.")

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": "FastAPI server is running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    logger.info("Health check requested")
    return {"status": "ok"}


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)) -> dict[str, str]:
    logger.info("DB Health check requested")
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/postgis-health")
def postgis_health(db: Session = Depends(get_db)) -> dict[str, str]:
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
        return {
            "status": "unavailable",
            "postgis": "disabled",
            "reason": str(exc.__cause__ or exc).strip(),
        }

    return {
        "status": "ok",
        "postgis": "enabled",
        "version": version,
    }


app.include_router(api_router)
