# Spring 분석 결과 저장/캐시 정책

## 목적

이 문서는 Spring Backend가 FastAPI 접근성 분석 결과를 저장, 캐시, 재사용할 때 따를 운영 기준을 정의한다.

이 문서는 다음 문서의 후속 정책이다.

- `docs/fastapi_internal_api_contract.md`
- `.agents/spring_fastapi_contract_agent.md`

핵심 원칙:

- FastAPI는 분석만 수행한다.
- 분석 결과의 저장과 캐시는 Spring이 담당한다.
- README 기준 데이터 밖의 정보는 확정 저장 문구로 확대 해석하지 않는다.
- 점수 정책 버전과 설명 버전은 반드시 함께 관리한다.

---

## 1. 저장 대상

Spring은 FastAPI `POST /api/v1/accessibility/analyze-batch` 응답에서 다음 값을 저장 대상으로 본다.

### 1.1 저장 권장 필드

- `user_id`
- `job_post_id`
- `company_id`
- `accessibility_score`
- `accessibility_grade`
- `score_detail.transport_score`
- `score_detail.station_access_score`
- `score_detail.crosswalk_score`
- `score_detail.facility_score`
- `score_detail.work_environment_score`
- `score_detail.risk_penalty`
- `positive_factors`
- `risk_factors`
- `evidence_items`
- `summary`
- `scoring_version`
- `analysis_requested_at`
- `analysis_completed_at`

### 1.2 현재 고정 메타데이터

- `scoring_version = "v1.0"`

설명 API를 별도로 호출해 저장하는 경우에는 아래도 함께 저장한다.

- `explanation_version`
- `short_summary`
- `detail_explanation`
- `check_points`
- `used_llm`

---

## 2. 저장하지 않아도 되는 값

다음 값은 Spring이 이미 원본 공고/사용자 정보에서 복원 가능하므로, 분석 결과 테이블에 중복 저장하지 않아도 된다.

- `company_name`
- `job_title`
- `work_address`
- 사용자 프로필 원본 라벨
- 정규화 이전 한글 태그

단, 이력 보존이나 디버깅 목적이 있으면 JSON snapshot 컬럼으로 보조 저장할 수 있다.

---

## 3. 권장 저장 구조

### 3.1 단일 테이블 저장

MVP에서는 Spring이 단일 분석 결과 테이블에 저장해도 충분하다.

권장 예시:

- `id`
- `user_id`
- `job_post_id`
- `company_id`
- `accessibility_score`
- `accessibility_grade`
- `score_detail_json`
- `positive_factors_json`
- `risk_factors_json`
- `evidence_items_json`
- `summary`
- `scoring_version`
- `explanation_version`
- `used_llm`
- `analyzed_at`
- `expires_at`

### 3.2 분석과 설명 분리 저장

설명 재생성을 독립적으로 하고 싶다면 분석 결과와 설명 결과를 분리 저장할 수 있다.

권장 분리 기준:

- 분석 결과: 점수, 등급, 세부점수, 근거, 요약
- 설명 결과: 설명 문장, check_points, used_llm, explanation_version

이 경우 설명은 `job_post_id + user_id + scoring_version + explanation_version` 조합으로 관리하는 것을 권장한다.

---

## 4. 캐시 키 기준

Spring 캐시는 분석 요청의 의미가 달라질 때 반드시 무효화될 수 있어야 한다.

### 4.1 접근성 분석 캐시 키 권장값

최소 포함 항목:

- `user_id`
- `job_post_id`
- `scoring_version`

추가 포함 권장 항목:

- 정규화된 `disability_types`
- 정규화된 `required_supports`
- 정규화된 `work_environment_preferences`
- `transport_preferences`
- `work_environment_tags`
- `support_tags`
- `is_standard_workplace`
- `is_disability_friendly_post`

### 4.2 권장 캐시 키 형태

예시:

```text
accessibility:v1.0:user:1:job:101:profile_hash:abc123:job_hash:def456
```

권장 이유:

- 사용자 조건 변경과 공고 태그 변경을 분리 추적 가능
- `scoring_version` 변경 시 전체 무효화 가능
- 같은 사용자와 같은 공고라도 조건이 바뀌면 재분석 가능

### 4.3 설명 캐시 키 형태

예시:

```text
explanation:v1-rule-fallback:user:1:job:101:scoring:v1.0:analysis_hash:abc123
```

설명은 분석 결과에 종속되므로, 설명 캐시는 반드시 `scoring_version` 또는 분석 결과 hash를 포함해야 한다.

---

## 5. 재분석이 필요한 조건

다음 중 하나라도 바뀌면 Spring은 기존 캐시를 재사용하지 않고 FastAPI를 다시 호출하는 것을 권장한다.

### 5.1 사용자 조건 변경

- `disability_types` 변경
- `required_supports` 변경
- `work_environment_preferences` 변경
- `transport_preferences` 변경
- `commute_limit_minutes` 변경

### 5.2 공고 정보 변경

- `work_lat`, `work_lng` 변경
- `is_standard_workplace` 변경
- `is_disability_friendly_post` 변경
- `work_environment_tags` 변경
- `support_tags` 변경

### 5.3 정책/데이터 변경

- `scoring_version` 변경
- `explanation_version` 변경
- 관련 `public_data_record` 또는 `public_accessibility_gis_feature` 갱신
- 근거 데이터 수집 기준일 변경이 중요한 경우

---

## 6. TTL 권장값

운영 초반에는 보수적으로 짧은 TTL을 권장한다.

### 6.1 분석 결과 캐시

- 기본 권장: `24시간`
- 공공데이터 동기화 직후 일괄 무효화 가능

### 6.2 설명 결과 캐시

- 기본 권장: `24시간`
- `explanation_version` 또는 설명 정책 변경 시 무효화

주의:

- 공고 데이터가 자주 바뀌는 경우 `job_hash` 기반 캐시 무효화를 우선한다.
- 단순 TTL만으로 운영하지 말고 버전 키와 hash 키를 함께 사용한다.

---

## 7. 저장 시 문구 취급 원칙

Spring은 FastAPI가 반환한 `positive_factors`, `risk_factors`, `summary`, `check_points`를 임의로 긍정적 표현으로 바꾸지 않는다.

특히 다음 문구는 보존하는 것을 권장한다.

- `현재 공공데이터 기준`
- `확인 필요`
- `지원 전 확인을 권장합니다`

금지 예시:

- `확인 필요`를 제거하고 확정 문구로 저장
- `위험 요인 없음`으로 일괄 치환
- README 기준에 없는 시설 정보를 프론트 문구에서 단정적으로 보강

---

## 8. 부분 실패 처리 정책

FastAPI `analyze-batch`는 배치 단위 요청이지만, Spring은 운영 정책상 부분 실패 대응을 준비하는 것이 좋다.

권장 정책:

- HTTP 200 + 정상 응답이면 전체 저장
- HTTP 422면 요청 DTO 구성 버그로 보고 저장하지 않음
- HTTP 500 또는 timeout이면 기존 캐시가 있으면 stale 결과 사용 가능
- 기존 캐시가 없으면 프론트에는 분석 불가 상태와 안전한 안내 문구 반환

권장 사용자 안내 방향:

- `현재 접근성 분석 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.`
- 확정 점수 대신 분석 미완료 상태 반환

---

## 9. Spring 팀 구현 체크리스트

### 9.1 저장 전

- `tags/normalize` 결과를 분석 입력에 사용했는지 확인
- `analyze-batch` 요청에 정규화된 태그만 전달
- `scoring_version = v1.0` 메타데이터 포함

### 9.2 저장 시

- `results[]`를 공고별 row로 분해 저장
- `score_detail`, `positive_factors`, `risk_factors`, `evidence_items`는 JSON 저장 가능
- `summary`는 별도 문자열 컬럼 저장 권장

### 9.3 재사용 시

- 캐시 hit여도 `scoring_version` 불일치 시 폐기
- 공고/사용자 hash 불일치 시 재분석
- 설명만 다시 생성할 경우 분석 결과는 재사용 가능

---

## 10. 현재 권장 운영 결론

현재 단계에서는 다음 기준을 권장한다.

1. Spring은 FastAPI 분석 결과를 공고별로 저장한다.
2. 캐시 키에는 최소 `user_id`, `job_post_id`, `scoring_version=v1.0`을 포함한다.
3. 가능하면 사용자 조건 hash와 공고 조건 hash를 함께 사용한다.
4. `positive_factors`, `risk_factors`, `summary` 문구는 임의 수정 없이 저장한다.
5. 설명 API를 별도 사용하면 `explanation_version`도 저장/캐시 키에 포함한다.
