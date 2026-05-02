# Spring-FastAPI 호출 시나리오

## 목적

이 문서는 Spring Backend가 화면/기능별로 FastAPI API를 언제, 어떤 순서로 호출해야 하는지 정의한다.

이 문서는 다음 문서를 전제로 한다.

- `docs/fastapi_internal_api_contract.md`
- `docs/spring_analysis_storage_cache_policy.md`
- `docs/frontend_response_composition_examples.md`

핵심 원칙:

- 프론트엔드는 FastAPI를 직접 호출하지 않는다.
- Spring이 화면 목적에 맞게 FastAPI 호출 여부를 결정한다.
- 추천 목록에서는 가능한 한 `analyze-batch`만 사용한다.
- 상세 설명이 더 필요할 때만 `explanations/accessibility`를 추가 호출한다.

---

## 1. 사용 API

Spring이 사용하는 FastAPI 내부 API는 현재 기준으로 다음 4개다.

- `POST /api/v1/tags/normalize`
- `POST /api/v1/accessibility/analyze-batch`
- `POST /api/v1/explanations/accessibility`
- `GET /api/v1/gis/nearby-features`

각 API의 역할은 다음과 같다.

- `tags/normalize`: 사용자 입력 라벨을 분석용 표준 태그로 변환
- `analyze-batch`: 사용자 조건과 공고 후보를 분석해 점수, 등급, 근거, 요약 반환
- `explanations/accessibility`: 분석 결과를 상세 설명 문장으로 변환
- `nearby-features`: 디버깅 또는 운영 검증용 근거 조회

---

## 2. 기본 호출 원칙

### 2.1 `tags/normalize`는 언제 호출하는가

다음 중 하나에 해당하면 Spring은 `tags/normalize`를 호출하는 것을 권장한다.

- 사용자 온보딩/프로필 저장 시
- 사용자 조건 수정 시
- 아직 정규화 태그가 저장되어 있지 않을 때

이미 정규화된 태그가 Spring DB에 신뢰 가능한 형태로 저장되어 있다면, 매 요청마다 다시 호출할 필요는 없다.

### 2.2 `analyze-batch`는 언제 호출하는가

다음 중 하나에 해당하면 Spring은 `analyze-batch`를 호출한다.

- 공고 목록 화면에서 여러 공고 점수가 필요할 때
- 공고 상세 화면에서 특정 공고의 최신 접근성 분석이 필요할 때
- 캐시 miss 또는 재분석 조건 충족 시

단건 분석이 필요해도 현재 운영 API는 `analyze-batch` 하나로 통일한다.

### 2.3 `explanations/accessibility`는 언제 호출하는가

다음 중 하나에 해당할 때만 별도 호출하는 것을 권장한다.

- 공고 상세 화면에서 더 긴 설명이 필요할 때
- 상담기관용 상세 설명이 필요할 때
- `summary`만으로는 부족한 화면일 때

추천 목록이나 지도 마커 화면에서는 기본적으로 호출하지 않는다.

---

## 3. 화면별 권장 시나리오

### 3.1 사용자 온보딩/프로필 저장

목적:

- 사용자가 선택한 한글 라벨을 분석용 태그로 정규화

권장 흐름:

1. Spring이 사용자 입력 라벨 수신
2. Spring이 `POST /api/v1/tags/normalize` 호출
3. 정규화 결과를 Spring DB에 저장
4. 이후 분석 요청에서는 저장된 정규화 태그 재사용

권장 저장값:

- `disability_types`
- `required_supports`
- `work_environment_preferences`
- `transport_preferences`
- `unknown_labels`

주의:

- 원본 한글 라벨도 Spring이 별도 보관할 수 있다.
- FastAPI 분석 요청에는 가능한 한 정규화된 태그만 전달한다.

### 3.2 공고 목록/지도 화면

목적:

- 여러 공고를 한 번에 점수화해 정렬, 필터, 마커 색상 표시 등에 사용

권장 흐름:

1. Spring이 사용자 정규화 태그 조회
2. Spring이 후보 공고 목록 조회
3. 캐시 hit 여부 확인
4. 필요한 공고만 묶어 `POST /api/v1/accessibility/analyze-batch` 호출
5. Spring이 결과 저장 또는 캐시
6. 프론트에는 점수, 등급, 요약, 핵심 요인만 반환

이 화면에서 기본 사용 권장 필드:

- `accessibility_score`
- `accessibility_grade`
- `summary`
- `positive_factors`
- `risk_factors`

이 화면에서 기본적으로 하지 않는 것:

- `POST /api/v1/explanations/accessibility` 별도 호출
- 긴 상세 설명 생성

이유:

- 목록 화면은 응답 속도가 우선이다.
- `analyze-batch`의 `summary`만으로도 1차 노출이 가능하다.

### 3.3 공고 상세 화면

목적:

- 특정 공고에 대해 점수 근거와 상세 설명을 더 풍부하게 제공

권장 흐름:

1. Spring이 해당 공고의 분석 캐시 조회
2. 캐시가 없거나 재분석 조건이면 `POST /api/v1/accessibility/analyze-batch` 호출
3. 상세 설명 캐시 조회
4. 상세 설명이 없거나 설명 재생성 조건이면 `POST /api/v1/explanations/accessibility` 호출
5. 점수 결과와 설명 결과를 합쳐 프론트에 반환

상세 화면에서 권장 반환 필드:

- `accessibility_score`
- `accessibility_grade`
- `score_detail`
- `positive_factors`
- `risk_factors`
- `evidence_items`
- `summary`
- `short_summary`
- `detail_explanation`
- `check_points`

설명 API를 생략해도 되는 경우:

- MVP 초기 단계
- 응답 속도가 중요한 경우
- `summary + 요인 목록 + evidence_items`만으로 충분한 경우

### 3.4 상담기관/운영자 검토 화면

목적:

- 왜 이런 점수가 나왔는지 근거를 검토하고 예외를 파악

권장 흐름:

1. Spring이 저장된 분석 결과 조회
2. 필요 시 `evidence_items` 기반으로 `GET /api/v1/gis/nearby-features` 호출
3. 운영자 화면에는 점수와 함께 근거 목록 노출

권장 사용 필드:

- `score_detail`
- `positive_factors`
- `risk_factors`
- `evidence_items`

이 화면은 디버깅/운영 검증용이므로 일반 사용자 화면과 분리하는 것을 권장한다.

---

## 4. 설명 API 호출 기준

Spring은 모든 분석 결과에 대해 설명 API를 즉시 호출할 필요가 없다.

### 4.1 즉시 호출 권장 경우

- 공고 상세 화면 최초 진입 시
- 상담기관용 리포트 생성 시
- 사용자가 설명 펼치기 기능을 명시적으로 요청한 경우

### 4.2 지연 호출 권장 경우

- 목록 화면에서 상세 보기 진입 전
- 분석 결과는 이미 있으나 긴 설명은 아직 필요 없는 경우

### 4.3 호출하지 않아도 되는 경우

- 지도 마커 점수 표시만 필요한 경우
- 추천 목록 요약 문구만 필요한 경우

현재 구현 기준에서는 `used_llm=false`일 수 있으므로, 설명 API는 여전히 deterministic fallback 문서 생성기로 봐도 된다.

---

## 5. 권장 응답 조합

### 5.1 목록 응답 조합

Spring이 프론트에 넘길 때 최소 권장 조합:

- 공고 기본 정보
- `accessibility_score`
- `accessibility_grade`
- `summary`

선택 추가:

- `positive_factors` 상위 1~2개
- `risk_factors` 상위 1~2개

### 5.2 상세 응답 조합

Spring이 프론트에 넘길 때 권장 조합:

- 공고 기본 정보
- `accessibility_score`
- `accessibility_grade`
- `score_detail`
- `positive_factors`
- `risk_factors`
- `evidence_items`
- `summary`
- `short_summary`
- `detail_explanation`
- `check_points`

---

## 6. 실패 시 fallback 시나리오

### 6.1 `tags/normalize` 실패

권장 처리:

- 프로필 저장 실패로 처리하거나
- 최소한 `unknown` 중심 fallback 태그로 저장 후 재시도 유도

권장하지 않는 처리:

- 정규화 실패 라벨을 임의 매핑

### 6.2 `analyze-batch` 실패

권장 처리:

- 캐시가 있으면 마지막 성공 결과 사용
- 캐시가 없으면 분석 미완료 상태 반환

프론트 권장 문구:

- `현재 접근성 분석 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.`

### 6.3 `explanations/accessibility` 실패

권장 처리:

- `summary`를 기본 설명으로 사용
- `detail_explanation` 없이도 상세 화면 렌더링 가능하게 구성

프론트 권장 fallback:

- `summary`
- `positive_factors`
- `risk_factors`
- `evidence_items`

---

## 7. 운영 결론

현재 MVP 기준 권장 흐름은 아래와 같다.

1. 사용자 입력은 먼저 `tags/normalize`로 정규화한다.
2. 공고 목록과 상세 점수 계산은 모두 `analyze-batch`로 통일한다.
3. 목록 화면은 `summary` 중심으로 빠르게 보여준다.
4. 상세 화면에서만 필요 시 `explanations/accessibility`를 추가 호출한다.
5. 디버깅 또는 운영 검증이 필요할 때만 `nearby-features`를 사용한다.
