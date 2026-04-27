# app/main.py
from fastapi import FastAPI

app = FastAPI(title="aiserver")


@app.get("/")
async def read_root() -> dict[str, str]:
    return {"message": "FastAPI server is running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
