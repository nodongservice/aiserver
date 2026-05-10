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
uv run python -m uvicorn app.main:app --reload
```

- 기본 주소: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 3. 서버 실행 확인

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/db-health
curl http://127.0.0.1:8000/metrics
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

## CI/CD

같은 EC2 인스턴스에서 FastAPI 컨테이너를 Blue/Green(`19000`, `19001`)으로 배포합니다.
Nginx 라우팅/업스트림 전환은 `backend-infra` 레포에서 관리합니다.

- 워크플로우: `.github/workflows/cicd-main-ec2.yml`
- CI 트리거: 모든 브랜치 `push`, `main` 대상 `pull_request`
- 배포 트리거: `main` 브랜치 `push`, `workflow_dispatch`
- 이미지 빌드/게시: `Dockerfile` 기반 GHCR multi-arch 이미지(`linux/amd64`, `linux/arm64`)
- 서버 배포 스크립트: `deploy/deploy.sh`
- 트래픽 전환 스크립트: `~/bridgework-infra/deploy/fastapi_blue_green_switch.sh`

### 배포 방식

1. `push`/`pull_request`마다 PostGIS 서비스 컨테이너를 띄운 뒤 `pytest`를 실행합니다.
2. `main` 브랜치 `push` 또는 수동 실행일 때만 배포 job이 이어집니다.
3. 배포 job은 GHCR에 `ghcr.io/<owner>/bridgework-aiserver:<commit-sha>` multi-arch 이미지를 push합니다.
4. 운영 `.env`, 배포 스크립트를 EC2로 업로드합니다.
5. EC2에서 GHCR에 로그인하고 이미지를 pull한 뒤 비활성 슬롯(`19000` 또는 `19001`)에 새 컨테이너를 띄웁니다.
6. `/health` 확인 후 `backend-infra`의 `fastapi_blue_green_switch.sh`를 호출해 Nginx 업스트림을 전환합니다.
7. 이전 슬롯 컨테이너를 제거합니다.
8. 배포 성공 후 현재 서비스 이미지 저장소의 최근 이미지 5개만 남기도록 백그라운드에서 이전 이미지를 정리합니다.

EC2에는 Git 저장소를 clone하지 않습니다. GitHub hosted runner가 이미지를 빌드해 GHCR에 게시하고, EC2는 GHCR 이미지와 배포 스크립트만 사용해 배포합니다.
EC2에서는 이미지를 빌드하지 않으므로 배포 중 Docker builder cache 정리는 수행하지 않습니다.

### GitHub Secrets

- `EC2_HOST`
- `EC2_PORT`
- `EC2_USER`
- `EC2_SSH_PRIVATE_KEY`
- `GHCR_USERNAME`
- `GHCR_READ_TOKEN`
- `DATABASE_URL`
- `CORS_ALLOW_ORIGINS`
- `EXPLANATION_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `LOG_LEVEL`
- `AUTO_CREATE_DB_SCHEMA`
- `REQUIRE_POSTGIS`

비어도 되는 값은 빈 문자열로 넣어도 됩니다. 다만 `DATABASE_URL`은 필수입니다.
`GHCR_READ_TOKEN`은 EC2에서 private GHCR 이미지를 pull할 수 있도록 `read:packages` 권한이 필요합니다.
운영에서는 `AUTO_CREATE_DB_SCHEMA=false`, `REQUIRE_POSTGIS=true`를 권장합니다.

### EC2 선행 작업

1. Docker, Nginx, curl 설치
2. 배포 계정에 Docker 실행 권한 부여
3. 배포 계정에 `sudo nginx -t`, `sudo systemctl reload nginx`, `sudo cp` 권한 부여
4. `backend-infra` 레포 CI/CD를 먼저 1회 실행해 `~/bridgework-infra/deploy`를 준비


### 폴더구조
| **영역** | **역할** |
| --- | --- |
| `api` | Spring이 호출하는 API 엔드포인트 |
| `schemas` | 요청/응답 DTO, Pydantic 모델 |
| `services` | 점수 계산, 태그 변환, 설명 생성 로직 |
| `repositories` | PostGIS 조회 |
| `db` | DB 연결 |
| `core` | 환경변수, 로깅 |

## FastAPI 내부 API

Spring Backend가 호출하는 scoring v2 API는 다음과 같습니다.

| API | 역할 |
| --- | --- |
| `POST /api/v1/score/quick` | 기능 2. 최신 공고를 조회하고 직무 적합도만 계산 |
| `POST /api/v1/score/map` | 기능 3. 공고/공공데이터를 조회하고 6개 항목 동일비중 종합 점수 계산 |
| `POST /api/v1/explain/recommendation` | 이미 계산된 점수/근거를 추천 사유, 주의사항, 체크리스트로 변환 |
| `POST /api/v1/profile-draft/from-portfolio` | 포트폴리오 PDF를 분석해 프로필 전체 필드 초안 생성(null 허용) |

구조 원칙:

- 프론트엔드는 FastAPI를 직접 호출하지 않습니다.
- Spring은 선택된 프로필 1개만 FastAPI에 전달합니다.
- FastAPI는 Spring DB의 `pd_*` 정규화 테이블을 직접 조회합니다.
- 점수는 룰 기반이며 LLM은 점수를 직접 결정하지 않습니다.
- 데이터가 부족한 항목은 확정하지 않고 `추가 확인 필요`로 응답합니다.

## 포트폴리오 OCR 기반 프로필 초안 생성

`POST /api/v1/profile-draft/from-portfolio`는 `multipart/form-data`의 `file`(PDF) 1개를 받아 다음 순서로 처리합니다.

1. 파일 검증
- 비어있는 파일 차단
- Content-Type 허용 목록 검증(`application/pdf`)
- PDF 시그니처(`%PDF-`) 검증
- 최대 용량 제한 검증

2. 텍스트 추출 전략(운영형)
- 먼저 `pypdf`로 페이지별 임베디드 텍스트 추출
- 페이지별 품질 점수(한글 비율, 깨짐 문자 비율, 제어문자 비율, 긴 토큰 비율, 이력서 키워드 히트) 계산
- 저품질 페이지에 대해서만 PaddleOCR 수행
- 페이지별로 임베디드 텍스트와 OCR 결과를 비교해 더 신뢰도 높은 텍스트 선택

3. LLM 구조화
- OpenAI Responses API + JSON Schema(`strict=true`)로 스프링 프로필 스키마에 맞춰 구조화
- 전체 필드를 항상 포함하고, 근거가 부족한 값은 `null`로 반환

4. 응답
- `draft`: 전체 필드 초안
- `missingFields`: `null`인 필드명 목록
- `confidence`, `ocrTextLength`, `modelVersion`, `warnings`

## 포트폴리오 OCR/LLM 관련 환경변수

- `PROFILE_DRAFT_OPENAI_MODEL` (기본: `OPENAI_MODEL`)
- `PROFILE_DRAFT_OPENAI_TIMEOUT_SECONDS` (기본: `40`)
- `PROFILE_DRAFT_MAX_FILE_SIZE_BYTES` (기본: `10485760`)
- `PROFILE_DRAFT_MAX_PAGES` (기본: `10`)
- `PROFILE_DRAFT_PDF_RENDER_SCALE` (기본: `2.0`)
- `PROFILE_DRAFT_MAX_PROMPT_CHARS` (기본: `15000`)
- `PROFILE_DRAFT_ALLOWED_CONTENT_TYPES` (코드 기본값: `application/pdf`)
- `PROFILE_DRAFT_EMBEDDED_QUALITY_THRESHOLD` (기본: `55`)
- `PROFILE_DRAFT_EMBEDDED_MIN_CHARS_PER_PAGE` (기본: `40`)
- `PROFILE_DRAFT_EMBEDDED_MAX_REPLACEMENT_RATIO` (기본: `0.08`)
- `PROFILE_DRAFT_EMBEDDED_MAX_CONTROL_RATIO` (기본: `0.02`)
- `PROFILE_DRAFT_OCR_PREFER_MARGIN` (기본: `8`)
- `REQUIRE_PROFILE_DRAFT_OCR_DEPENDENCIES` (기본: `true`, 시작 시 OCR 의존성 import 검증)

## 스코어링 DB 조회 기준

주요 조회 테이블:

| 테이블 | 용도 |
| --- | --- |
| `pd_kepad_recruitment` | 공고 조회, quick/map scoring의 기본 공고 소스 |
| `pd_kepad_standard_workplace` | 장애인 표준사업장 매칭 |
| `pd_transport_support_center` | 접근성 요약 점수 근거 |
| `pd_nationwide_bus_stop` | 접근성 요약 점수 근거 |
| `pd_nationwide_crosswalk` | 접근성 요약 점수 근거 |
| `pd_nationwide_traffic_light` | 접근성 요약 점수 근거 |
| `pd_seoul_subway_entrance_lift` | 접근성 요약 점수 근거 |
| `pd_seoul_walking_network` | 접근성 요약 점수 근거 |
| `pd_kepad_support_agency` | 근로지원인 수행기관 지도 레이어용, 점수 미반영 |

`pd_kepad_recruitment`의 근무지 좌표는 `geo_latitude`, `geo_longitude`를 사용합니다.
`pd_kepad_support_agency`의 위치도 `geo_latitude`, `geo_longitude`를 사용하지만 기능정의서 기준 점수에는 반영하지 않습니다.

## 사용데이터 목록 
../backend/README.md 참고
test
