# 05. API Design

## 기본 원칙

FastAPI API는 Spring Backend가 호출하기 쉽게 설계한다.

기본 원칙은 다음과 같다.

- REST 기반
- JSON 요청/응답
- Pydantic Schema 사용
- 요청 모델과 응답 모델 분리
- 내부 API이더라도 validation 철저히 적용
- 에러 응답 형식 통일
- 분석 결과에는 request_id 포함
- LLM 원문 응답과 사용자 표시 응답 분리
- 긴 작업은 추후 비동기 작업 또는 큐로 분리 가능하게 설계

## 호출 구조

기본 호출 구조는 다음과 같다.

Next.js → Spring Backend → FastAPI AI/GIS Service

FastAPI는 프론트에서 직접 호출하지 않는다.

## 권장 endpoint

권장 endpoint는 다음과 같다.

- GET /api/v1/health
- GET /api/v1/models/status
- POST /api/v1/accessibility/tags/normalize
- POST /api/v1/accessibility/jobs/analyze
- POST /api/v1/accessibility/companies/analyze
- POST /api/v1/recommendations/explain
- POST /api/v1/counseling/summary

실제 endpoint 명은 기존 코드 스타일과 충돌하지 않게 정한다.

## 태그 정규화 API

목적은 사용자 입력을 구조화된 접근성 태그로 변환하는 것이다.

입력 예시는 다음 정보를 포함할 수 있다.

- 희망 직무
- 희망 근무지역
- 통근 범위
- 고용형태
- 경력
- 학력
- 장애 유형
- 필요 지원
- 선호 업무환경
- 기피 업무환경

응답에는 다음 정보를 포함한다.

- request_id
- normalized_tags
- unknown_fields
- warnings
- user_facing_summary

## 공고 접근성 분석 API

목적은 공고 또는 사업장에 대해 접근성 피처와 점수를 계산하는 것이다.

입력 예시는 다음 정보를 포함할 수 있다.

- user_profile_id
- job_post_id
- company_id
- company_address
- company_latitude
- company_longitude
- normalized_tags
- commute_radius_minutes
- preferred_transport_modes

응답에는 다음 정보를 포함한다.

- request_id
- target_job_id
- target_company_id
- accessibility_score
- score_label
- score_breakdown
- matched_reasons
- risk_factors
- unknown_factors
- data_sources
- user_facing_summary
- created_at

## 추천 설명 API

목적은 이미 계산된 점수와 breakdown을 바탕으로 사용자에게 보여줄 설명을 생성하는 것이다.

LLM은 점수를 생성하지 않는다.

LLM은 입력받은 계산 결과를 쉬운 한국어로 설명한다.

응답에는 다음 정보를 포함한다.

- request_id
- summary
- good_points
- check_points
- risk_factors
- unknown_factors
- screen_reader_summary

## 상담기관용 요약 API

목적은 상담사가 참고할 수 있는 요약을 생성하는 것이다.

응답에는 다음 정보를 포함한다.

- request_id
- counselor_summary
- user_conditions_summary
- job_match_summary
- accessibility_summary
- recommended_questions
- caution_notes

## 에러 응답 형식

에러 응답은 일관된 형식을 따른다.

필드는 다음과 같다.

- error_code
- message
- detail
- request_id

사용자에게 노출되는 message는 쉬운 문장으로 작성한다.

운영 환경에서 detail은 과도하게 노출하지 않는다.

## 주요 에러 코드 예시

- INVALID_REQUEST
- VALIDATION_ERROR
- NOT_FOUND
- DATABASE_ERROR
- GIS_ANALYSIS_FAILED
- LLM_TIMEOUT
- LLM_PARSE_FAILED
- EXTERNAL_SERVICE_ERROR
- INTERNAL_SERVER_ERROR

## 응답 문장 원칙

사용자 표시용 문장은 다음 원칙을 따른다.

- 쉬운 한국어 사용
- 단정 표현 금지
- 데이터 근거 표시
- 모르는 것은 추가 확인 필요로 표시
- 색상 없이도 이해 가능한 상태 라벨 포함

상태 라벨 예시는 다음과 같다.

- 접근 양호
- 일부 확인 필요
- 접근 주의
- 데이터 부족
- 추가 확인 필요

## request_id 원칙

모든 분석 요청과 응답에는 request_id를 포함한다.

request_id는 다음 용도로 사용한다.

- 로그 추적
- Spring 연동 디버깅
- LLM 호출 추적
- 분석 결과 재현
- 오류 문의 대응

## timeout 원칙

FastAPI는 외부 또는 내부 서비스 호출 시 timeout을 명시한다.

대상은 다음과 같다.

- LLM Server
- Spring Backend
- Redis
- DB query
- 외부 API

LLM timeout 발생 시 전체 API가 실패하지 않도록 fallback을 둔다.