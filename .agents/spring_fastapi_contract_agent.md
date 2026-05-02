# Spring-FastAPI 내부 호출 계약 가이드

## 1. 목적

이 문서는 BridgeWork 서비스에서 Spring Backend와 FastAPI AI/GIS Service 사이의 내부 API 호출 계약을 정의한다.

BridgeWork의 기본 호출 흐름은 다음과 같다.

Next.js Frontend  
→ Spring Backend  
→ FastAPI AI/GIS Service  
→ PostgreSQL + PostGIS / LLM Server

FastAPI는 프론트엔드가 직접 호출하지 않는다. FastAPI는 Spring 내부 호출 전용 분석 서버로 사용한다.

이 문서는 README.md에 정의된 공공데이터 동기화 대상 데이터만을 전제로 한다.

---

## 2. 역할 분리

### 2.1 Spring Backend 역할

Spring은 사용자와 서비스의 중심 API 서버다.

Spring이 담당하는 영역은 다음과 같다.

- 로그인/회원가입
- 카카오/네이버 OAuth
- 사용자 프로필 관리
- 이력서 관리
- 공고/기업 관리
- 공공데이터 원본 수집 및 동기화
- `public_data_record` 저장
- `public_data_record_field` 저장
- `public_accessibility_gis_feature` 생성/갱신 권장
- 추천 후보 공고 조회
- FastAPI 내부 호출
- 분석 결과 저장/캐싱
- 프론트엔드에 최종 API 제공

### 2.2 FastAPI AI/GIS Service 역할

FastAPI는 접근성 분석과 설명 생성을 담당한다.

FastAPI가 담당하는 영역은 다음과 같다.

- 사용자 접근성 조건 태그화
- PostGIS 기반 접근성 분석
- 공고별 접근성 점수 계산
- 긍정 요인 생성
- 위험 요인 생성
- 근거 데이터 반환
- 사용자용 접근성 설명 생성
- 향후 LLM 기반 설명 생성

FastAPI는 원칙적으로 공공데이터 원본 수집을 담당하지 않는다.

---

## 3. 핵심 원칙

### 3.1 FastAPI는 내부 호출 전용이다

FastAPI API는 Next.js Frontend에서 직접 호출하지 않는다.

프론트엔드는 항상 Spring API만 호출한다. Spring은 필요한 경우 FastAPI를 내부적으로 호출하고, 결과를 가공하거나 저장한 뒤 프론트엔드에 반환한다.

### 3.2 점수 계산은 룰 기반이다

최종 접근성 점수는 FastAPI의 룰 기반 로직으로 계산한다.

LLM이 점수나 등급을 직접 결정하면 안 된다.

### 3.3 LLM은 설명 생성에만 사용한다

향후 LLM을 연결하더라도 LLM은 다음 영역에만 사용한다.

- 설명 문장 생성
- 위험 요인 문장 정리
- 사용자 친화적 요약 생성
- 확인 필요 항목 표현 개선

LLM은 다음 값을 변경하면 안 된다.

- accessibility_score
- accessibility_grade
- score_detail
- positive_factors
- risk_factors
- evidence_items

### 3.4 데이터 부족 시 “확인 필요”로 표현한다

공공데이터 또는 GIS 데이터가 부족한 경우, 임의로 긍정 또는 부정 판단하지 않는다.

데이터가 부족한 항목은 다음 방식으로 표현한다.

- risk_factors에 확인 필요 문구 추가
- explanation API에서 check_points에 확인 권장 항목 추가
- evidence_items에는 확인 가능한 근거만 포함

### 3.5 README에 없는 데이터는 직접 판정하지 않는다

README.md의 동기화 대상 데이터에 없는 항목은 FastAPI 분석 결과에서 확정 표현하지 않는다.

예:

- 저상버스 운행 여부
- 사업장 내부 장애인 화장실
- 사업장 내부 자동문
- 실제 건물 경사도
- 실시간 시설 고장 여부
- 실시간 대중교통 정보
- 별도 장애인 편의시설 표준데이터

위 항목은 데이터가 추가되기 전까지 “확인 필요”로 처리한다.

---

## 4. README 기준 공공데이터 사용 계약

### 4.1 Spring이 동기화해야 하는 SourceType

Spring은 README.md에 정의된 다음 SourceType을 동기화 대상으로 관리한다.

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

### 4.2 Spring 저장 테이블

Spring은 공공데이터 원본을 다음 구조로 저장한다.

#### public_data_record

원본 레코드 단위 저장 테이블이다.

권장 필드:

- id
- source_type
- external_id
- payload
- payload_hash
- collected_at
- updated_at
- is_active

#### public_data_record_field

원본 payload를 field_path 단위로 펼쳐 저장한다.

권장 필드:

- id
- public_data_record_id
- source_type
- field_path
- field_value

#### public_accessibility_gis_feature

PostGIS 근접 검색용 가공 테이블이다.

FastAPI는 이 테이블을 읽어 접근성 분석에 활용한다.

권장 필드:

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

권장 unique constraint:

- `(public_data_record_id, feature_type)`

### 4.3 GIS feature 생성 주체

운영 기준 권장안은 Spring이 `public_accessibility_gis_feature`를 생성/갱신하는 것이다.

권장 흐름:

1. Spring이 공공데이터 원본 API 호출
2. `public_data_record` 저장
3. `public_data_record_field` 저장
4. 좌표/WKT/역코드/주소 기반으로 `public_accessibility_gis_feature` 생성 또는 갱신
5. FastAPI는 `public_accessibility_gis_feature`를 읽어 분석 수행

FastAPI의 GIS feature builder는 개발/검증용으로 둘 수 있으나, 운영 주체는 Spring으로 두는 것이 책임 분리에 적합하다.

---

## 5. SourceType별 GIS Feature 변환 계약

### 5.1 좌표 기반 POINT 생성

아래 SourceType은 위도/경도가 명확하므로 Spring이 POINT geometry/geography를 생성할 수 있다.

| SourceType | latitude field | longitude field | feature_type | name 후보 |
|---|---|---|---|---|
| `NATIONWIDE_BUS_STOP` | `GPS_LATI` | `GPS_LONG` | `BUS_STOP` | `NODE_NM` |
| `NATIONWIDE_CROSSWALK` | `latitude` | `longitude` | `CROSSWALK` | `crslkManageNo` |
| `NATIONWIDE_TRAFFIC_LIGHT` | `latitude` | `longitude` | `TRAFFIC_LIGHT` | `tfclghtManageNo` |
| `TRANSPORT_SUPPORT_CENTER` | `LATITUDE` | `LONGITUDE` | `TRANSPORT_SUPPORT_CENTER` | `TFCWKER_MVMN_CNTER_NM` |

PostGIS 좌표 생성 시 `ST_MakePoint(longitude, latitude)` 순서를 사용한다.

### 5.2 WKT 기반 geometry 생성

아래 SourceType은 WKT 필드를 사용한다.

| SourceType | WKT field | feature_type | 비고 |
|---|---|---|---|
| `SEOUL_SUBWAY_ENTRANCE_LIFT` | `NODE_WKT` | `SUBWAY_ENTRANCE_LIFT` | 지하철 출입구 리프트 |
| `SEOUL_WALKING_NETWORK` | `NODE_WKT` | `WALKING_NODE` | 향후 보행 네트워크 분석 |
| `SEOUL_WALKING_NETWORK` | `LNKG_WKT` | `WALKING_LINK` | 향후 보행 네트워크 분석 |

MVP에서는 `SEOUL_SUBWAY_ENTRANCE_LIFT`를 우선 활용한다.

`SEOUL_WALKING_NETWORK`는 README에는 포함되어 있으나 실제 경로 탐색 기능이 후순위이므로, 초기에는 저장만 하고 점수에는 제한적으로 사용한다.

### 5.3 역코드/역명 매핑 기반 데이터

아래 SourceType은 좌표가 직접 없거나 역코드/역명 중심이다.

Spring은 프로젝트에 포함된 역사 코드 파일 또는 별도 매핑 테이블을 사용해 역/출입구 좌표를 보강할 수 있다.

| SourceType | 주요 위치 필드 | 활용 방식 |
|---|---|---|
| `KORAIL_WEEK_PERSON_FACILITIES` | `stn_cd`, `stn_nm` | 역 좌표 매핑 후 역사 편의시설 근거로 활용 |
| `SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT` | `stnCd`, `stnNm`, `vcntEntrcNo` | 역/출입구 좌표 매핑 후 휠체어리프트 근거로 활용 |
| `RAIL_WHEELCHAIR_LIFT` | `stinCd`, `exitNo` | 역/출입구 좌표 매핑 후 휠체어리프트 근거로 활용 |
| `RAIL_WHEELCHAIR_LIFT_MOVEMENT` | `stinCd` | 역 좌표 매핑 후 이동동선 설명 보조 근거로 활용 |
| `SEOUL_WHEELCHAIR_LIFT` | `STATION NAME`, `ENTRANCE NUMBER` | 역명/출입구 번호 매핑 후 휠체어리프트 근거로 활용 |

좌표 매핑 신뢰도가 낮으면 properties에 `mapping_confidence`, `coordinate_source`를 남기는 것을 권장한다.

### 5.4 주소 기반 지오코딩 필요 데이터

아래 SourceType은 주소가 있으나 좌표가 직접 없거나 공고/기관 주소 중심이다.

| SourceType | 주소 필드 | 활용 방식 |
|---|---|---|
| `KEPAD_RECRUITMENT` | `compAddr` | 공고 근무지 좌표 생성 또는 Spring 공고 좌표와 매칭 |
| `KEPAD_STANDARD_WORKPLACE` | `address` | 표준사업장 위치 좌표 생성 |
| `KEPAD_SUPPORT_AGENCY` | `excInstnAddr` | 근로지원인 수행기관 위치 좌표 생성 |
| `VOCATIONAL_TRAINING` | `ADDRESS` | 훈련기관 위치 좌표 생성 |
| `JOBSEEKER_COMPETENCY_PROGRAM` | `openPlcCont` | 프로그램 장소 좌표 생성 가능 시 활용 |

주소 지오코딩 결과는 데이터 품질에 따라 다음 상태를 남기는 것을 권장한다.

- `geocoding_status`
- `coordinate_source`
- `coordinate_quality`

---

## 6. FeatureType 계약

DB에는 문자열로 저장하고, Spring/FastAPI 코드에서는 enum 또는 상수로 관리한다.

권장 feature_type:

- `BUS_STOP`
- `CROSSWALK`
- `TRAFFIC_LIGHT`
- `SUBWAY_ENTRANCE_LIFT`
- `WHEELCHAIR_LIFT`
- `TRANSPORT_SUPPORT_CENTER`
- `SUPPORT_AGENCY`
- `STANDARD_WORKPLACE`
- `KORAIL_ACCESSIBLE_FACILITY`
- `WALKING_NODE`
- `WALKING_LINK`
- `VOCATIONAL_TRAINING_CENTER`
- `JOBSEEKER_COMPETENCY_PROGRAM_PLACE`

주의:

- `AUDIBLE_SIGNAL`은 MVP에서는 별도 row로 만들지 않고 `TRAFFIC_LIGHT.properties.sondSgngnrYn`으로 관리한다.
- 음향신호기를 지도에 별도 마커로 표시해야 하는 요구가 생기면 `AUDIBLE_SIGNAL` feature_type을 추가할 수 있다.

---

## 7. 공통 호출 기준

### 7.1 Base URL

환경별 Base URL은 Spring 설정 파일에서 관리한다.

예시:

- local: `http://localhost:8000`
- dev: `http://bridgework-ai:8000`
- prod: 내부망 또는 private endpoint 사용

Spring에서는 FastAPI URL을 코드에 직접 하드코딩하지 않고 환경변수 또는 `application.yml`에서 관리한다.

예시 설정명:

- `bridgework.ai.base-url`
- `bridgework.ai.timeout.connect`
- `bridgework.ai.timeout.read`

### 7.2 인증/보안

FastAPI는 내부 서버 전용으로 운영한다.

운영 환경에서는 다음 중 하나 이상을 적용한다.

- 같은 VPC 또는 내부 네트워크에서만 접근 허용
- Security Group으로 Spring 서버만 접근 허용
- API Gateway 또는 Nginx 내부 라우팅 제한
- 내부 호출용 API Key 헤더 추가

권장 내부 헤더:

- `X-Internal-Api-Key`
- `X-Request-Id`
- `X-Service-Name`

### 7.3 Timeout 기준

권장 timeout:

- 태그 정규화 API: 1~3초
- 접근성 분석 API: 3~10초
- 설명 생성 API: 3~15초

LLM 연결 이후에도 설명 생성 API timeout은 별도로 관리한다. 설명 생성 실패가 추천 점수 계산 실패로 이어지면 안 된다.

---

## 8. API 1: 태그 정규화 API

## POST /api/v1/tags/normalize

### 8.1 역할

사용자 온보딩 또는 직장 필터에서 선택한 한글 라벨을 FastAPI 내부 표준 태그로 변환한다.

Spring은 이 API의 응답을 사용자 프로필 또는 필터 조건에 저장할 수 있다. 이후 접근성 분석 API 호출 시 정규화된 태그를 그대로 사용한다.

### 8.2 요청 DTO

Spring 요청 DTO 권장명:

- `AiTagNormalizeRequest`
- `AiTagNormalizeResponse`

### 8.3 요청 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---:|---|
| user_id | number | 선택 | 사용자 ID. 로그 추적용 |
| disability_labels | string[] | 선택 | 화면에서 선택한 장애 유형 원본 라벨 |
| required_support_labels | string[] | 선택 | 화면에서 선택한 필요 지원 원본 라벨 |
| work_environment_labels | string[] | 선택 | 화면에서 선택한 업무환경 선호/기피 라벨 |
| transport_preferences | object | 선택 | 이동수단 선호 정보 |

### 8.4 transport_preferences 필드

| 필드 | 타입 | 기본값 | 설명 |
|---|---|---:|---|
| prefer_bus | boolean | true | 버스 선호 여부 |
| prefer_subway | boolean | true | 지하철 선호 여부 |
| prefer_transfer | boolean | false | 환승 선호 여부 |
| prefer_direct_route | boolean | true | 직행 선호 여부 |

### 8.5 응답 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| disability_types | string[] | 표준 장애 유형 태그 |
| required_supports | string[] | 표준 필요 지원 태그 |
| work_environment_preferences | string[] | 표준 업무환경 선호/기피 태그 |
| transport_preferences | object | 표준 이동 선호값 |
| unknown_labels | string[] | 정규화하지 못한 원본 라벨 |

### 8.6 Spring 처리 기준

Spring은 unknown_labels가 비어 있지 않아도 요청을 실패 처리하지 않는다.

대신 다음 중 하나로 처리한다.

- 로그 기록
- 관리자 확인 대상 저장
- 신규 프론트 옵션 누락 여부 확인
- 사용자는 나머지 정상 태그 기준으로 계속 진행

---

## 9. API 2: 접근성 분석 API

## POST /api/v1/accessibility/analyze-batch

### 9.1 역할

Spring이 추천 후보 공고 목록을 조회한 뒤, 사용자 접근성 조건과 함께 FastAPI로 전달한다.

FastAPI는 공고별 접근성 점수, 등급, 긍정 요인, 위험 요인, 근거 데이터를 반환한다.

### 9.2 요청 DTO

Spring 요청 DTO 권장명:

- `AiAccessibilityAnalyzeRequest`
- `AiAccessibilityAnalyzeResponse`
- `AiUserAccessibilityCondition`
- `AiJobCandidate`
- `AiTransportPreferences`

### 9.3 요청 최상위 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---:|---|
| user | object | 필수 | 분석 대상 사용자 조건 |
| jobs | object[] | 필수 | 분석 대상 공고 후보 목록 |

### 9.4 user 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---:|---|
| user_id | number | 필수 | Spring DB 사용자 ID |
| home_lat | number | 필수 | 사용자 기준 위치 위도 |
| home_lng | number | 필수 | 사용자 기준 위치 경도 |
| commute_limit_minutes | number | 필수 | 최대 통근 허용 시간 |
| disability_types | string[] | 선택 | 표준 장애 유형 태그 |
| required_supports | string[] | 선택 | 표준 필요 지원 태그 |
| work_environment_preferences | string[] | 선택 | 표준 업무환경 선호/기피 태그 |
| transport_preferences | object | 선택 | 이동수단 선호 정보 |

주의:

- `required_supports`에 `low_floor_bus`가 들어올 수는 있으나, README 기준 동기화 데이터에는 저상버스 운행 여부가 없다.
- FastAPI는 이 경우 직접 가점하지 않고 확인 필요 문구로 처리한다.

### 9.5 jobs 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---:|---|
| job_post_id | number | 필수 | Spring DB 공고 ID |
| company_id | number | 필수 | Spring DB 기업 ID |
| company_name | string | 필수 | 기업명 |
| job_title | string | 필수 | 공고 제목 또는 직무명 |
| work_lat | number | 필수 | 근무지 위도 |
| work_lng | number | 필수 | 근무지 경도 |
| work_address | string | 선택 | 근무지 주소 |
| is_standard_workplace | boolean | 선택 | 장애인 표준사업장 여부 |
| is_disability_friendly_post | boolean | 선택 | 장애인 우대/전형 여부 |
| work_environment_tags | string[] | 선택 | 공고 업무환경 태그 |
| support_tags | string[] | 선택 | 공고 지원 제도 태그 |

주의:

- `work_lat`, `work_lng`는 Spring이 공고 주소를 지오코딩하거나 기존 저장 좌표를 사용해 제공한다.
- 공고 좌표가 없으면 FastAPI는 PostGIS 근접 검색을 수행할 수 없으므로 해당 공고는 분석 제외 또는 확인 필요 처리한다.

### 9.6 응답 DTO

Spring 응답 DTO 권장명:

- `AiAccessibilityAnalyzeResponse`
- `AiAccessibilityAnalyzeResult`
- `AiScoreDetail`
- `AiEvidenceItem`

### 9.7 응답 최상위 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| results | object[] | 공고별 접근성 분석 결과 목록 |

### 9.8 result 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| job_post_id | number | 분석 대상 공고 ID |
| company_id | number | 분석 대상 기업 ID |
| accessibility_score | number | 최종 접근성 점수 |
| accessibility_grade | string | GOOD, CAUTION, RISK |
| score_detail | object | 세부 점수 |
| positive_factors | string[] | 긍정 요인 |
| risk_factors | string[] | 위험 요인 |
| evidence_items | object[] | 근거 데이터 |
| summary | string | 사용자 노출용 한 줄 요약 |

### 9.9 score_detail 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| transport_score | number | 버스정류장 중심 대중교통 접근성 점수 |
| station_access_score | number | 지하철/역사/리프트 접근성 점수 |
| crosswalk_score | number | 횡단보도/신호등/보행 안전 점수 |
| facility_score | number | 표준사업장/역사 편의시설/지원 인프라 점수 |
| work_environment_score | number | 직무/업무환경 접근성 점수 |
| risk_penalty | number | 위험 요소 감점 |

### 9.10 evidence_items 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---:|---|
| source_type | string | 필수 | 공공데이터 SourceType |
| source_name | string | 필수 | 공공데이터 이름 |
| description | string | 필수 | 근거 요약 |
| distance_meters | number | 선택 | 관련 거리 |
| record_id | number | 선택 | Spring `public_data_record.id` |

`record_id`는 원칙적으로 Spring이 저장한 `public_data_record.id`를 사용한다.

### 9.11 접근성 등급 기준

| 등급 | 기준 | 의미 |
|---|---:|---|
| GOOD | 80점 이상 | 접근성 양호 |
| CAUTION | 60점 이상 80점 미만 | 일부 확인 필요 |
| RISK | 60점 미만 | 접근성 제약 가능성 또는 확인 필요성 높음 |

### 9.12 Spring 처리 기준

Spring은 FastAPI 응답의 `job_post_id`를 기준으로 기존 공고 후보와 매핑한다.

현재 analyze-batch 응답에는 `company_name`과 `job_title`이 포함되지 않는다. 따라서 프론트엔드 표시용 기업명과 공고명은 Spring이 기존 공고 데이터에서 조합한다.

Spring은 분석 결과를 저장하거나 캐싱할 수 있다.

권장 저장 필드:

- user_id
- job_post_id
- accessibility_score
- accessibility_grade
- score_detail JSON
- positive_factors JSON
- risk_factors JSON
- evidence_items JSON
- summary
- analyzed_at
- public_data_snapshot_key

---

## 10. API 3: 접근성 설명 생성 API

## POST /api/v1/explanations/accessibility

### 10.1 역할

접근성 분석 API 결과를 바탕으로 사용자에게 보여줄 설명 문구를 생성한다.

이 API는 점수를 새로 계산하지 않는다. 이미 계산된 점수, 등급, 요인, 근거를 받아 설명만 생성한다.

현재는 실제 LLM을 호출하지 않고 룰 기반 fallback 설명을 반환한다.

### 10.2 요청 DTO

Spring 요청 DTO 권장명:

- `AiAccessibilityExplanationRequest`
- `AiAccessibilityExplanationResponse`

### 10.3 요청 필드

| 필드 | 타입 | 필수 여부 | 설명 |
|---|---|---:|---|
| user_id | number | 선택 | 사용자 ID. 로그 추적용 |
| job_post_id | number | 필수 | 공고 ID |
| company_name | string | 필수 | 기업명 |
| job_title | string | 필수 | 공고 제목 또는 직무명 |
| accessibility_score | number | 필수 | 접근성 점수 |
| accessibility_grade | string | 필수 | 접근성 등급 |
| score_detail | object | 필수 | 세부 점수 |
| positive_factors | string[] | 선택 | 긍정 요인 |
| risk_factors | string[] | 선택 | 위험 요인 |
| evidence_items | object[] | 선택 | 근거 데이터 |

### 10.4 응답 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| explanation_version | string | 설명 생성 로직 버전 |
| short_summary | string | 공고 카드용 짧은 설명 |
| detail_explanation | string | 상세 화면용 설명 |
| check_points | string[] | 사용자 확인 권장 사항 |
| used_llm | boolean | LLM 사용 여부 |

### 10.5 현재 응답 정책

| 필드 | 값 |
|---|---|
| explanation_version | v1-rule-fallback |
| used_llm | false |

### 10.6 Spring 처리 기준

Spring은 설명 API 결과를 별도로 저장하거나 캐싱할 수 있다.

권장 캐싱 기준:

- user_id
- job_post_id
- accessibility_score
- accessibility_grade
- explanation_version

설명 API 호출 실패 시에도 접근성 점수 결과는 유지한다.

설명 생성 실패 시 Spring은 다음 중 하나로 fallback 처리한다.

- analyze-batch의 summary 사용
- positive_factors와 risk_factors를 그대로 노출
- “상세 설명은 잠시 후 다시 확인해 주세요.” 표시

---

## 11. 에러 응답 포맷

### 11.1 기본 원칙

FastAPI는 요청 검증 실패 시 422 응답을 반환한다.

Spring에서 처리하기 쉽게 공통 에러 포맷을 맞춘다.

### 11.2 권장 에러 응답 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| error_code | string | 에러 코드 |
| message | string | 사용자 또는 개발자용 메시지 |
| detail | object 또는 array | 상세 오류 정보 |
| request_id | string | 요청 추적 ID |

### 11.3 권장 에러 코드

| HTTP Status | error_code | 의미 |
|---:|---|---|
| 400 | INVALID_REQUEST | 요청 형식 오류 |
| 401 | UNAUTHORIZED_INTERNAL_REQUEST | 내부 인증 실패 |
| 422 | VALIDATION_ERROR | 필수 필드 누락 또는 타입 오류 |
| 500 | AI_SERVICE_INTERNAL_ERROR | FastAPI 내부 오류 |
| 503 | AI_SERVICE_UNAVAILABLE | FastAPI 또는 LLM/GIS 의존성 장애 |
| 504 | AI_SERVICE_TIMEOUT | FastAPI 처리 시간 초과 |

### 11.4 Spring 처리 기준

Spring은 FastAPI 호출 실패 시 프론트엔드에 FastAPI 원본 에러를 그대로 노출하지 않는다.

Spring은 서비스 상황에 맞게 다음 방식으로 변환한다.

- 추천 점수 계산 실패: 해당 공고 분석 제외 또는 “분석 불가” 표시
- 설명 생성 실패: 기본 summary 또는 fallback 문구 사용
- 태그 정규화 실패: 원본 선택값 재확인 유도
- timeout: 재시도 또는 fallback 처리

---

## 12. Spring WebClient/RestClient 연동 기준

### 12.1 WebClient 사용 시 권장 사항

Spring에서 FastAPI를 호출할 때는 다음 기준을 따른다.

- Base URL은 설정 파일에서 주입한다.
- connect timeout과 read timeout을 분리한다.
- X-Request-Id를 전달한다.
- FastAPI 응답 DTO를 명확히 분리한다.
- 4xx와 5xx를 구분해서 처리한다.
- 설명 API 실패가 분석 API 실패로 전파되지 않게 한다.

### 12.2 호출 순서

추천 기본 흐름은 다음과 같다.

1. Spring이 사용자 프로필/필터 조건을 조회한다.
2. 필요하면 FastAPI 태그 정규화 API를 호출한다.
3. Spring이 추천 후보 공고 목록을 조회한다.
4. Spring이 FastAPI analyze-batch API를 호출한다.
5. Spring이 분석 결과를 저장 또는 캐싱한다.
6. 상세 설명이 필요한 경우 explanation API를 별도로 호출한다.
7. Spring이 최종 응답을 Next.js에 반환한다.

### 12.3 설명 API 분리 호출 원칙

설명 API는 analyze-batch와 분리해서 호출한다.

이유는 다음과 같다.

- 점수 계산과 설명 생성을 분리할 수 있다.
- LLM 장애/지연이 추천 점수 계산에 영향 주지 않는다.
- 설명만 재생성할 수 있다.
- 프롬프트 수정 시 scoring_service.py를 건드릴 필요가 없다.
- 비용 제어가 쉽다.
- 캐싱 전략을 분리할 수 있다.

---

## 13. 캐싱 기준

### 13.1 분석 결과 캐싱

Spring은 접근성 분석 결과를 캐싱할 수 있다.

권장 캐시 키 구성:

- user_id
- job_post_id
- user_accessibility_condition_hash
- job_accessibility_condition_hash
- public_data_snapshot_key

캐시 무효화 조건:

- 사용자 접근성 조건 변경
- 공고 업무환경 태그 변경
- 공고 근무지 좌표 변경
- 공공데이터 동기화 결과 변경
- `public_accessibility_gis_feature` 변경
- 점수 계산 로직 변경

### 13.2 설명 결과 캐싱

설명 결과는 분석 결과와 별도로 캐싱한다.

권장 캐시 키 구성:

- user_id
- job_post_id
- accessibility_score
- accessibility_grade
- explanation_version

캐시 무효화 조건:

- explanation_version 변경
- positive_factors 변경
- risk_factors 변경
- evidence_items 변경
- LLM 프롬프트 버전 변경

---

## 14. 현재 MVP 범위

현재 FastAPI AI/GIS 분석 서버는 다음 범위를 가진다.

포함된 기능:

- `/health`
- `/api/v1/tags/normalize`
- `/api/v1/accessibility/analyze-batch`
- `/api/v1/explanations/accessibility`
- 룰 기반 점수 계산
- PostGIS 기반 GIS feature 조회 구조
- `public_accessibility_gis_feature` 읽기 구조
- 버스정류장/횡단보도/신호등/지하철 출입구 리프트 근접 검색 구조
- `evidence_items.record_id` 구조
- positive_factors/risk_factors 구조
- 데이터 부족 시 확인 필요 문구
- rule fallback 설명 생성
- explanation_version
- used_llm=false

아직 포함되지 않은 기능 또는 Spring 구현 의존 기능:

- 운영 기준 Spring의 `public_accessibility_gis_feature` 생성/갱신 구현
- 실제 전체 공공데이터 운영 동기화 완료
- 저상버스 운행 여부 직접 판정
- 사업장 내부 장애인 화장실/자동문/근무층 직접 판정
- 실제 보행 경로 탐색
- 실시간 교통 정보
- 실시간 시설 고장 정보
- 실제 LLM API 호출
- 운영 배포 설정
- Spring WebClient/RestClient 실제 구현

---

## 15. 다음 작업

추천 작업은 다음과 같다.

1. Spring DTO 작성
2. Spring FastAPI Client 작성
3. Spring의 `public_accessibility_gis_feature` 생성/갱신 구현
4. FastAPI 공통 에러 응답 핸들러 유지/보강
5. 분석 결과 저장/캐싱 테이블 설계
6. 설명 결과 저장/캐싱 테이블 설계
7. 운영 배포 설정
