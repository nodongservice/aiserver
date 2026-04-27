# app/main.py
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import Base, engine, get_db

load_dotenv(".env.local")

app = FastAPI(title="aiserver")
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
    return {"status": "ok"}


@app.get("/db-health")
def db_health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
