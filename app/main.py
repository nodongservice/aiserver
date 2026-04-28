# app/main.py
# app/main.py

import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.routes_analysis import router as analysis_router
from app.api.v1.routes_explanation import router as explanation_router
from app.api.v1.routes_public_data import router as public_data_router
from app.api.v1.routes_tags import router as tags_router
from app.core.exceptions import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.api.v1.routers import api_router
from app.core.logging import setup_logging
from app.db import models  # noqa: F401
from app.db.session import Base, engine, get_db

load_dotenv(".env.local")
setup_logging()

logger = logging.getLogger(__name__)


app = FastAPI(
    title="BridgeWork AI Server",
    version="0.1.0",
)
Base.metadata.create_all(bind=engine)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.include_router(public_data_router)

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

    result = db.execute(text("SELECT PostGIS_Version()")).scalar()

    return {
        "status": "ok",
        "postgis": "enabled",
        "version": str(result),
    }


app.include_router(api_router)
