# 실행법


## 로컬 실행

### 1. 의존성 설치

```bash
uv sync
```

개발 도구까지 설치하려면 다음 명령을 사용합니다.

```bash
uv sync --dev
```

### 2. 환경변수 설정

로컬 기본값은 `.env.local`을 사용합니다. 최소 실행에는 PostgreSQL/PostGIS 접속 정보와 OpenAI 설정이 필요합니다.

주요 환경변수:

| 변수 | 설명 |
| --- | --- |
| `DATABASE_URL` | PostgreSQL/PostGIS 접속 URL |
| `INTERNAL_API_KEY` 또는 `BRIDGEWORK_FASTAPI_INTERNAL_API_KEY` | Spring이 FastAPI 내부 API 호출 시 보내는 shared secret |
| `INTERNAL_API_KEY_HEADER` | 내부 API 키 헤더명, 기본값 `X-Internal-Api-Key` |
| `CORS_ALLOW_ORIGINS` | 허용할 CORS origin 목록 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `OPENAI_MODEL` | 설명 생성 기본 모델 |
| `PROFILE_DRAFT_OPENAI_MODEL` | 프로필 초안 생성 모델, 미설정 시 `OPENAI_MODEL` 사용 |
| `PROFILE_DRAFT_ENABLE_OCR` | OCR 사용 여부 |
| `PROFILE_DRAFT_MAX_FILE_SIZE_BYTES` | PDF 업로드 최대 크기 |
| `AUTO_CREATE_DB_SCHEMA` | SQLAlchemy 스키마 자동 생성 여부 |
| `REQUIRE_POSTGIS` | 시작 시 PostGIS 필수 확인 여부 |
| `REQUIRE_PROFILE_DRAFT_OCR_DEPENDENCIES` | 시작 시 OCR 의존성 확인 여부 |

### 3. 개발 서버 실행

```bash
uv run python -m uvicorn app.main:app --reload
```

- API 서버: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 4. 헬스체크

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/db-health
curl http://127.0.0.1:8000/postgis-health
curl http://127.0.0.1:8000/metrics
```

## 테스트와 코드 품질

```bash
uv run pytest -v
uv run ruff check . --fix --unsafe-fixes
uv run ruff format .
uv run pre-commit run --all-files
```

테스트 작성 기준은 `.agents/skills/testing/SKILL.md`를 따릅니다.
