# app/main.py
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(".env.local")

app = FastAPI(title="aiserver")

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
