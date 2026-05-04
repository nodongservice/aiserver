# AGENTS.md

이 문서는 BridgeWork FastAPI AI/GIS Service 레포에서 AI 에이전트, Codex, 자동화 도구, 협업 개발자가 따라야 할 작업 기준의 진입점이다.

상세 지침은 `.agents/` 폴더의 문서를 따른다.

## 프로젝트 한 줄 요약

BridgeWork FastAPI AI/GIS Service는 장애인 구직자의 조건을 접근성 태그로 구조화하고, 공공데이터와 PostGIS 기반 공간 분석을 통해 일자리 접근성 점수, 추천 사유, 위험요소 설명, 상담기관용 요약을 생성하는 내부 분석 서비스이다.

전체 서비스 흐름은 다음과 같다.

React Frontend → Spring Backend → FastAPI AI/GIS Service → PostgreSQL/PostGIS + LLM Server

FastAPI는 프론트에서 직접 호출하지 않고, Spring Backend의 내부 API 호출을 받아 분석 결과를 반환하는 것을 기본으로 한다.

## 데이터 소스
사용하는 데이터는 ../backend/README.md에 안내된 데이터를 따른다.

## 기능정의서
모든 개발은 .agents/specification.md 에 적힌 기능정의서를 기반으로 한다.

## 테스트코드
테스트코드 작성은 .agents/skills/testing/SKILL.md를 따른다.