# app/main.py
# app/main.py

import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.routes_analysis import router as analysis_router
from app.api.v1.routes_explanation import router as explanation_router
from app.api.v1.routes_tags import router as tags_router
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


app.include_router(analysis_router)
app.include_router(tags_router)
app.include_router(explanation_router)
