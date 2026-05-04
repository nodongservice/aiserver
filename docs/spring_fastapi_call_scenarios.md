# Spring-FastAPI 호출 시나리오

## 목적

Spring Backend가 화면/기능별로 FastAPI scoring v2 API를 언제 호출하는지 정의한다.

전제 문서:

- `docs/fastapi_internal_api_contract.md`
- `docs/spring_analysis_storage_cache_policy.md`
- `.agents/specification.md`

## 사용 API

Spring이 사용하는 FastAPI 내부 API:

- `POST /ai/v1/score/quick`
- `POST /ai/v1/score/map`
- `POST /ai/v1/explain/recommendation`

역할:

- `/ai/v1/score/quick`: 기능 2, 최신 공고 + 직무 적합도 계산
- `/ai/v1/score/map`: 기능 3, 6항목 동일비중 종합 점수 계산
- `/ai/v1/explain/recommendation`: 계산된 점수/근거를 추천 설명으로 변환

## 기본 호출 원칙

- 프론트엔드는 FastAPI를 직접 호출하지 않는다.
- Spring은 선택된 프로필 1개만 FastAPI에 전달한다.
- 화면 필터는 기능정의서 기준 프론트에서 적용한다.
- `aiEnabled=false`인 경우 FastAPI를 호출하지 않는다.
- FastAPI는 `pd_kepad_recruitment` 및 접근성 `pd_*` 테이블을 직접 조회한다.

## 기능 2. 퀵 맞춤 일자리 추천

### AI 직무 적합도 ON

1. 프론트가 프로필 1개를 선택한다.
2. Spring이 선택 프로필을 조회한다.
3. Spring이 캐시를 확인한다.
4. 캐시 miss면 `POST /ai/v1/score/quick`을 호출한다.
5. FastAPI는 `pd_kepad_recruitment`를 최신순 조회하고 직무 적합도를 계산한다.
6. Spring은 결과를 저장/캐시한 뒤 프론트에 반환한다.
7. 프론트는 화면 필터를 적용한다.

권장 프론트 노출 필드:

- `job`
- `job_fit_score`
- `reasons`
- `risk_factors`

### AI 직무 적합도 OFF

1. Spring이 DB 공고를 최신순 반환한다.
2. FastAPI는 호출하지 않는다.
3. 프론트가 화면 필터를 적용한다.

## 기능 3. 지역 접근성 지도 추천

### AI 스코어링 ON

1. 프론트가 프로필 1개를 선택한다.
2. Spring이 선택 프로필을 조회한다.
3. Spring이 캐시를 확인한다.
4. 캐시 miss면 `POST /ai/v1/score/map`을 호출한다.
5. FastAPI는 공고/공공데이터를 직접 조회한다.
6. FastAPI는 6개 항목을 동일 비중으로 계산하고 총점 내림차순으로 반환한다.
7. Spring은 결과를 저장/캐시한 뒤 프론트에 반환한다.
8. 프론트는 화면 필터를 적용한다.

권장 프론트 노출 필드:

- `job`
- `score_detail`
- `total_score`
- `reasons`
- `risk_factors`
- `evidence_items`

### AI 스코어링 OFF

1. Spring이 DB 공고를 반환한다.
2. FastAPI는 호출하지 않는다.
3. 프론트가 화면 필터를 적용한다.

## 설명 API 호출

`POST /ai/v1/explain/recommendation`은 점수 계산 후 선택적으로 호출한다.

권장 호출 시점:

- 공고 상세 화면
- 상담기관용 요약
- 사용자가 추천 사유 상세 보기를 요청한 경우

목록/지도 초기 화면에서는 기본적으로 호출하지 않아도 된다.
