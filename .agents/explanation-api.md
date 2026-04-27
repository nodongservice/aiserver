# 설명 생성 API 운영 정책

BridgeWork는 접근성 점수 계산 API와 설명 생성 API를 분리한다.

## 분리 이유

- 점수 계산은 룰 기반으로 빠르고 안정적으로 처리한다.
- 설명 생성은 향후 LLM을 사용할 수 있으므로 지연, 실패, 비용이 발생할 수 있다.
- LLM 장애가 추천 점수 계산에 영향을 주지 않도록 한다.
- 설명 문구만 재생성하거나 프롬프트를 수정할 수 있게 한다.

## 호출 정책

### 추천 목록 화면

추천 목록 화면에서는 기본적으로 `/api/v1/accessibility/analyze-batch`만 호출한다.

Spring은 다음 값을 저장하거나 캐싱한다.

- accessibility_score
- accessibility_grade
- score_detail
- positive_factors
- risk_factors
- evidence_items
- summary

### 공고 상세 화면

공고 상세 화면에서 더 자세한 설명이 필요한 경우 `/api/v1/explanations/accessibility`를 호출한다.

Spring은 analyze-batch 결과를 바탕으로 설명 생성 API를 호출한다.

### AI 설명 보기 버튼

사용자가 “AI 설명 보기”를 누르는 경우 설명 생성 API를 호출할 수 있다.

이 방식은 LLM 비용과 응답 지연을 줄이는 데 유리하다.

## 실패 처리

설명 생성 API가 실패해도 추천 점수 결과는 유지한다.

Spring은 다음 fallback 값을 사용할 수 있다.

- analyze-batch의 summary
- positive_factors
- risk_factors

## 캐싱 기준

설명 생성 결과는 다음 기준으로 캐싱할 수 있다.

- user_id
- job_post_id
- scoring_version
- explanation_version
- evidence_items hash
- positive_factors hash
- risk_factors hash

## 버전 관리

설명 생성 로직은 점수 계산 로직과 별도로 버전 관리한다.

예시:

- scoring_version = "v1-rule-dummy-gis"
- explanation_version = "v1-rule-fallback"
- explanation_version = "v2-llm-prompt-basic"
- explanation_version = "v3-llm-prompt-accessibility-focused"

## 원칙

- LLM은 점수를 변경하지 않는다.
- LLM은 등급을 변경하지 않는다.
- LLM은 evidence_items에 없는 내용을 단정하지 않는다.
- 데이터가 부족한 경우 “확인 필요”로 표현한다.
- 민감정보를 프롬프트와 로그에 과도하게 포함하지 않는다.