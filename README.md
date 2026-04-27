# nodong-aiserver

FastAPI + `uv` 기반 서버 프로젝트입니다.

## 자주 쓰는 명령어

### 1. 의존성 설치

```bash
uv sync
uv sync --dev
```

`pyproject.toml` / `uv.lock` 기준으로 가상환경과 패키지를 맞춥니다.

### 2. 개발 서버 실행

```bash
uv run python -m uvicorn main:app --reload
```

- 기본 주소: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 3. 서버 실행 확인

```bash
curl http://127.0.0.1:8000/health
```

### 4. 패키지 추가

```bash
uv add 패키지명
```

### 5. 개발용 패키지 추가

```bash
uv add --dev pytest
```

### 6. 포매터 / 린트 실행

```bash
uv run ruff check . --fix --unsafe-fixes

uv run ruff format .
```

### 7. pre-commit 설치 및 실행

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
### 8. pytest

```bash
uv run pytest -v
```


### 폴더구조
| **영역** | **역할** |
| --- | --- |
| `api` | Spring이 호출하는 API 엔드포인트 |
| `schemas` | 요청/응답 DTO, Pydantic 모델 |
| `services` | 점수 계산, 태그 변환, 설명 생성 로직 |
| `repositories` | PostGIS 조회 |
| `db` | DB 연결 |
| `core` | 환경변수, 로깅 |