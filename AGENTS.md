# AGENTS.md

이 문서는 BridgeWork FastAPI AI/GIS Service 레포에서 AI 에이전트, Codex, 자동화 도구, 협업 개발자가 따라야 할 작업 기준의 진입점이다.

상세 지침은 `.agents/` 폴더의 문서를 따른다.

## 프로젝트 한 줄 요약

BridgeWork FastAPI AI/GIS Service는 장애인 구직자의 조건을 접근성 태그로 구조화하고, 공공데이터와 PostGIS 기반 공간 분석을 통해 일자리 접근성 점수, 추천 사유, 위험요소 설명, 상담기관용 요약을 생성하는 내부 분석 서비스이다.

전체 서비스 흐름은 다음과 같다.

Next.js Frontend → Spring Backend → FastAPI AI/GIS Service → PostgreSQL/PostGIS + LLM Server

FastAPI는 프론트에서 직접 호출하지 않고, Spring Backend의 내부 API 호출을 받아 분석 결과를 반환하는 것을 기본으로 한다.

## 문서 목록

### `.agents/01-project-context.md`

프로젝트 목적, 핵심 사용자, 주요 기능, MVP 범위를 정의한다.

### `.agents/02-architecture.md`

Next.js, Spring, FastAPI, PostgreSQL/PostGIS, LLM Server, Redis의 역할과 배포 구조를 정의한다.

### `.agents/03-ai-llm-policy.md`

LLM 사용 범위, 프롬프트 원칙, 금지 표현, fallback 정책, 모델 후보를 정의한다.

### `.agents/04-data-source-policy.md`

공공데이터 SourceType, 동기화 대상 데이터, 원본 저장 방식, CSV export 기준을 정의한다.

### `.agents/05-api-design.md`

FastAPI endpoint, 요청/응답 schema, 에러 응답, Spring 연동 방식을 정의한다.

### `.agents/06-db-gis-policy.md`

PostgreSQL schema 분리, PostGIS 사용 원칙, 공간 질의, 접근성 피처 계산 기준을 정의한다.

### `.agents/07-accessibility-policy.md`

WCAG 2.2 AA 기준, 장애 유형별 접근성 고려사항, 사용자 표시 문장 원칙을 정의한다.

### `.agents/08-development-rules.md`

코드 스타일, 테스트, 로깅, 환경변수, Git/PR 규칙, 금지사항을 정의한다.

## 공통 작업 원칙

- 이 레포는 FastAPI 기반 AI/GIS 분석 서비스이다.
- 회원가입, 로그인, OAuth, 공고 CRUD의 주 책임은 Spring Backend에 있다.
- FastAPI는 사용자 조건 태그화, 접근성 점수 계산, GIS 분석, LLM 설명 생성을 담당한다.
- LLM은 점수를 직접 결정하지 않는다.
- 점수 계산은 규칙 기반 코드에서 수행하고, LLM은 계산 결과를 쉬운 한국어로 설명한다.
- 데이터가 없으면 `unknown` 또는 `추가 확인 필요`로 표현한다.
- 접근 가능 여부를 확정적으로 단정하지 않는다.
- 장애 정보는 민감정보로 취급한다.
- API 키, 토큰, 사용자 민감정보를 로그에 남기지 않는다.
- 공공데이터 SourceType 이름은 임의로 변경하지 않는다.
- Spring 소유 테이블을 FastAPI에서 임의 수정하지 않는다.
- 좌표 거리 계산은 단순 위경도 차이가 아니라 PostGIS 또는 적절한 거리 계산 방식을 사용한다.

## 우선 개발 단계

현재 우선순위는 다음과 같다.

1. 기본 FastAPI 구조 정리
2. 장애 유형별 태그 정규화 API
3. 공공데이터 기반 GIS 피처 계산
4. 접근성 점수 계산
5. 추천 사유 및 위험요소 설명 생성
6. Spring Backend 연동 안정화

## 가장 중요한 기준

MVP에서는 복잡한 AI보다 안정적인 규칙 기반 분석이 우선이다.

LLM은 태그 구조화 보조, 설명 문장 생성, 상담 요약 생성에 제한적으로 사용한다.