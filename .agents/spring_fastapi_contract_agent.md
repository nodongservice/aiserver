# 파일: agents/spring_fastapi_contract_agent.md

# Spring-FastAPI Contract Agent

## 목적

이 문서는 BridgeWork 서비스에서 Spring Backend와 FastAPI AI/GIS Service 사이의 내부 호출 계약을 정의한다.

BridgeWork의 사용자-facing API는 Spring Backend가 제공한다.
FastAPI는 프론트엔드가 직접 호출하지 않으며, Spring 내부에서만 호출되는 분석 전용 서비스로 사용한다.

## 전체 호출 흐름
```
Next.js Frontend
→ Spring Backend
→ FastAPI AI/GIS Service
→ Spring Backend
→ Next.js Frontend
```
## 역할 분리

### Spring Backend 역할

Spring Backend는 서비스의 메인 백엔드이다.

담당 책임:

- 로그인/회원가입
- 카카오/네이버 OAuth
- 사용자 프로필 관리
- 이력서 관리
- 공고/기업 관리
- 공공데이터 동기화
- 공공데이터 원본 저장
- 추천 후보 공고 조회
- FastAPI 내부 호출
- 분석 결과 저장/캐싱
- Next.js에 최종 API 제공

Spring은 사용자와 공고의 원본 데이터를 관리한다.
FastAPI는 Spring이 넘겨준 분석용 데이터만 사용한다.

### FastAPI AI/GIS Service 역할

FastAPI는 분석 전용 서비스이다.

담당 책임:

- 사용자 접근성 조건 태그화
- 장애 유형/필요 지원/업무환경 태그 정규화
- 공고별 접근성 점수 계산
- GIS 기반 접근성 분석
- 긍정 요인 생성
- 위험 요인 생성
- 공공데이터 근거 evidence_items 생성
- 향후 LLM 기반 설명 생성

FastAPI는 회원가입, 로그인, OAuth, 공고 CRUD를 담당하지 않는다.

## 기본 원칙

- FastAPI는 프론트엔드가 직접 호출하지 않는다.
- Spring만 FastAPI를 내부 호출한다.
- FastAPI는 사용자 인증을 직접 처리하지 않는다.
- FastAPI 요청에는 분석에 필요한 최소 데이터만 포함한다.
- FastAPI 응답은 Spring이 저장하거나 캐싱한다.
- Next.js는 FastAPI 응답을 직접 받지 않고 Spring API를 통해 받는다.
- 최종 점수는 룰 기반으로 계산한다.
- LLM은 점수를 직접 결정하지 않는다.
- LLM은 설명 생성에만 사용한다.
- 데이터가 부족한 경우 단정하지 않고 “확인 필요”로 표현한다.

## FastAPI 내부 호출 대상

### 1. 태그 정규화 API

Endpoint:

POST /api/v1/tags/normalize

사용 시점:

- 사용자 온보딩 완료 시
- 사용자 프로필 수정 시
- 직장 필터 조건 변경 시
- Spring에서 한글 선택값을 FastAPI 표준 태그로 변환해야 할 때

요청 예시:
```json
{
  "user_id": 1,
  "disability_labels": [
    "지체 - 휠체어"
  ],
  "required_support_labels": [
    "계단 없는 출입 필요",
    "엘리베이터 필요",
    "장애인 화장실 필요",
    "저상버스 필요"
  ],
  "work_environment_labels": [
    "컴퓨터 사용 중심",
    "문서 작업 많음",
    "조용한 근무환경 선호"
  ],
  "transport_preferences": {
    "prefer_bus": true,
    "prefer_subway": true,
    "prefer_transfer": false,
    "prefer_direct_route": true
  }
}
```
응답 예시:
```json
{
  "disability_types": [
    "wheelchair"
  ],
  "required_supports": [
    "step_free_access",
    "elevator",
    "accessible_restroom",
    "low_floor_bus"
  ],
  "work_environment_preferences": [
    "computer_based",
    "document_work",
    "prefer_quiet_environment"
  ],
  "transport_preferences": {
    "prefer_subway": true,
    "prefer_bus": true,
    "prefer_transfer": false,
    "prefer_direct_route": true
  },
  "unknown_labels": []
}
```
Spring 처리 기준:

- disability_types 저장 가능
- required_supports 저장 가능
- work_environment_preferences 저장 가능
- transport_preferences 저장 가능
- unknown_labels가 비어 있지 않으면 로그 또는 관리자 확인 대상으로 남긴다
- unknown_labels가 있어도 전체 요청을 실패 처리할 필요는 없다

## 2. 접근성 분석 API

Endpoint:

POST /api/v1/accessibility/analyze-batch

사용 시점:

- 사용자가 추천 공고 목록을 조회할 때
- Spring이 추천 후보 공고를 선별한 뒤 접근성 점수를 계산해야 할 때
- 공고 상세에서 사용자 맞춤 접근성 분석 결과를 보여줄 때
- 추천 결과 캐시를 갱신할 때

요청 예시:
```json
{
  "user": {
    "user_id": 1,
    "home_lat": 37.5665,
    "home_lng": 126.978,
    "commute_limit_minutes": 60,
    "disability_types": [
      "wheelchair"
    ],
    "required_supports": [
      "step_free_access",
      "elevator",
      "low_floor_bus",
      "accessible_restroom"
    ],
    "work_environment_preferences": [
      "avoid_phone_work",
      "avoid_long_standing",
      "avoid_heavy_lifting",
      "prefer_computer_based_work",
      "prefer_document_work",
      "prefer_quiet_environment"
    ],
    "transport_preferences": {
      "prefer_subway": true,
      "prefer_bus": true,
      "prefer_transfer": false
    }
  },
  "jobs": [
    {
      "job_post_id": 101,
      "company_id": 55,
      "company_name": "ABC복지센터",
      "job_title": "사무보조",
      "work_lat": 37.5701,
      "work_lng": 126.9823,
      "work_address": "서울특별시 중구 세종대로 110",
      "is_standard_workplace": true,
      "is_disability_friendly_post": true,
      "work_environment_tags": [
        "computer_based",
        "document_work",
        "quiet_environment"
      ],
      "support_tags": [
        "interview_accommodation",
        "chat_communication"
      ]
    }
  ]
}
```
응답 예시:
```json
{
  "results": [
    {
      "job_post_id": 101,
      "company_id": 55,
      "accessibility_score": 88,
      "accessibility_grade": "GOOD",
      "score_detail": {
        "transport_score": 25,
        "station_access_score": 20,
        "crosswalk_score": 15,
        "facility_score": 18,
        "work_environment_score": 20,
        "risk_penalty": 0
      },
      "positive_factors": [
        "근무지 주변에 버스정류장 정보가 확인됩니다.",
        "근무지 주변에 지하철역 정보가 확인됩니다.",
        "장애인 표준사업장으로 확인됩니다."
      ],
      "risk_factors": [
        "현재 확인된 주요 위험 요인은 없습니다."
      ],
      "evidence_items": [
        {
          "source_type": "NATIONWIDE_BUS_STOP",
          "source_name": "전국 버스정류장 위치정보",
          "description": "근무지 주변 버스정류장 4개 확인",
          "distance_meters": 180,
          "record_id": null
        }
      ],
      "summary": "접근성 조건이 비교적 양호한 공고입니다."
    }
  ]
}
```
Spring 처리 기준:

- results는 job_post_id 기준으로 기존 공고 후보와 매칭한다
- accessibility_score는 추천 정렬 또는 필터링에 활용할 수 있다
- accessibility_grade는 프론트 표시용으로 활용한다
- score_detail은 상세 분석 화면에 활용한다
- positive_factors는 추천 사유 카드에 활용한다
- risk_factors는 주의 사항 카드에 활용한다
- evidence_items는 “근거 보기” 또는 관리자 검증용으로 활용한다
- summary는 공고 카드의 한 줄 설명으로 활용할 수 있다

## 접근성 등급 기준

GOOD:

- accessibility_score >= 80
- 접근성 조건이 비교적 양호한 공고

CAUTION:

- accessibility_score >= 60
- 일부 접근성 정보 확인이 필요한 공고

RISK:

- accessibility_score < 60
- 사용자 조건과 충돌 가능성이 높은 공고

## 에러 처리 기준

### FastAPI 호출 실패

Spring 처리:

- 추천 API 전체를 실패시키기보다 기본 공고 목록은 반환한다
- 접근성 분석 상태를 “분석 일시 실패” 또는 “확인 필요”로 표시한다
- 장애가 반복되면 로그/모니터링으로 확인한다

### FastAPI 응답 지연

Spring 처리:

- 내부 호출 timeout을 설정한다
- MVP에서는 3~5초 내 응답을 목표로 한다
- timeout 발생 시 접근성 분석 결과 없이 기본 공고 목록을 반환할 수 있다
- 이후 캐시 또는 비동기 분석으로 개선할 수 있다

### unknown_labels 존재

Spring 처리:

- 사용자 요청 자체를 실패시키지 않는다
- unknown_labels를 로그로 남긴다
- 관리자 또는 개발자가 태그 매핑 누락 여부를 확인한다

## 캐싱 기준

Spring은 FastAPI 분석 결과를 저장/캐싱할 수 있다.

추천 캐시 키 예시:

- user_id
- job_post_id
- user_accessibility_profile_hash
- job_accessibility_data_hash
- public_data_snapshot_version

캐시 무효화 조건:

- 사용자 접근성 프로필 변경
- 사용자 이동 선호 변경
- 공고 업무환경 태그 변경
- 공고 근무지 좌표 변경
- 공공데이터 동기화로 관련 데이터 변경
- 점수 계산 로직 버전 변경

## 분석 결과 저장 시 권장 필드

Spring에서 분석 결과를 저장한다면 다음 필드를 권장한다.

- user_id
- job_post_id
- accessibility_score
- accessibility_grade
- score_detail_json
- positive_factors_json
- risk_factors_json
- evidence_items_json
- summary
- scoring_version
- analyzed_at

## 버전 관리

FastAPI 분석 로직은 버전 관리가 필요하다.

예시:

- scoring_version = "v1-rule-dummy-gis"
- scoring_version = "v2-rule-postgis"
- scoring_version = "v3-rule-postgis-llm-summary"

Spring은 분석 결과 저장 시 scoring_version을 함께 저장하는 것이 좋다.

## 보안 기준

- FastAPI는 외부 공개 API로 열지 않는다.
- Spring에서만 접근 가능한 내부 네트워크에 둔다.
- 운영 환경에서는 FastAPI 접근을 보안 그룹, 방화벽, VPC 내부 통신 등으로 제한한다.
- 내부 API라도 요청/응답 로그에 민감정보를 과도하게 남기지 않는다.
- 장애 유형 정보는 민감할 수 있으므로 로그에는 최소한으로 남긴다.

## 향후 확장

Phase 7까지는 repository 인터페이스만 존재하고 실제 PostGIS 조회는 하지 않는다.

향후 확장 방향:

- PostGIS 기반 근처 버스정류장 조회
- PostGIS 기반 근처 횡단보도 조회
- PostGIS 기반 지하철 엘리베이터/리프트 조회
- Spring public_data_record와 FastAPI evidence_items의 record_id 연결
- LLM 기반 자연어 설명 생성
- 분석 결과 캐싱 및 비동기 갱신