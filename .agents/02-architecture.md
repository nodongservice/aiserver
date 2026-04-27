# 02. Architecture

## 전체 아키텍처

전체 서비스 흐름은 다음과 같다.

Next.js Frontend → Spring Backend → FastAPI AI/GIS Service → PostgreSQL/PostGIS + LLM Server

## 컴포넌트 역할

### Next.js Frontend

Next.js는 사용자 화면을 담당한다.

주요 역할은 다음과 같다.

- 지도 UI
- 공고 마커 표시
- 공고 목록 표시
- 필터 및 검색
- 접근성 점수 표시
- AI 설명 표시
- 접근성 상태 라벨 표시

### Spring Backend

Spring Backend는 서비스의 중심 API 서버이다.

주요 역할은 다음과 같다.

- 로그인
- 회원가입
- 카카오/네이버 연동
- 사용자 프로필 관리
- 이력 프로필 관리
- 공고 데이터 관리
- 기업 데이터 관리
- 추천 결과 저장
- 추천 결과 캐싱
- 프론트에 최종 API 제공
- FastAPI에 분석 요청

### FastAPI AI/GIS Service

FastAPI는 AI/GIS 분석 전용 내부 서비스이다.

주요 역할은 다음과 같다.

- 사용자 조건 태그화
- 접근성 점수 계산
- 공공데이터 공간 분석
- 추천 사유 생성
- 위험요소 요약
- 상담사용 요약 생성
- LLM 호출 및 응답 검증
- GIS 피처 계산

### PostgreSQL + PostGIS

하나의 PostgreSQL에 PostGIS 확장을 적용하여 사용한다.

schema는 다음처럼 분리한다.

- app 또는 public schema: 서비스 데이터
- gis schema: 공간 데이터
- ai schema: 분석 및 생성 결과

### LLM Server

LLM Server는 설명 생성과 태그 구조화 보조에 사용한다.

후보는 다음과 같다.

- Ollama
- vLLM

모델 후보는 다음과 같다.

- Qwen2.5 7B Instruct
- Llama 3.1 8B Instruct
- Mistral 7B Instruct
- EXAONE 계열
- EEVE Korean 계열

### Redis

Redis는 필요 시 캐싱과 비동기 작업 보조에 사용한다.

예상 용도는 다음과 같다.

- 추천 결과 캐싱
- 분석 요청 중복 방지
- LLM 응답 캐싱
- 작업 큐 확장 준비

## 배포 기준

기본 배포 구조는 다음과 같다.

- Next.js Frontend: Vercel
- Spring Backend: App 인스턴스 Docker Compose
- FastAPI AI/GIS Service: App 인스턴스 Docker Compose
- LLM Server: App 인스턴스 Docker Compose
- Redis: App 인스턴스 Docker Compose
- PostgreSQL + PostGIS: AWS RDS

## 기본 포트

- Spring Backend: 8080
- FastAPI AI/GIS Service: 8000
- Next.js Frontend: 3000

## 호출 방향

기본 호출 방향은 다음과 같다.

Next.js → Spring → FastAPI

프론트엔드에서 FastAPI를 직접 호출하지 않는다.

FastAPI는 Spring의 내부 분석 요청을 처리하고 결과를 반환한다.

## 데이터 흐름

1. 사용자가 Next.js에서 위치, 통근 범위, 선호 조건을 선택한다.
2. Next.js가 Spring API를 호출한다.
3. Spring이 사용자 프로필과 공고 후보를 조회한다.
4. Spring이 FastAPI에 분석 요청을 보낸다.
5. FastAPI가 PostGIS에서 주변 접근성 데이터를 조회한다.
6. FastAPI가 접근성 점수를 계산한다.
7. FastAPI가 LLM으로 설명을 생성한다.
8. Spring이 결과를 저장하거나 캐싱한다.
9. Next.js가 지도에 마커, 점수, 설명을 표시한다.

## FastAPI 책임 경계

FastAPI가 담당하는 것:

- 접근성 태그 정규화
- 접근성 점수 계산
- GIS 피처 계산
- LLM 설명 생성
- 분석 결과 반환

FastAPI가 담당하지 않는 것:

- OAuth 로그인
- 회원가입
- 사용자 세션 관리
- 공고 CRUD 주 책임
- 이력서 전체 관리
- 결제
- 관리자 백오피스
- 프론트 지도 UI 구현