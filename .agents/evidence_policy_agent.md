# Evidence Policy Agent

## 목적

BridgeWork 접근성 분석 결과에서 `evidence_items`를 생성할 때 사용할 공공데이터 근거 기준을 정리한다.

FastAPI AI/GIS Service는 점수를 직접 설명할 때 반드시 근거 데이터를 함께 제공해야 한다.

## 기본 원칙

- 최종 점수는 룰 기반으로 계산한다.
- LLM은 점수를 직접 결정하지 않는다.
- LLM은 `score_detail`, `positive_factors`, `risk_factors`, `evidence_items`를 바탕으로 설명 문구만 생성한다.
- 공공데이터가 부족한 경우 단정하지 않고 “확인 필요”로 표현한다.
- `evidence_items`에는 가능한 한 `source_type`, `source_name`, `description`, `record_id`를 포함한다.

## 점수 항목별 근거 데이터

### transport_score

사용 데이터:

- `NATIONWIDE_BUS_STOP`
- `SEOUL_SUBWAY_ENTRANCE_LIFT`
- `SEOUL_WALKING_NETWORK`

설명 예시:

- 근무지 주변 버스정류장 N개 확인
- 근무지 주변 지하철역 또는 출입구 정보 확인
- 도보 접근 경로 확인 필요

### station_access_score

사용 데이터:

- `SEOUL_SUBWAY_ENTRANCE_LIFT`
- `SEOUL_WHEELCHAIR_LIFT`
- `SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT`
- `RAIL_WHEELCHAIR_LIFT`
- `RAIL_WHEELCHAIR_LIFT_MOVEMENT`
- `KORAIL_WEEK_PERSON_FACILITIES`

설명 예시:

- 근처 지하철 출입구 엘리베이터 정보 확인
- 휠체어 리프트 정보 확인
- 철도/역사 교통약자 이용시설 확인

### crosswalk_score

사용 데이터:

- `NATIONWIDE_CROSSWALK`
- `NATIONWIDE_TRAFFIC_LIGHT`
- `SEOUL_WALKING_NETWORK`

설명 예시:

- 근무지 주변 횡단보도 N개 확인
- 음향신호기/신호등 정보 확인
- 보행 경로 안전성 확인 필요

### facility_score

사용 데이터:

- `KEPAD_STANDARD_WORKPLACE`
- `KEPAD_RECRUITMENT`
- `KEPAD_SUPPORT_AGENCY`

설명 예시:

- 장애인 표준사업장 여부 확인
- 장애인 우대/전형 공고 여부 확인
- 취업지원기관 연계 가능성 확인

### work_environment_score

사용 데이터:

- `KEPAD_RECRUITMENT`
- `KEPAD_JOB_CATEGORY`

설명 예시:

- 공고의 작업환경 태그 확인
- 직종별 업무환경 특성 확인
- 사용자 선호/기피 업무환경과의 충돌 여부 확인

### risk_penalty

사용 데이터:

- 위 항목 전체
- 공고/사업장 내부 편의시설 정보
- 누락된 필수 접근성 정보

설명 예시:

- 필수 지원 항목 정보가 확인되지 않음
- 장애 유형과 충돌 가능한 업무환경이 포함됨
- 이동 편의시설 정보 확인 필요