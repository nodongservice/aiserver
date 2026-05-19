FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    FLAGS_use_mkldnn=false

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libstdc++6 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r bridgework && useradd -r -g bridgework bridgework

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app

ARG RUN_OCR_RUNTIME_SMOKE=false
RUN if [ "$RUN_OCR_RUNTIME_SMOKE" = "true" ]; then \
      /app/.venv/bin/python -c "from app.services.profile_portfolio_draft_service import verify_profile_draft_ocr_runtime_dependencies; verify_profile_draft_ocr_runtime_dependencies(); print('OCR runtime dependency verification passed')"; \
    fi

EXPOSE 8000

RUN chown -R bridgework:bridgework /app
USER bridgework

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
