# 분석 결과 저장/캐싱 정책 가이드

## 1. 목적

이 문서는 BridgeWork에서 Spring Backend가 FastAPI AI/GIS Service의 분석 결과와 설명 결과를 저장/캐싱할 때의 기준을 정의한다.

FastAPI는 접근성 점수 계산과 설명 생성을 담당한다.  
Spring은 FastAPI 호출 결과를 저장하거나 캐싱하고, 최종 응답을 Next.js Frontend에 제공한다.

---

## 2. 기본 원칙

### 2.1 FastAPI는 분석 결과를 직접 저장하지 않는다

현재 MVP 구조에서 FastAPI는 분석 서버 역할만 수행한다.

FastAPI는 다음 작업을 수행한다.

- 사용자 조건과 공고 후보를 입력받는다.
- 공고별 접근성 점수를 계산한다.
- 긍정 요인과 위험 요인을 생성한다.
- 공공데이터 근거를 evidence_items로 반환한다.
- 분석 결과 기반 설명을 생성한다.

FastAPI는 다음 작업을 직접 담당하지 않는다.

- 사용자 프로필 저장
- 공고 데이터 저장
- 공공데이터 원본 동기화
- 추천 결과 장기 저장
- 프론트엔드 최종 응답 제공

위 작업은 Spring Backend가 담당한다.

### 2.2 점수 결과와 설명 결과는 분리해서 저장한다

접근성 분석 결과와 설명 생성 결과는 서로 다른 성격의 데이터다.

분석 결과는 룰 기반 점수 계산 결과다.  
설명 결과는 분석 결과를 사용자에게 보여주기 위한 문장 생성 결과다.

따라서 Spring은 두 결과를 분리해서 저장하거나 캐싱하는 것을 권장한다.

분리 이유는 다음과 같다.

- 점수 계산 로직과 설명 생성 로직의 변경 주기가 다르다.
- LLM 도입 후에도 점수 결과는 안정적으로 유지되어야 한다.
- 설명만 재생성할 수 있어야 한다.
- 설명 API 장애가 추천 점수 제공에 영향을 주면 안 된다.
- 비용과 timeout 정책을 분리할 수 있다.

---

## 3. 분석 결과 저장 권장 필드

Spring은 `/api/v1/accessibility/analyze-batch` 응답 결과를 공고별로 저장할 수 있다.

권장 저장 필드는 다음과 같다.

| 필드 | 설명 |
|---|---|
| user_id | 분석 대상 사용자 ID |
| job_post_id | 분석 대상 공고 ID |
| company_id | 분석 대상 기업 ID |
| accessibility_score | 최종 접근성 점수 |
| accessibility_grade | GOOD, CAUTION, RISK |
| score_detail | 세부 점수 JSON |
| positive_factors | 긍정 요인 JSON |
| risk_factors | 위험 요인 JSON |
| evidence_items | 근거 데이터 JSON |
| summary | 사용자 노출용 한 줄 요약 |
| user_condition_hash | 사용자 접근성 조건 해시 |
| job_condition_hash | 공고 접근성 조건 해시 |
| public_data_snapshot_key | 공공데이터 동기화 기준 키 |
| analyzed_at | 분석 수행 시각 |
| expires_at | 캐시 만료 시각 |

---

## 4. 설명 결과 저장 권장 필드

Spring은 `/api/v1/explanations/accessibility` 응답 결과를 별도로 저장할 수 있다.

권장 저장 필드는 다음과 같다.

| 필드 | 설명 |
|---|---|
| user_id | 설명 대상 사용자 ID |
| job_post_id | 설명 대상 공고 ID |
| accessibility_score | 설명 생성 시점의 접근성 점수 |
| accessibility_grade | 설명 생성 시점의 접근성 등급 |
| explanation_version | 설명 생성 로직 버전 |
| short_summary | 공고 카드용 짧은 설명 |
| detail_explanation | 상세 화면용 설명 |
| check_points | 사용자 확인 권장 사항 JSON |
| used_llm | LLM 사용 여부 |
| generated_at | 설명 생성 시각 |
| expires_at | 설명 캐시 만료 시각 |

---

## 5. 분석 결과 캐시 키

분석 결과 캐시는 사용자 조건과 공고 조건이 같을 때 재사용할 수 있다.

권장 캐시 키 구성은 다음과 같다.

| 구성 요소 | 설명 |
|---|---|
| user_id | 사용자 ID |
| job_post_id | 공고 ID |
| user_condition_hash | 사용자 접근성 조건 해시 |
| job_condition_hash | 공고 접근성 조건 해시 |
| public_data_snapshot_key | 공공데이터 기준 시점 |

예시 캐시 키 개념:

`analysis:{user_id}:{job_post_id}:{user_condition_hash}:{job_condition_hash}:{public_data_snapshot_key}`

---

## 6. 사용자 조건 해시 기준

user_condition_hash는 접근성 분석에 영향을 주는 사용자 조건을 기준으로 만든다.

포함 권장 필드:

- home_lat
- home_lng
- commute_limit_minutes
- disability_types
- required_supports
- work_environment_preferences
- transport_preferences

포함하지 않아도 되는 필드:

- 사용자 이름
- 이메일
- 로그인 제공자
- 프로필 이미지
- 이력서 파일명
- 분석과 무관한 계정 정보

사용자 조건이 변경되면 기존 분석 캐시는 무효화한다.

---

## 7. 공고 조건 해시 기준

job_condition_hash는 접근성 분석에 영향을 주는 공고 조건을 기준으로 만든다.

포함 권장 필드:

- job_post_id
- company_id
- work_lat
- work_lng
- work_address
- is_standard_workplace
- is_disability_friendly_post
- work_environment_tags
- support_tags

포함하지 않아도 되는 필드:

- 조회수
- 북마크 수
- 단순 노출용 이미지
- 분석과 무관한 마케팅 문구

공고의 근무지, 업무환경, 지원 제도 정보가 변경되면 기존 분석 캐시는 무효화한다.

---

## 8. 공공데이터 기준 키

public_data_snapshot_key는 분석에 사용한 공공데이터 기준 시점을 나타낸다.

Spring이 공공데이터 동기화를 담당하므로, Spring은 동기화 완료 시점 또는 소스별 최신 동기화 로그를 기준으로 snapshot key를 만들 수 있다.

예시 구성:

- 전체 공공데이터 최신 동기화 시각
- SourceType별 최신 동기화 시각 조합
- public_data_sync_log의 batch_id
- 공공데이터 버전 문자열

예시:

`public-data:2026-04-27T18:00:00`

또는:

`KEPAD_STANDARD_WORKPLACE:2026-04-27|NATIONWIDE_BUS_STOP:2026-04-26|NATIONWIDE_CROSSWALK:2026-04-26`

공공데이터가 변경되면 위치/접근성 근거가 달라질 수 있으므로 관련 분석 캐시를 무효화하는 것을 권장한다.

---

## 9. 설명 결과 캐시 키

설명 결과는 분석 결과와 별도로 캐싱한다.

권장 캐시 키 구성은 다음과 같다.

| 구성 요소 | 설명 |
|---|---|
| user_id | 사용자 ID |
| job_post_id | 공고 ID |
| accessibility_score | 설명 생성 당시 점수 |
| accessibility_grade | 설명 생성 당시 등급 |
| explanation_version | 설명 생성 로직 버전 |

예시 캐시 키 개념:

`explanation:{user_id}:{job_post_id}:{accessibility_score}:{accessibility_grade}:{explanation_version}`

설명은 점수와 등급이 같더라도 positive_factors, risk_factors, evidence_items가 바뀌면 달라질 수 있다.  
운영 단계에서는 factors_hash 또는 evidence_hash를 추가하는 것도 권장한다.

---

## 10. 캐시 무효화 조건

### 10.1 분석 결과 캐시 무효화 조건

다음 상황에서는 분석 결과 캐시를 무효화한다.

- 사용자의 장애 유형이 변경된 경우
- 사용자의 필요 지원 조건이 변경된 경우
- 사용자의 통근 기준 위치가 변경된 경우
- 사용자의 최대 통근 시간이 변경된 경우
- 사용자의 이동수단 선호가 변경된 경우
- 사용자의 업무환경 선호/기피 조건이 변경된 경우
- 공고의 근무지 좌표가 변경된 경우
- 공고의 업무환경 태그가 변경된 경우
- 공고의 지원 제도 태그가 변경된 경우
- 공고의 장애인 우대/전형 여부가 변경된 경우
- 표준사업장 여부 매칭 결과가 변경된 경우
- 공공데이터 동기화 결과가 변경된 경우
- FastAPI 점수 계산 로직이 변경된 경우

### 10.2 설명 결과 캐시 무효화 조건

다음 상황에서는 설명 결과 캐시를 무효화한다.

- accessibility_score가 변경된 경우
- accessibility_grade가 변경된 경우
- positive_factors가 변경된 경우
- risk_factors가 변경된 경우
- evidence_items가 변경된 경우
- explanation_version이 변경된 경우
- LLM 프롬프트 버전이 변경된 경우
- 설명 표현 정책이 변경된 경우

---

## 11. TTL 권장 기준

현재 MVP 단계에서는 복잡한 실시간 무효화보다 짧은 TTL과 조건 기반 무효화를 함께 사용하는 것을 권장한다.

권장 TTL:

| 캐시 대상 | 권장 TTL |
|---|---|
| 태그 정규화 결과 | 사용자 프로필 변경 전까지 |
| 분석 결과 | 1일 ~ 7일 |
| 설명 결과 | 1일 ~ 7일 |
| 공공데이터 조회 결과 | 다음 동기화 전까지 |

운영 초기에는 1일 TTL을 권장한다.  
데이터 안정성이 확인되면 3일 또는 7일로 늘릴 수 있다.

---

## 12. 공공데이터 동기화 후 재분석 기준

Spring이 공공데이터 동기화를 완료한 뒤에는 다음 기준으로 재분석 대상을 판단한다.

### 12.1 즉시 재분석이 필요한 경우

- 공고 근처 접근성 시설 데이터가 변경된 경우
- 표준사업장 매칭 결과가 변경된 경우
- 버스정류장/횡단보도/엘리베이터/리프트 데이터가 변경된 경우
- 사용자가 최근 조회한 추천 결과에 영향을 줄 수 있는 경우

### 12.2 즉시 재분석하지 않아도 되는 경우

- 오래된 추천 결과
- 사용자가 조회하지 않은 공고
- 마감된 공고
- 접근성 점수에 직접 영향이 없는 공공데이터 변경

### 12.3 권장 방식

MVP에서는 전체 재분석보다 다음 방식이 적합하다.

1. 공공데이터 동기화 완료
2. 변경된 SourceType 기록
3. 변경된 지역 또는 좌표 범위 파악
4. 해당 범위에 포함되는 공고 캐시만 무효화
5. 사용자가 다시 조회할 때 lazy re-analysis 수행

---

## 13. 실패 시 fallback 기준

### 13.1 태그 정규화 실패

태그 정규화 API 호출 실패 시 Spring은 다음 중 하나로 처리한다.

- 사용자에게 다시 시도 요청
- 원본 라벨 저장 후 나중에 재정규화
- 기본 태그 unknown 사용

단, 잘못된 태그로 분석을 강행하는 것은 권장하지 않는다.

### 13.2 접근성 분석 실패

analyze-batch API 호출 실패 시 Spring은 다음 중 하나로 처리한다.

- 해당 공고를 분석 불가 상태로 표시
- 기존 캐시가 있으면 기존 분석 결과 사용
- “접근성 정보 확인 필요” 상태로 표시
- 추천 목록 자체는 제공하되 접근성 점수는 비워둔다

프론트엔드에 FastAPI 원본 에러를 그대로 노출하지 않는다.

### 13.3 설명 생성 실패

설명 API 호출 실패 시 Spring은 다음 fallback을 사용할 수 있다.

- analyze-batch의 summary 사용
- positive_factors와 risk_factors를 그대로 표시
- “상세 설명은 잠시 후 다시 확인해 주세요.” 표시

설명 생성 실패가 접근성 점수 제공 실패로 이어지면 안 된다.

---

## 14. LLM 도입 후 캐싱 기준

향후 LLM을 설명 API에 연결하면 설명 결과 캐싱이 더 중요해진다.

LLM 설명 결과 캐싱 기준에는 다음 값을 포함하는 것을 권장한다.

- user_id
- job_post_id
- accessibility_score
- accessibility_grade
- positive_factors hash
- risk_factors hash
- evidence_items hash
- explanation_version
- prompt_version
- model_name

LLM 응답은 비용과 지연 시간이 크기 때문에 동일 조건에서는 재사용하는 것이 좋다.

단, LLM이 생성한 설명이 오래된 근거를 바탕으로 하지 않도록 evidence_items 변경 시 반드시 무효화한다.

---

## 15. FastAPI 쪽 유지 원칙

FastAPI는 캐시 저장소를 직접 관리하지 않는다.

다만 FastAPI 응답은 Spring이 저장하기 쉬운 구조를 유지해야 한다.

FastAPI 응답에서 유지해야 할 값:

- job_post_id
- company_id
- accessibility_score
- accessibility_grade
- score_detail
- positive_factors
- risk_factors
- evidence_items
- summary
- explanation_version
- used_llm

FastAPI는 데이터가 부족한 경우에도 응답 구조를 깨뜨리지 않는다.

예를 들어 근거 데이터가 부족하면 다음 방식으로 반환한다.

- risk_factors에 “확인 필요” 문구 추가
- evidence_items는 빈 배열 또는 확인 가능한 근거만 반환
- summary에 “일부 접근성 정보는 확인이 필요합니다.” 표현 포함

---

## 16. 현재 MVP 적용 범위

현재 MVP에서는 다음까지만 적용한다.

- 분석 결과는 Spring이 저장/캐싱할 수 있다는 기준만 문서화한다.
- FastAPI는 저장소에 직접 쓰지 않는다.
- explanation_version은 `v1-rule-fallback`으로 고정한다.
- used_llm은 `false`로 고정한다.
- PostGIS 연결 전까지 evidence_items의 record_id는 null일 수 있다.
- 공공데이터 변경 기반 정밀 무효화는 추후 구현한다.

---

## 17. 다음 작업

이 문서 이후 추천 작업은 다음과 같다.

1. Spring 분석 결과 저장 테이블 설계
2. Spring 설명 결과 저장 테이블 설계
3. FastAPI Swagger 예시 보강
4. PostGIS 연결 후 evidence_items.record_id 연결
5. LLM 연결 후 explanation_version/prompt_version 확장