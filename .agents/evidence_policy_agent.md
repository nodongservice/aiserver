# Evidence Policy Agent

## 목적

이 문서는 BridgeWork 접근성 분석 결과에서 `evidence_items`를 생성할 때 사용할 공공데이터 근거 기준을 정리한다.

이 문서의 데이터 범위는 반드시 [README.md](/Users/emfpdlzj/Desktop/nodong/aiserver/README.md:75)의 `사용데이터 목록`만 따른다.

FastAPI AI/GIS Service는 점수를 직접 설명할 때 반드시 근거 데이터를 함께 제공해야 한다.

---

## 데이터 범위

`evidence_items`에 사용할 수 있는 `source_type`은 다음 17개로 한정한다.

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

위 목록에 없는 데이터는 점수 근거나 설명 근거로 직접 사용하지 않는다.

예:

- 저상버스 실제 운행 여부
- 건물 내부 자동문
- 건물 내부 장애인 화장실
- 실시간 시설 고장 여부
- 실시간 대중교통 도착 정보
- 별도 장애인 편의시설 표준데이터

이런 항목은 데이터가 없으면 `확인 필요`로 표현한다.

---

## 기본 원칙

- 최종 점수는 룰 기반으로 계산한다.
- LLM은 점수를 직접 결정하지 않는다.
- LLM은 `score_detail`, `positive_factors`, `risk_factors`, `evidence_items`를 바탕으로 설명 문구만 생성한다.
- 공공데이터가 부족한 경우 단정하지 않고 `확인 필요`로 표현한다.
- `evidence_items`에는 가능한 한 `source_type`, `source_name`, `description`, `record_id`를 포함한다.
- `source_name`은 README 사용데이터 목록의 데이터명을 기준으로 유지한다.

---

## 점수 항목별 근거 데이터

### transport_score

직접 근거로 사용할 수 있는 데이터:

- `NATIONWIDE_BUS_STOP`

보조 설명 또는 향후 확장 근거:

- `SEOUL_WALKING_NETWORK`

설명 예시:

- 근무지 주변 버스정류장 N개 확인
- 가장 가까운 버스정류장 거리 확인
- 저상버스 운행 여부는 현재 데이터만으로 확인 어려움

주의:

- `SEOUL_SUBWAY_ENTRANCE_LIFT`는 `station_access_score`의 핵심 근거이지 `transport_score`의 직접 근거로 보지 않는다.

### station_access_score

사용 데이터:

- `SEOUL_SUBWAY_ENTRANCE_LIFT`
- `SEOUL_WHEELCHAIR_LIFT`
- `SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT`
- `RAIL_WHEELCHAIR_LIFT`
- `RAIL_WHEELCHAIR_LIFT_MOVEMENT`
- `KORAIL_WEEK_PERSON_FACILITIES`

설명 예시:

- 근처 지하철 출입구 리프트 정보 확인
- 휠체어 리프트 정보 확인
- 철도/역사 교통약자 편의시설 확인

### crosswalk_score

직접 근거로 사용할 수 있는 데이터:

- `NATIONWIDE_CROSSWALK`
- `NATIONWIDE_TRAFFIC_LIGHT`

보조 설명 또는 향후 확장 근거:

- `SEOUL_WALKING_NETWORK`

설명 예시:

- 근무지 주변 횡단보도 N개 확인
- 음향신호기, 보행자작동신호기, 잔여시간표시기 정보 확인
- 보행 네트워크 상세 경로 정보는 향후 확장 가능

### facility_score

사용 데이터:

- `KEPAD_STANDARD_WORKPLACE`
- `KEPAD_RECRUITMENT`
- `KEPAD_SUPPORT_AGENCY`
- `KORAIL_WEEK_PERSON_FACILITIES`
- `TRANSPORT_SUPPORT_CENTER`

설명 예시:

- 장애인 표준사업장 여부 확인
- 장애인 우대/전형 공고 여부 확인
- 근로지원인 수행기관 또는 교통약자 이동지원센터 정보 확인
- 역사 편의시설 정보 확인

### work_environment_score

사용 데이터:

- `KEPAD_RECRUITMENT`
- `KEPAD_JOB_CATEGORY`

설명 예시:

- 공고의 작업환경 태그 확인
- 직종 분류 정보 확인
- 사용자 선호/기피 업무환경과의 충돌 여부 확인

### risk_penalty

사용 데이터:

- 위 항목 전체
- 누락된 필수 접근성 정보

설명 예시:

- 필수 지원 항목 정보가 확인되지 않음
- 장애 유형과 충돌 가능한 업무환경이 포함됨
- 이동 편의시설 정보 확인 필요
- README 사용데이터 목록에 없는 항목은 현장 확인 필요

---

## evidence_items 작성 기준

권장 예시:

- `NATIONWIDE_BUS_STOP`: 반경 500m 이내 버스정류장 N개 확인
- `NATIONWIDE_CROSSWALK`: 반경 500m 이내 횡단보도와 보행 안전 속성 확인
- `NATIONWIDE_TRAFFIC_LIGHT`: 음향신호기 또는 보행자작동신호기 정보 확인
- `SEOUL_SUBWAY_ENTRANCE_LIFT`: 지하철 출입구 리프트 위치 정보 확인
- `SEOUL_WHEELCHAIR_LIFT`: 휠체어 리프트 설치 정보 확인
- `KORAIL_WEEK_PERSON_FACILITIES`: 역사 교통약자 편의시설 정보 확인
- `KEPAD_STANDARD_WORKPLACE`: 장애인 표준사업장 여부 확인
- `KEPAD_RECRUITMENT`: 장애인 우대/전형 또는 업무환경 정보 확인

지양 예시:

- README에 없는 시설을 근거처럼 작성
- `접근 가능`, `이용 가능`처럼 현장 확인 없이 단정하는 문구
- 장애 유형만 보고 적합/부적합을 단정하는 문구
