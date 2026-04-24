# nodong-aiserver

FastAPI + `uv` 기반 서버 프로젝트입니다.

## 자주 쓰는 명령어

### 1. 의존성 설치

```bash
uv sync
```

`pyproject.toml` / `uv.lock` 기준으로 가상환경과 패키지를 맞춥니다.

### 2. 개발 서버 실행

```bash
uv run uvicorn main:app --reload
```

- 기본 주소: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 3. 서버 실행 확인

```bash
curl http://127.0.0.1:8000/health
```

예상 응답:

```json
{"status":"ok"}
```

### 4. 패키지 추가

```bash
uv add 패키지명
```

예시:

```bash
uv add sqlalchemy
```

### 5. 개발용 패키지 추가

```bash
uv add --dev pytest
```

### 6. 포매터 / 린트 실행

```bash
uv run ruff check . --fix
uv run ruff format .
```

### 7. pre-commit 설치 및 실행

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

### 8. 파이썬 코드 한 번 실행

```bash
uv run python main.py
```

현재 `main.py`는 FastAPI 앱 엔트리포인트라서, 실제 서버 실행은 `uvicorn` 명령을 사용하는 것이 기준입니다.
