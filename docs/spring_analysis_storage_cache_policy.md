# Spring 추천 결과 저장/캐시 정책

## 목적

Spring Backend가 FastAPI scoring v2 결과를 저장, 캐시, 재사용할 때 따를 운영 기준을 정의한다.

전제 문서:

- `docs/fastapi_internal_api_contract.md`
- `.agents/specification.md`
- `../backend/README.md`

## 핵심 원칙

- FastAPI는 점수 계산과 설명 문장 생성을 담당한다.
- Spring은 인증, 프로필 관리, API 게이트웨이, 결과 저장/캐시를 담당한다.
- FastAPI는 `pd_*` 정규화 테이블을 직접 조회한다.
- 점수는 룰 기반이며 LLM은 점수를 결정하지 않는다.
- 데이터가 없으면 확정하지 않고 `추가 확인 필요`로 저장한다.

## 저장 대상

### Quick 추천

`POST /ai/v1/score/quick` 결과에서 저장 또는 캐시할 수 있는 값:

- `profile_id`
- `user_id`
- `job.job_post_id`
- `job.company_name`
- `job.job_title`
- `job.source_table`
- `job.source_id`
- `job_fit_score`
- `reasons`
- `risk_factors`
- `evidence_items`
- `scoring_version`
- `scored_at`
- `expires_at`

### Map 추천

`POST /ai/v1/score/map` 결과에서 저장 또는 캐시할 수 있는 값:

- `profile_id`
- `user_id`
- `job.job_post_id`
- `job.company_name`
- `job.job_title`
- `score_detail.job_fit_score`
- `score_detail.work_condition_score`
- `score_detail.disability_support_score`
- `score_detail.work_environment_score`
- `score_detail.company_stability_score`
- `score_detail.accessibility_score`
- `total_score`
- `reasons`
- `risk_factors`
- `evidence_items`
- `scoring_version`
- `scored_at`
- `expires_at`

### 설명 결과

`POST /ai/v1/explain/recommendation` 결과에서 저장할 수 있는 값:

- `short_summary`
- `recommendation_reasons`
- `caution_points`
- `checklist`
- `used_llm`
- `explanation_version`
- `explained_at`

## 캐시 키 기준

FastAPI가 공고를 직접 조회하므로 캐시 키는 “프로필 조건 + 기능 + 페이지 조건 + 정책 버전”을 포함한다.

권장 quick 캐시 키:

```text
quick-score:v2:profile:{profile_id}:profile_hash:{profile_hash}:limit:{limit}:offset:{offset}
```

권장 map 캐시 키:

```text
map-score:v2:profile:{profile_id}:profile_hash:{profile_hash}:limit:{limit}:offset:{offset}
```

권장 설명 캐시 키:

```text
recommendation-explain:v1:profile:{profile_id}:job:{job_post_id}:score_hash:{score_hash}
```

## 재계산 조건

다음 중 하나라도 바뀌면 Spring은 캐시를 재사용하지 않는 것을 권장한다.

- 선택 프로필 변경
- 프로필의 직무, 기술, 학력, 경력, 장애 유형, 필요 지원사항 변경
- `pd_kepad_recruitment` 동기화 완료
- 표준사업장 또는 접근성 `pd_*` 데이터 동기화 완료
- scoring 버전 변경
- 설명 정책 또는 explanation 버전 변경

## TTL 권장값

- quick score: 30분~24시간
- map score: 30분~24시간
- recommendation explanation: 24시간

공공데이터 동기화 직후에는 TTL과 별개로 관련 캐시를 무효화할 수 있다.

## 저장 시 문구 취급

Spring은 FastAPI가 반환한 문구를 확정적으로 바꾸지 않는다.

보존 권장 표현:

- `현재 공공데이터 기준`
- `추가 확인이 필요합니다`
- `지원 전 확인하세요`

금지:

- `추가 확인 필요` 제거
- 데이터가 없는 항목을 `문제 없음`으로 치환
- 접근 가능 여부를 확정 단정

## 장애 처리

- HTTP 200: 결과 저장 또는 캐시 가능
- HTTP 422: Spring 요청 DTO 구성 오류로 보고 저장하지 않음
- HTTP 500 또는 timeout: 기존 캐시가 있으면 stale 결과 사용 가능
- 기존 캐시가 없으면 프론트에는 AI 점수 미제공 상태를 반환

권장 안내:

```text
현재 AI 추천 점수를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.
```
