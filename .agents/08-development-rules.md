# 08. Development Rules

## 코드 구조

권장 구조는 다음과 같다.

- app/main.py
- app/api/v1
- app/core
- app/db
- app/models
- app/schemas
- app/services
- app/repositories
- app/clients
- app/llm
- app/gis
- app/scoring
- app/prompts
- app/utils
- scripts
- tests

## 디렉터리 역할

api는 라우터와 HTTP 입출력을 담당한다.

schemas는 Pydantic 요청/응답 모델을 담당한다.

services는 비즈니스 로직을 담당한다.

repositories는 DB 접근을 담당한다.

clients는 외부 API 또는 Spring API 호출을 담당한다.

llm은 LLM 호출, 프롬프트, 출력 파싱을 담당한다.

gis는 PostGIS 공간 질의, 거리 계산, 좌표 처리를 담당한다.

scoring은 접근성 점수와 추천 점수 계산을 담당한다.

prompts는 LLM 프롬프트 템플릿을 담당한다.

core는 설정, 로깅, 예외, 보안을 담당한다.

db는 SQLAlchemy 세션, Base, DB 초기화를 담당한다.

scripts는 실험, CSV, 데이터 점검 스크립트를 담당한다.

tests는 단위 테스트와 통합 테스트를 담당한다.

## Python 코드 스타일

Python 코드는 다음 원칙을 따른다.

- 타입 힌트 사용
- Pydantic 모델 사용
- 함수는 가능한 작게 유지
- 라우터와 서비스 로직 분리
- DB 접근은 repository로 분리
- 설정값 하드코딩 금지
- API 키 하드코딩 금지
- 매직 넘버는 상수화
- 복잡한 점수 계산은 설명 가능한 함수로 분리
- 도메인 용어는 주석으로 보강 가능

## 설정 관리

환경변수는 .env 파일로 관리하되, 실제 비밀키는 커밋하지 않는다.

권장 파일은 다음과 같다.

- .env.local
- .env.dev
- .env.prod
- .env.example

.env.example에는 값이 아닌 키 이름만 둔다.

필수 설정 예시는 다음과 같다.

- APP_ENV
- LOG_LEVEL
- DATABASE_URL
- SPRING_API_BASE_URL
- REDIS_URL
- LLM_PROVIDER
- LLM_BASE_URL
- LLM_MODEL_NAME
- LLM_TIMEOUT_SECONDS
- DATA_GO_KR_SERVICE_KEY
- KRIC_SERVICE_KEY
- SEOUL_OPEN_API_KEY
- WORK24_VOCATIONAL_TRAINING_AUTH_KEY
- WORK24_COMPETENCY_AUTH_KEY
- CORS_ALLOW_ORIGINS

## 로깅 원칙

로그는 stdout으로 출력한다.

로그에 남겨야 하는 정보는 다음과 같다.

- request_id
- endpoint
- source_type
- 분석 대상 job_id 또는 company_id
- 처리 시간
- LLM 모델명
- LLM 호출 성공 여부
- scoring 성공 여부
- 데이터 부족 여부
- 예외 메시지

로그에 남기면 안 되는 정보는 다음과 같다.

- API 인증키
- OAuth 토큰
- 전화번호 전체
- 주민등록번호
- 민감한 장애 상세 정보 원문
- 사용자 입력 원문 전체
- LLM prompt 전체
- DB 접속 비밀번호

민감정보는 마스킹하거나 요약해서 기록한다.

## 테스트 원칙

테스트는 최소한 다음 영역을 포함한다.

- Pydantic schema validation
- 태그 정규화 테스트
- 점수 계산 테스트
- GIS 거리 계산 테스트
- LLM 응답 파싱 테스트
- LLM 실패 fallback 테스트
- API endpoint 테스트
- DB repository 테스트

AI 결과 문장 자체는 완전 일치 비교보다 구조와 필수 필드 검증을 우선한다.

점수 계산은 deterministic하게 유지한다.

LLM이 개입되는 부분은 mock을 사용한다.

## Git 커밋 규칙

커밋은 기능 단위로 나눈다.

권장 prefix는 다음과 같다.

- feat
- fix
- refactor
- docs
- test
- chore
- ci

## PR 작성 기준

PR에는 다음을 포함한다.

- 변경사항
- 테스트 결과
- 영향 범위
- 관련 API
- 관련 데이터 SourceType
- LLM 또는 scoring 변경 여부
- 마이그레이션 여부
- 환경변수 추가 여부

PR 설명 구조는 다음을 권장한다.

## 변경사항

- 사용자 접근성 조건 태그 정규화 API 추가
- Qwen 기반 설명 생성 서비스 인터페이스 추가
- LLM 실패 시 규칙 기반 fallback 응답 추가

## 테스트

- uv run pytest
- 로컬 Swagger에서 API 확인

## 영향 범위

- FastAPI 내부 분석 API
- Spring 연동 요청 스키마
- LLM 설정 환경변수

## 금지사항

다음은 금지한다.

- API 키를 코드에 직접 작성
- .env 파일 커밋
- 사용자 장애 정보를 로그에 원문 저장
- LLM 결과를 검증 없이 그대로 저장
- LLM이 만든 점수를 최종 점수로 사용
- 데이터가 없는데 있다고 설명
- 접근 가능 여부를 확정적으로 단정
- Spring 소유 테이블을 FastAPI에서 임의 수정
- 프론트에서 FastAPI를 직접 호출하는 구조로 변경
- 공공데이터 SourceType 이름을 임의 변경
- 좌표 거리 계산을 단순 위경도 차이로 처리
- 테스트 없이 scoring 로직 변경
- 장애 유형별 불리한 표현 사용

## 개발 우선순위

현재 개발 우선순위는 다음과 같다.

1. 기본 FastAPI 구조 정리
2. health check API
3. 설정 관리
4. 로깅
5. DB 연결
6. CORS 설정
7. 장애 유형별 태그 정규화 API
8. GIS 피처 계산
9. 접근성 점수 계산
10. LLM 설명 생성
11. Spring 연동 안정화

## 가장 중요한 개발 기준

MVP에서는 복잡한 AI보다 안정적인 규칙 기반 분석이 우선이다.

LLM은 태그 구조화 보조, 설명 문장 생성, 상담 요약 생성에 제한적으로 사용한다.

점수 계산은 코드에서 수행하고, LLM은 계산된 결과를 설명한다.