# BridgeWork Spring ↔ FastAPI 연동 정리

## 1. 목적

이 문서는 Spring Backend 담당자가 FastAPI AI/GIS 분석 서버와 연동하기 위해 알아야 할 API 명세와 Spring 쪽에서 구현해야 할 작업을 간단히 정리한 문서입니다.

FastAPI는 프론트엔드가 직접 호출하지 않고, Spring Backend가 내부에서 호출합니다.

전체 흐름은 다음과 같습니다.

Next.js Frontend  
→ Spring Backend  
→ FastAPI AI/GIS Service  
→ PostgreSQL + PostGIS

---

## 2. 역할 분리

### Spring Backend가 담당하는 것

- 사용자 로그인/회원가입
- OAuth 로그인
- 사용자 프로필 관리
- 이력서 관리
- 공고/기업 관리
- 공공데이터 원본 수집 및 동기화
- 공공데이터 원본 저장
- GIS 분석용 가공 테이블 생성
- 추천 후보 공고 조회
- FastAPI 내부 호출
- 분석 결과 저장/캐싱
- 프론트엔드 최종 API 제공

### FastAPI가 담당하는 것

- 사용자 조건 태그 정규화
- 공고별 접근성 점수 계산
- PostGIS 기반 주변 접근성 시설 조회
- 긍정 요인 생성
- 위험 요인 생성
- evidence_items 생성
- 접근성 설명 생성

---

## 3. Spring이 호출할 FastAPI API 목록

## 3.1 Health Check

### GET /health

FastAPI 서버가 살아 있는지 확인합니다.

응답 예시:

    {
      "status": "ok"
    }

---

### GET /db-health

FastAPI가 PostgreSQL에 연결 가능한지 확인합니다.

응답 예시:

    {
      "status": "ok",
      "database": "connected"
    }

---

### GET /postgis-health

PostGIS extension이 활성화되어 있는지 확인합니다.

응답 예시:

    {
      "status": "ok",
      "postgis": "enabled",
      "version": "3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1"
    }

---

## 3.2 태그 정규화 API

### POST /api/v1/tags/normalize

사용자가 화면에서 선택한 한글 라벨을 FastAPI 내부 표준 태그로 변환합니다.

Spring은 이 API의 응답을 사용자 프로필 또는 필터 조건에 저장해두고, 이후 접근성 분석 API 호출 시 사용할 수 있습니다.

### 요청 예시

    {
      "user_id": 1,
      "disability_labels": ["지체 - 휠체어"],
      "required_support_labels": [
        "계단 없는 출입 필요",
        "엘리베이터 필요",
        "장애인 화장실 필요",
        "저상버스 필요"
      ],
      "work_environment_labels": [
        "전화 응대 적은 업무 선호",
        "조용한 근무환경 선호"
      ],
      "transport_preferences": {
        "prefer_bus": true,
        "prefer_subway": true,
        "prefer_transfer": false,
        "prefer_direct_route": true
      }
    }

### 응답 예시

    {
      "disability_types": ["wheelchair"],
      "required_supports": [
        "step_free_access",
        "elevator",
        "accessible_restroom",
        "low_floor_bus"
      ],
      "work_environment_preferences": [
        "avoid_phone_work",
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

### Spring 처리 기준

- unknown_labels가 있어도 무조건 실패 처리하지 않습니다.
- unknown_labels는 로그 또는 관리자 확인 대상으로 저장하는 것을 권장합니다.
- 정규화된 태그는 사용자 프로필 또는 검색 필터에 저장해 재사용할 수 있습니다.

---

## 3.3 접근성 분석 API

### POST /api/v1/accessibility/analyze-batch

Spring이 추천 후보 공고 목록을 FastAPI에 넘기면, FastAPI가 공고별 접근성 점수와 근거 데이터를 반환합니다.

### 요청 예시

    {
      "user": {
        "user_id": 1,
        "home_lat": 37.5665,
        "home_lng": 126.978,
        "commute_limit_minutes": 60,
        "disability_types": ["wheelchair"],
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

### 응답 예시

    {
      "results": [
        {
          "job_post_id": 101,
          "company_id": 55,
          "accessibility_score": 86,
          "accessibility_grade": "GOOD",
          "score_detail": {
            "transport_score": 20,
            "station_access_score": 15,
            "crosswalk_score": 15,
            "facility_score": 20,
            "work_environment_score": 20,
            "risk_penalty": -4
          },
          "positive_factors": [
            "근무지 주변에 버스정류장 정보가 확인됩니다.",
            "근무지 주변 횡단보도에 보도턱낮춤 정보가 확인됩니다."
          ],
          "risk_factors": [
            "근무지 출입구의 계단 없는 접근 가능 여부는 확인이 필요합니다."
          ],
          "evidence_items": [
            {
              "source_type": "NATIONWIDE_BUS_STOP",
              "source_name": "국토교통부_전국 버스정류장 위치정보",
              "description": "근무지 반경 내 버스정류장 정보가 확인됩니다.",
              "distance_meters": 120.5,
              "record_id": 1001
            }
          ],
          "summary": "접근성 조건이 비교적 양호한 공고입니다."
        }
      ]
    }

### Spring 처리 기준

- Spring은 job_post_id 기준으로 기존 공고 후보와 분석 결과를 매핑합니다.
- FastAPI 응답의 accessibility_score, accessibility_grade, score_detail은 그대로 저장하는 것을 권장합니다.
- positive_factors, risk_factors, evidence_items는 JSON 형태로 저장하면 됩니다.
- evidence_items.record_id는 Spring의 public_data_record.id를 의미합니다.
- FastAPI가 반환한 점수는 LLM이 아니라 룰 기반 점수입니다.

---

## 3.4 접근성 설명 생성 API

### POST /api/v1/explanations/accessibility

접근성 분석 결과를 바탕으로 사용자에게 보여줄 설명 문장을 생성합니다.

현재는 실제 LLM 없이 rule fallback 설명을 반환합니다.

### 요청 예시

    {
      "user_id": 1,
      "job_post_id": 101,
      "company_name": "ABC복지센터",
      "job_title": "사무보조",
      "accessibility_score": 86,
      "accessibility_grade": "GOOD",
      "score_detail": {
        "transport_score": 20,
        "station_access_score": 15,
        "crosswalk_score": 15,
        "facility_score": 20,
        "work_environment_score": 20,
        "risk_penalty": -4
      },
      "positive_factors": [
        "근무지 주변에 버스정류장 정보가 확인됩니다."
      ],
      "risk_factors": [
        "근무지 출입구의 계단 없는 접근 가능 여부는 확인이 필요합니다."
      ],
      "evidence_items": []
    }

### 응답 예시

    {
      "explanation_version": "v1-rule-fallback",
      "short_summary": "ABC복지센터의 접근성 등급은 GOOD입니다.",
      "detail_explanation": "이 공고는 접근성 조건이 비교적 양호하지만 일부 항목은 확인이 필요합니다.",
      "check_points": [
        "근무지 출입구의 계단 없는 접근 가능 여부는 확인이 필요합니다."
      ],
      "used_llm": false
    }

### Spring 처리 기준

- 설명 API는 분석 API와 분리해서 호출합니다.
- 설명 생성 실패가 접근성 점수 제공 실패로 이어지면 안 됩니다.
- 설명 API 실패 시 analyze-batch의 summary, positive_factors, risk_factors를 fallback으로 사용할 수 있습니다.
- explanation_version과 used_llm은 저장해두는 것을 권장합니다.

---

## 4. Spring이 구현해야 하는 것

## 4.1 FastAPI 내부 호출 Client

Spring은 아래 API를 호출할 수 있는 내부 Client를 구현합니다.

- POST /api/v1/tags/normalize
- POST /api/v1/accessibility/analyze-batch
- POST /api/v1/explanations/accessibility
- GET /health
- GET /db-health
- GET /postgis-health

권장 사항:

- FastAPI base URL은 application.yml 또는 환경변수로 관리합니다.
- X-Request-Id 헤더를 전달합니다.
- timeout을 설정합니다.
- 4xx와 5xx 예외를 분리해서 처리합니다.

---

## 4.2 공공데이터 원본 저장

Spring은 기존 방향대로 아래 테이블을 관리합니다.

### public_data_record

원본 공공데이터 레코드 저장 테이블입니다.

필수 또는 권장 컬럼:

- id
- source_type
- external_id
- payload_hash
- payload
- is_active
- collected_at
- created_at
- updated_at

### public_data_record_field

payload를 field_path 단위로 펼친 테이블입니다.

필수 또는 권장 컬럼:

- id
- record_id
- source_type
- field_path
- field_value

---

## 4.3 GIS 분석용 가공 테이블 생성

Spring은 공공데이터 동기화 후, 좌표나 WKT가 있는 데이터를 `public_accessibility_gis_feature`에 가공 저장하는 것을 권장합니다.

FastAPI는 이 테이블을 PostGIS로 조회합니다.

### public_accessibility_gis_feature 권장 컬럼

- id
- public_data_record_id
- source_type
- feature_type
- name
- address
- latitude
- longitude
- geom
- geog
- properties
- is_active
- created_at
- updated_at

### DDL 예시

    CREATE TABLE IF NOT EXISTS public_accessibility_gis_feature (
        id BIGSERIAL PRIMARY KEY,
        public_data_record_id BIGINT NOT NULL,
        source_type VARCHAR(100) NOT NULL,
        feature_type VARCHAR(100) NOT NULL,
        name VARCHAR(255),
        address TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        geom geometry(Geometry, 4326),
        geog geography(Geometry, 4326),
        properties JSONB,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_accessibility_gis_source_type
    ON public_accessibility_gis_feature (source_type);

    CREATE INDEX IF NOT EXISTS idx_accessibility_gis_feature_type
    ON public_accessibility_gis_feature (feature_type);

    CREATE INDEX IF NOT EXISTS idx_accessibility_gis_record_id
    ON public_accessibility_gis_feature (public_data_record_id);

    CREATE INDEX IF NOT EXISTS idx_accessibility_gis_geog
    ON public_accessibility_gis_feature
    USING GIST (geog);

---

## 4.4 GIS feature 생성 대상

우선 아래 SourceType부터 GIS feature로 가공하면 됩니다.

| SourceType | feature_type | 좌표 필드 | 용도 |
|---|---|---|---|
| NATIONWIDE_BUS_STOP | BUS_STOP | GPS_LATI, GPS_LONG | 근처 버스정류장 검색 |
| NATIONWIDE_CROSSWALK | CROSSWALK | latitude, longitude | 근처 횡단보도 검색 |
| NATIONWIDE_TRAFFIC_LIGHT | TRAFFIC_LIGHT | latitude, longitude | 근처 신호등 검색 |
| NATIONWIDE_TRAFFIC_LIGHT | AUDIBLE_SIGNAL | latitude, longitude | 음향신호기 검색 |
| SEOUL_SUBWAY_ENTRANCE_LIFT | SUBWAY_ENTRANCE_LIFT | NODE_WKT | 지하철 출입구 리프트 검색 |
| SEOUL_WHEELCHAIR_LIFT | WHEELCHAIR_LIFT | 역/출입구 좌표 보강 필요 | 휠체어 리프트 검색 |

---

## 4.5 SourceType별 가공 규칙

### NATIONWIDE_BUS_STOP

- source_type: NATIONWIDE_BUS_STOP
- feature_type: BUS_STOP
- name: NODE_NM
- latitude: GPS_LATI
- longitude: GPS_LONG
- public_data_record_id: public_data_record.id
- properties 권장값:
  - NODE_ID
  - NODE_MOBILE_ID
  - CITY_NAME
  - ADMIN_NM

---

### NATIONWIDE_CROSSWALK

- source_type: NATIONWIDE_CROSSWALK
- feature_type: CROSSWALK
- name: crslkManageNo
- address: rdnmadr 또는 lnmadr
- latitude: latitude
- longitude: longitude
- public_data_record_id: public_data_record.id
- properties 권장값:
  - tfclghtYn
  - fnctngSgngnrYn
  - sondSgngnrYn
  - ftpthLowerYn
  - brllBlckYn

FastAPI는 위 properties를 이용해 횡단보도 접근성 점수와 설명을 생성합니다.

---

### NATIONWIDE_TRAFFIC_LIGHT

- source_type: NATIONWIDE_TRAFFIC_LIGHT
- feature_type: TRAFFIC_LIGHT 또는 AUDIBLE_SIGNAL
- name: tfclghtManageNo
- latitude: latitude
- longitude: longitude
- public_data_record_id: public_data_record.id
- properties 권장값:
  - tfclghtSe
  - fnctngSgngnrYn
  - sondSgngnrYn
  - remndrIdctYn

feature_type 기준:

- 기본은 TRAFFIC_LIGHT
- sondSgngnrYn이 Y인 경우 AUDIBLE_SIGNAL로 별도 row를 만들거나, TRAFFIC_LIGHT row의 properties에만 담아도 됩니다.
- FastAPI는 현재 TRAFFIC_LIGHT와 AUDIBLE_SIGNAL 모두 조회할 수 있습니다.

---

### SEOUL_SUBWAY_ENTRANCE_LIFT

- source_type: SEOUL_SUBWAY_ENTRANCE_LIFT
- feature_type: SUBWAY_ENTRANCE_LIFT
- name: SBWY_STN_NM
- geom: ST_SetSRID(ST_GeomFromText(NODE_WKT), 4326)
- geog: geom::geography
- public_data_record_id: public_data_record.id
- properties 권장값:
  - NODE_ID
  - SBWY_STN_CD
  - SBWY_STN_NM
  - SGG_NM
  - EMD_NM

---

## 4.6 PostGIS 좌표 생성 기준

위도/경도 기반 데이터는 아래 방식으로 geom/geog를 생성합니다.

중요: ST_MakePoint는 경도, 위도 순서입니다.

    geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    geog = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography

WKT 기반 데이터는 아래 방식으로 생성합니다.

    geom = ST_SetSRID(ST_GeomFromText(wkt), 4326)
    geog = ST_SetSRID(ST_GeomFromText(wkt), 4326)::geography

---

## 4.7 분석 결과 저장/캐싱

Spring은 analyze-batch 결과를 저장하거나 캐싱할 수 있습니다.

권장 저장 필드:

- user_id
- job_post_id
- company_id
- accessibility_score
- accessibility_grade
- score_detail JSON
- positive_factors JSON
- risk_factors JSON
- evidence_items JSON
- summary
- analyzed_at

캐시 무효화 조건:

- 사용자 접근성 조건 변경
- 공고 위치 변경
- 공고 업무환경 태그 변경
- 공공데이터 동기화 결과 변경
- public_accessibility_gis_feature 변경

---

## 5. 에러 응답 형식

FastAPI는 공통 에러 포맷을 반환합니다.

예시:

    {
      "error_code": "VALIDATION_ERROR",
      "message": "요청 값 검증에 실패했습니다.",
      "detail": [],
      "request_id": "..."
    }

주요 error_code:

| HTTP Status | error_code | 의미 |
|---:|---|---|
| 422 | VALIDATION_ERROR | 요청 필드 누락 또는 타입 오류 |
| 500 | AI_SERVICE_INTERNAL_ERROR | FastAPI 내부 오류 |
| 503 | AI_SERVICE_UNAVAILABLE | 의존성 장애 |
| 504 | AI_SERVICE_TIMEOUT | 처리 시간 초과 |

Spring은 FastAPI 원본 에러를 프론트엔드에 그대로 노출하지 않고, 서비스용 에러 메시지로 변환하는 것을 권장합니다.

---

## 6. Spring 쪽 구현 체크리스트

### 필수

- FastAPI 내부 호출 Client 구현
- 태그 정규화 API 호출
- 접근성 분석 API 호출
- 설명 API 호출
- public_data_record 저장
- public_data_record_field 저장
- public_accessibility_gis_feature 테이블 생성
- 좌표가 있는 공공데이터를 GIS feature로 가공 저장
- analyze-batch 결과 저장 또는 캐싱

### 우선 구현 추천

1. public_accessibility_gis_feature 테이블 생성
2. NATIONWIDE_BUS_STOP → BUS_STOP 변환
3. NATIONWIDE_CROSSWALK → CROSSWALK 변환
4. NATIONWIDE_TRAFFIC_LIGHT → TRAFFIC_LIGHT 변환
5. SEOUL_SUBWAY_ENTRANCE_LIFT → SUBWAY_ENTRANCE_LIFT 변환
6. FastAPI analyze-batch 호출
7. 결과 저장/캐싱

### 나중에 해도 되는 것

- 주소 지오코딩
- 역/출입구 좌표 보강
- SEOUL_WHEELCHAIR_LIFT 정확 좌표 매핑
- KORAIL/RAIL 데이터 역코드 매핑
- LLM 설명 캐싱 고도화

---
## 기타 참고사항
- GIS feature 생성 주체 :Spring
- FastAPI 역할 :GIS feature 읽기 전용 분석
- feature_type :DB는 문자열, 코드에서는 enum/상수
- AUDIBLE_SIGNAL :MVP에서는 TRAFFIC_LIGHT properties로 처리 
- 삭제 정책 :is_active=false soft delete
- 재동기화 후 갱신 :MVP는 source_type 단위 재생성
- 분석 결과 저장 테이블 :accessibility_analysis_result
- 설명 결과 저장 테이블 :accessibility_explanation_result
- 분석/설명 저장 방식 :분리 저장
- LLM 도입 후 정책 :설명만 LLM, 점수 변경 금지