# 06. DB and GIS Policy

## DB 기본 원칙

별도의 DB 엔진을 분리하지 않는다.

하나의 PostgreSQL에 PostGIS 확장을 적용하여 Spring Backend와 FastAPI AI/GIS Service가 함께 사용한다.

schema를 분리하여 소유권과 책임을 명확히 한다.

## 권장 schema 구조

권장 schema는 다음과 같다.

- app 또는 public schema
- gis schema
- ai schema

## app 또는 public schema

서비스 핵심 데이터를 저장한다.

주요 테이블은 다음과 같다.

- users
- resumes
- job_posts
- companies
- applications
- recommendation_results

이 영역은 Spring Backend가 주로 관리한다.

FastAPI는 임의로 수정하지 않는다.

## gis schema

공간 데이터와 접근성 공공데이터를 저장한다.

주요 테이블은 다음과 같다.

- crosswalks
- traffic_lights
- bus_stops
- subway_stations
- subway_exits
- elevators
- wheelchair_lifts
- walking_network_nodes
- walking_network_links
- transport_support_centers
- accessibility_facilities
- company_accessibility_features

## ai schema

AI 분석 결과와 생성 로그를 저장한다.

주요 테이블은 다음과 같다.

- accessibility_analysis_logs
- llm_generation_logs
- user_accessibility_tags
- job_accessibility_scores
- company_accessibility_scores

## FastAPI DB 접근 원칙

FastAPI는 다음 데이터를 읽을 수 있다.

- 공고 후보 정보
- 사업장 위치 정보
- gis schema의 공간 데이터
- ai schema의 분석 결과

FastAPI가 직접 수정할 수 있는 영역은 다음과 같다.

- ai schema
- FastAPI 소유의 분석 캐시
- FastAPI 소유의 로그 테이블

Spring 소유 테이블은 임의 수정하지 않는다.

## PostGIS 원칙

좌표계는 기본적으로 WGS84를 사용한다.

기본 SRID는 4326이다.

거리 계산은 단순 위경도 차이로 처리하지 않는다.

거리 계산 시 다음 중 하나를 사용한다.

- geography 타입 변환
- ST_DWithin
- ST_Distance
- 적절한 projection 변환

## 공간 인덱스

공간 검색 대상 테이블에는 GIST index를 고려한다.

권장 인덱스는 다음과 같다.

- geometry GIST index
- source_type index
- external_id unique index
- collected_at index
- region code index
- company_id index
- job_post_id index

## MVP 공간 질의

MVP에서 우선 구현할 공간 질의는 다음과 같다.

- 특정 사업장 반경 내 버스정류장 조회
- 특정 사업장 반경 내 지하철역 또는 출입구 조회
- 특정 사업장 반경 내 횡단보도 조회
- 특정 사업장 반경 내 신호등 조회
- 특정 사업장 반경 내 휠체어 리프트 조회
- 특정 사업장 반경 내 교통약자 편의시설 조회
- 보도턱낮춤 횡단보도 비율 계산
- 점자블록 횡단보도 비율 계산
- 음향신호기 보유 신호등 또는 횡단보도 여부 계산

## 접근성 피처 예시

사업장 기준 피처는 다음과 같다.

- nearest_bus_stop_distance_m
- bus_stop_count_500m
- nearest_subway_entrance_distance_m
- subway_entrance_lift_count_500m
- wheelchair_lift_count_500m
- crosswalk_count_300m
- curb_cut_crosswalk_ratio_300m
- tactile_block_crosswalk_ratio_300m
- audible_signal_count_300m
- traffic_light_count_300m
- transport_support_center_distance_m
- is_standard_workplace
- support_agency_nearby

## unknown 처리

데이터가 없거나 확인할 수 없는 경우 0점으로 단정하지 않는다.

다음처럼 분리한다.

- true
- false
- unknown

예시는 다음과 같다.

- 엘리베이터 정보 있음: true
- 엘리베이터 없음으로 확인됨: false
- 데이터 없음: unknown

사용자에게는 unknown을 추가 확인 필요로 표시한다.

## 점수 계산 원칙

접근성 점수는 확정 판정이 아니라 참고 지표이다.

점수는 다음 항목으로 나눌 수 있다.

- 대중교통 접근성
- 휠체어 이동 접근성
- 시각장애 이동 지원
- 청각장애 업무환경 적합성
- 사업장 지원 정보
- 데이터 신뢰도

LLM이 점수를 생성하지 않는다.

점수 계산은 deterministic한 Python 코드에서 수행한다.

## 라우팅 엔진

추후 경로 추천을 위해 다음 엔진을 검토한다.

- Valhalla
- GraphHopper
- OSRM

MVP에서는 실제 라우팅 엔진 도입보다 공공데이터 기반 주변 접근성 피처 계산을 우선한다.