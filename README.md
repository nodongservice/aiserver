# BridgeWork AI/GIS Server

장애인 구직자의 프로필과 공공데이터를 결합해 **일자리 적합도**, **근무지 접근성**, **장애 지원 가능성**, **추천 사유**를 계산하는 FastAPI 기반 AI/GIS 분석 서버입니다.

BridgeWork 전체 서비스에서 이 레포는 Spring Backend가 내부 API로 호출하는 AI 분석 서버 역할을 담당합니다. 프론트엔드는 FastAPI를 직접 호출하지 않고, Spring Backend가 인증/프로필/공공데이터 동기화/API 게이트웨이를 처리한 뒤 필요한 분석 요청만 FastAPI로 전달합니다.

## 전체 구조


```text
React Frontend
  -> Nginx
  -> Spring Backend
  -> FastAPI AI/GIS Server
  -> PostgreSQL/PostGIS + Redis + OpenAI API
```

아래 표의 레포명을 클릭하면 각 GitHub 레포지토리로 이동합니다.

| 레포 | 역할 |
| --- | --- |
| [frontend](https://github.com/nodongservice/frontend) | React 웹 클라이언트, 소셜 로그인, 온보딩, 프로필, 추천/지도 화면 |
| [backend](https://github.com/nodongservice/backend) | Spring Boot API 서버, 인증/프로필/공공데이터 동기화, FastAPI 게이트웨이 |
| [aiserver](https://github.com/nodongservice/aiserver) | FastAPI AI/GIS 분석 서버, 스코어링, OCR/LLM 프로필 초안, 추천 설명 생성 |
| [backend-infra](https://github.com/nodongservice/backend-infra) | Nginx, Blue/Green 전환 스크립트, Prometheus/Grafana/Loki/Alloy 모니터링 |

## 핵심 기능

### 1. 포트폴리오 PDF 기반 프로필 초안 생성

![Portfolio OCR and profile draft flow](images/image4.png)

사용자가 PDF 이력서/포트폴리오를 업로드하면 Spring Backend가 파일을 검증하고 FastAPI로 전달합니다. FastAPI는 PDF 텍스트를 추출한 뒤, 품질이 낮은 페이지만 OCR로 보강하고, OpenAI Responses API와 JSON Schema를 이용해 BridgeWork 프로필 스키마에 맞는 초안을 생성합니다.

- `pypdf`로 페이지별 임베디드 텍스트 추출
- 한글 비율, 깨짐 문자, 제어문자, 긴 토큰, 이력서 키워드 기반 텍스트 품질 평가
- 저품질 페이지에 한해 `PaddleOCR` 수행
- 임베디드 텍스트와 OCR 결과 중 신뢰도 높은 텍스트 선택
- OpenAI Responses API + strict JSON Schema로 프로필 필드 구조화
- 근거가 부족한 필드는 추측하지 않고 `null`로 반환
- `missingFields`, `confidence`, `warnings`를 함께 제공해 사용자 확인/수정 흐름 지원

### 2. 퀵 맞춤 일자리 추천

![Quick recommendation flow](images/image2.png)

퀵 추천은 별도 퀵공고 화면에서 최신 공고를 빠르게 확인하는 흐름입니다. AI 직무 적합도 토글이 켜져 있으면 Spring Backend가 선택된 프로필 1개를 FastAPI로 전달하고, FastAPI가 최신 공고별 직무 적합도와 근거를 계산합니다.

- 모집 중이고 마감일이 지나지 않은 장애인 구인 공고 조회
- 좌표가 있는 공고 우선 정렬
- `limit`/`offset` 기반 페이지네이션
- 사용자 지원 직무, 기술, 학력, 경력과 공고 조건 비교
- `job_fit_score`, 추천 근거, 위험요소 반환
- AI 토글 OFF 시 Spring Backend가 최신 공고만 조회

### 3. 지역 접근성 지도 추천
```mermaid
flowchart LR
    A["React Frontend<br/>지역 접근성 지도"] -->|프로필 선택, aiEnabled=true| B["Spring Backend<br/>/api/v1/recommend/map"]
    B -->|선택 프로필 1개 전달| C["FastAPI AI/GIS<br/>POST /api/v1/score/map"]

    C --> D["ScoreRequest 검증<br/>profile, limit, offset"]
    D --> E["공고 후보 조회<br/>pd_kepad_recruitment<br/>모집중/마감 전/좌표 우선"]
    E --> F["공고 컨텍스트 보강<br/>직무분류, 직업훈련, 취업역량 프로그램"]

    F --> G["표준사업장 매칭<br/>pd_kepad_standard_workplace"]
    F --> H["PostGIS 접근성 근거 조회<br/>ST_DWithin / ST_Distance"]
    F --> I["거주지-근무지<br/>대중교통 시간 조회"]

    G --> J["6개 항목 AI 점수 계산"]
    H --> J
    I --> J

    J --> J1["직무 적합도"]
    J --> J2["근무조건 적합도"]
    J --> J3["장애 지원 적합도"]
    J --> J4["업무환경 적합도"]
    J --> J5["기업 안정성/채용 친화도"]
    J --> J6["접근성 요약 점수"]

    J1 --> K["동일 비중 총점 계산<br/>round(sum / 6)"]
    J2 --> K
    J3 --> K
    J4 --> K
    J5 --> K
    J6 --> K

    K --> L["추천 사유 생성<br/>reasons"]
    K --> M["위험요소 생성<br/>risk_factors"]
    K --> N["근거 생성<br/>evidence_items"]

    L --> O["총점 내림차순 정렬"]
    M --> O
    N --> O

    O --> P["limit / offset 적용"]
    P --> Q["MapScoreResponse 반환<br/>job, score_detail, total_score,<br/>transit_time, reasons, risk_factors, evidence_items"]

    Q --> B
    B --> A

    R["근로지원인 수행기관 마커<br/>/api/v1/map/support-agencies"] -. "점수 미반영<br/>지도 레이어 전용" .-> A
```


지도 추천은 공고의 근무지 주변 접근성 공공데이터와 사용자 프로필을 함께 분석해 종합 점수를 계산합니다. 점수는 LLM이 직접 결정하지 않고, FastAPI의 룰 기반 스코어링 모듈이 계산합니다.

6개 항목을 동일 비중으로 계산합니다.

| 항목 | 설명 |
| --- | --- |
| 직무 적합도 | 직무명, 요구 경력, 학력, 자격, 기술 키워드 기반 적합도 |
| 근무조건 적합도 | 고용형태, 임금형태, 모집기간, 근무 가능 조건 |
| 장애 지원 적합도 | 장애 유형/정도, 표준사업장 매칭, 지원 필요사항 |
| 업무환경 적합도 | 양손사용, 시력, 듣고 말하기, 서거나 걷기, 드는힘 등 작업환경 |
| 기업 안정성/채용 친화도 | 표준사업장 인증, 담당기관, 공고 등록 정보 |
| 접근성 요약 점수 | 근무지 주변 이동지원센터, 버스정류장, 횡단보도, 신호등, 지하철 리프트 등 |

### 4. 추천 설명 생성

스코어링 결과는 바로 사용자 문장으로 노출하지 않고, 별도 설명 생성 API를 통해 추천 사유, 주의사항, 체크리스트로 변환합니다.

- LLM은 점수를 결정하지 않음
- 이미 계산된 점수, 근거, 위험요소만 설명 재료로 사용
- 제공자 설정에 따라 OpenAI 기반 설명 또는 룰 기반 fallback 설명 사용
- 상담기관 또는 사용자 화면에서 바로 읽을 수 있는 문장 형태로 반환

## AI/GIS 처리 원칙

- **근거 기반 계산**: 공공데이터와 프로필 입력값을 기준으로 점수를 계산합니다.
- **LLM 역할 제한**: LLM은 구조화와 설명 생성에 사용하며, 핵심 점수는 룰 기반으로 산정합니다.
- **불확실성 보존**: 정보가 부족한 필드는 추측하지 않고 `null`, `추가 확인 필요`, `warnings`로 전달합니다.
- **PostGIS 활용**: 근무지 좌표 주변의 접근성 데이터를 반경 기반으로 조회합니다.
- **운영 안정성**: OCR 프로세스 격리, OCR 대상 페이지 최소화, 접근성 조회 캐시, 헬스체크/메트릭을 제공합니다.

## 주요 API

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/health` | 서버 헬스체크 |
| `GET` | `/db-health` | DB 연결 확인 |
| `GET` | `/postgis-health` | PostGIS extension 확인 |
| `GET` | `/metrics` | Prometheus 메트릭 |
| `POST` | `/api/v1/profile-draft/from-portfolio` | PDF 포트폴리오 기반 프로필 초안 생성 |
| `POST` | `/api/v1/score/quick` | 전체 후보 랭킹 기반 퀵 추천 점수 계산 |
| `POST` | `/api/v1/score/map` | 지도 추천용 6개 항목 종합 점수 계산 |
| `POST` | `/api/v1/explain/recommendation` | 추천 사유/주의사항/체크리스트 생성 |

### 추천 점수 API 규칙

- `limit`: 1~100
- `offset`: 0 이상
- 후보 공고는 `posting_status=ACTIVE` 또는 상태값 없음, 직무명/사업장명 존재, 마감일이 지나지 않은 공고 전체를 기준으로 조회합니다.
- FastAPI는 전체 후보를 빠른 프로필 기반 점수로 먼저 랭킹하고, 상위 1000개 안에서 `limit`/`offset`을 적용합니다. 후보 랭킹은 같은 프로필/모드에서 짧게 재사용해 1개 단위 스트리밍 호출의 반복 조회 비용을 줄입니다.
- 퀵 추천 점수는 직무 적합도만으로 산정하지 않고 직무 적합도, 근무조건, 거주지-근무지 거리 감점을 함께 반영합니다.
- 지도 추천은 빠른 후보 랭킹 상위 1000개를 대상으로 접근성/통근/공공데이터 정밀 점수를 계산한 뒤 점수 기준 정렬 후 `limit`/`offset`을 적용합니다.
- Spring Backend가 AI ON 100개 배치 요청을 1개 단위로 나눠 호출할 수 있으므로, FastAPI는 `limit=1` 요청도 일반 요청과 동일하게 안정적으로 처리해야 합니다.

## 기술 스택

| 영역 | 사용 기술 |
| --- | --- |
| API | FastAPI, Uvicorn, Pydantic |
| DB/GIS | PostgreSQL, PostGIS, SQLAlchemy, GeoAlchemy2 |
| OCR | pypdf, pypdfium2, PaddleOCR, PaddlePaddle |
| AI | OpenAI Responses API, JSON Schema structured output |
| 운영 | Docker, GHCR, GitHub Actions, Blue/Green deployment |
| 관측 | Prometheus metrics, Grafana, Loki, Alloy |
| 품질 | pytest, ruff, pre-commit, uv |

## 폴더 구조

```text
app/
  api/                 FastAPI 라우터
  core/                설정, 예외 처리, 로깅, 공통 응답
  db/                  SQLAlchemy 세션과 DB 모델
  repositories/        공고/공공데이터/PostGIS 조회
  schemas/             요청/응답 Pydantic 모델
  services/            OCR, LLM, 스코어링, 설명 생성 비즈니스 로직
  services/scoring/    6개 점수 항목별 계산 모듈
  utils/               지리 좌표 유틸리티
tests/                 pytest 테스트
deploy/                EC2 배포 스크립트
images/                README 및 제출 문서용 다이어그램
```

## 배포

이 레포는 GitHub Actions에서 Docker 이미지를 빌드해 GHCR에 게시하고, EC2에서 비활성 Blue/Green 슬롯에 새 컨테이너를 띄운 뒤 Nginx 업스트림을 전환합니다.

- 워크플로우: `.github/workflows/cicd-main-ec2.yml`
- 컨테이너 이미지: `ghcr.io/<owner>/bridgework-aiserver:<commit-sha>`
- Blue/Green 포트: `19000`, `19001`
- 트래픽 전환: `../backend-infra/deploy/fastapi_blue_green_switch.sh`
- 운영 모니터링: `../backend-infra/monitoring`

배포 대상 EC2에는 Git 저장소를 clone하지 않습니다. GitHub hosted runner가 이미지를 빌드/게시하고, EC2는 GHCR 이미지와 배포 스크립트만 사용합니다.

## 데이터 사용

공공데이터 수집과 정규화는 `backend`가 담당하며, FastAPI는 Spring DB의 정규화 테이블을 직접 조회해 스코어링에 사용합니다.

대표 데이터:

- 한국장애인고용공단 장애인 구인 실시간 현황
- 한국장애인고용공단 장애인 표준사업장 실시간 조회
- 한국장애인고용공단 근로지원인 수행기관 정보
- 전국교통약자이동지원센터 표준데이터
- 전국 버스정류장, 횡단보도, 신호등 데이터
- 서울 지하철 출입구 리프트, 도보 네트워크, 휠체어 경사로 데이터
- 한국철도공사/KRIC 교통약자 편의시설 데이터

상세 데이터 출처와 동기화 방식은 `backend/README.md`를 기준으로 합니다.

## 사업 아이템 차별점

- 단순 채용 공고 추천이 아니라, 장애인 구직자의 **실제 출근 가능성**과 **근무 지속 가능성**을 함께 계산합니다.
- 이력서 PDF를 프로필로 자동 변환해 사용자의 초기 입력 부담을 줄입니다.
- AI 추천을 켜고 끌 수 있어, 최신 공고 조회와 AI 분석 흐름을 명확히 분리합니다.
- 점수 산정은 설명 가능한 룰 기반 로직으로 처리하고, LLM은 구조화와 자연어 설명에 제한적으로 사용합니다. 
