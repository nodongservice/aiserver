# Explanation Policy Agent

## 목적

BridgeWork의 접근성 설명 생성 API 운영 정책을 정의한다.

접근성 점수 계산 API와 설명 생성 API는 분리한다.

이 문서의 데이터 범위는 반드시 [README.md](/Users/emfpdlzj/Desktop/nodong/aiserver/README.md:75)의 `사용데이터 목록`만 따른다.

---

## 데이터 범위

설명 생성에서 직접 언급하거나 근거로 사용할 수 있는 `source_type`은 다음 17개다.

- `KEPAD_RECRUITMENT`
- `KEPAD_JOB_CATEGORY`
- `KEPAD_STANDARD_WORKPLACE`
- `KEPAD_SUPPORT_AGENCY`
- `KORAIL_WEEK_PERSON_FACILITIES`
- `SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT`
- `TRANSPORT_SUPPORT_CENTER`
- `RAIL_WHEELCHAIR_LIFT`
- `RAIL_WHEELCHAIR_LIFT_MOVEMENT`
- `SEOUL_WHEELCHAIR_LIFT`
- `SEOUL_SUBWAY_ENTRANCE_LIFT`
- `SEOUL_WALKING_NETWORK`
- `NATIONWIDE_BUS_STOP`
- `NATIONWIDE_TRAFFIC_LIGHT`
- `NATIONWIDE_CROSSWALK`
- `VOCATIONAL_TRAINING`
- `JOBSEEKER_COMPETENCY_PROGRAM`

설명에서 직접 단정하면 안 되는 예:

- 저상버스 실제 운행 여부
- 사업장 내부 장애인 화장실 존재 여부
- 사업장 내부 자동문 존재 여부
- 실제 건물 경사도
- 실시간 시설 고장 여부
- 실시간 대중교통 정보

이런 항목은 `확인 필요`로 표현한다.

---

## API 분리 원칙

### 접근성 분석 API

Endpoint:

POST /api/v1/accessibility/analyze-batch

역할:

- 접근성 점수 계산
- 접근성 등급 계산
- 점수 상세 생성
- 긍정 요인 생성
- 위험 요인 생성
- 근거 데이터 `evidence_items` 생성

특징:

- 룰 기반으로 동작한다.
- 빠르고 안정적이어야 한다.
- LLM을 사용하지 않는다.
- 추천 목록 화면에서 기본적으로 사용한다.

### 설명 생성 API

Endpoint:

POST /api/v1/explanations/accessibility

역할:

- 접근성 분석 결과를 사용자 친화적인 문장으로 변환한다.
- 상세 설명을 생성한다.
- 확인할 사항을 정리한다.
- 향후 LLM 기반 설명 생성을 담당한다.

특징:

- 점수를 직접 계산하지 않는다.
- 등급을 변경하지 않는다.
- `evidence_items`에 없는 내용을 단정하지 않는다.
- README 사용데이터 목록에 없는 정보를 근거처럼 꾸미지 않는다.
- LLM 장애 또는 지연이 발생해도 추천 점수 계산에는 영향을 주지 않는다.

---

## 호출 정책

### 추천 목록 화면

추천 목록 화면에서는 기본적으로 `/api/v1/accessibility/analyze-batch`만 호출한다.

Spring은 다음 값을 저장하거나 캐싱한다.

- `accessibility_score`
- `accessibility_grade`
- `score_detail`
- `positive_factors`
- `risk_factors`
- `evidence_items`
- `summary`

이 화면에서는 기본 `summary`와 요인 목록만으로 충분하다.

### 공고 상세 화면

공고 상세 화면에서는 필요한 경우 `/api/v1/explanations/accessibility`를 호출한다.

Spring은 analyze-batch 결과를 바탕으로 설명 생성 API를 호출한다.

설명 생성 결과는 상세 화면의 다음 영역에서 사용할 수 있다.

- AI 설명 요약
- 상세 접근성 설명
- 지원 전 확인사항
- 상담사용 참고 설명

### AI 설명 보기 버튼

사용자가 “AI 설명 보기” 버튼을 누르는 경우에만 설명 생성 API를 호출할 수 있다.

이 방식은 LLM 비용과 응답 지연을 줄이는 데 유리하다.

---

## 실패 처리

설명 생성 API가 실패해도 추천 점수 결과는 유지한다.

Spring은 다음 fallback 값을 사용할 수 있다.

- analyze-batch의 `summary`
- `positive_factors`
- `risk_factors`
- `evidence_items`

사용자에게는 다음처럼 표현할 수 있다.

- “상세 설명을 불러오지 못했습니다.”
- “기본 접근성 분석 결과를 표시합니다.”
- “일부 설명은 확인이 필요합니다.”

---

## 캐싱 기준

설명 생성 결과는 다음 기준으로 캐싱할 수 있다.

- `user_id`
- `job_post_id`
- `scoring_version`
- `explanation_version`
- `evidence_items hash`
- `positive_factors hash`
- `risk_factors hash`
- `accessibility_score`
- `accessibility_grade`

## 캐시 무효화 조건

다음 경우 설명 캐시를 무효화한다.

- 사용자 접근성 조건 변경
- 공고 업무환경 태그 변경
- 공고 근무지 좌표 변경
- `evidence_items` 변경
- `positive_factors` 변경
- `risk_factors` 변경
- `scoring_version` 변경
- `explanation_version` 변경
- LLM 프롬프트 정책 변경

---

## 버전 관리

점수 계산 로직과 설명 생성 로직은 별도로 버전 관리한다.

예시:

- `scoring_version = "v1-rule-dummy-gis"`
- `scoring_version = "v2-rule-postgis"`
- `explanation_version = "v1-rule-fallback"`
- `explanation_version = "v2-llm-prompt-basic"`
- `explanation_version = "v3-llm-prompt-accessibility-focused"`

---

## LLM 사용 원칙

LLM은 설명 생성에만 사용한다.

LLM이 하면 안 되는 것:

- `accessibility_score` 변경
- `accessibility_grade` 변경
- `score_detail` 변경
- `evidence_items` 조작
- 존재하지 않는 공공데이터 근거 생성
- README 사용데이터 목록에 없는 시설/서비스를 확인된 것처럼 서술
- 장애 유형이나 건강 상태에 대한 과도한 추론
- 취업 가능/불가능 단정

LLM이 해야 하는 것:

- 이미 계산된 결과를 쉬운 문장으로 설명
- 긍정 요인 정리
- 위험 요인 정리
- 확인 필요 사항 정리
- 사용자에게 과도한 불안을 주지 않는 표현 사용

---

## 표현 원칙

공공데이터가 부족한 경우 단정하지 않는다.

권장 표현:

- “확인 필요”
- “정보가 확인되지 않았습니다”
- “추가 확인을 권장합니다”
- “사용자 조건과 충돌할 수 있습니다”
- “현재 공공데이터 기준으로 확인된 내용입니다”

피해야 할 표현:

- “이 공고는 지원하면 안 됩니다”
- “이 사업장은 접근성이 없습니다”
- “휠체어 사용자는 이용할 수 없습니다”
- “장애 때문에 적합하지 않습니다”
- “저상버스 이용이 가능합니다”
- “건물 내부 장애인 화장실이 있습니다”

마지막 두 예시는 README 사용데이터 목록만으로는 직접 확정하기 어렵다.

---

## 보안 및 개인정보

- 장애 유형 정보는 민감할 수 있으므로 로그에 과도하게 남기지 않는다.
- LLM 프롬프트에는 필요한 최소 정보만 포함한다.
- 이름, 전화번호, 주소 등 직접 식별정보는 가능하면 제외한다.
- 사용자 상세 이력서 내용은 설명 생성에 기본 포함하지 않는다.
- 외부 LLM API 사용 시 전송 데이터 범위를 별도로 검토한다.

---

## 현재 구현 상태

현재는 실제 LLM을 호출하지 않는다.

현재 설명 생성 방식:

- 룰 기반 fallback 설명
- `explanation_version = "v1-rule-fallback"`
- `used_llm = false`

향후 LLM 연결 시에도 아래 원칙은 유지한다.

- README 사용데이터 목록 바깥의 근거를 추가하지 않는다.
- 점수와 등급은 바꾸지 않는다.
- fallback 설명은 계속 유지한다.
