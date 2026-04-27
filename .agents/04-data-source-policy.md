# 04. Data Source Policy

## SourceType 원칙

공공데이터는 SourceType enum을 기준으로 식별한다.

SourceType 이름은 코드, DB, API 응답, 로그에서 일관되게 사용한다.

한글 데이터명은 사용자 표시 또는 문서에는 사용할 수 있지만 내부 식별자로는 SourceType을 우선한다.

## 승인된 동기화 대상 SourceType

현재 승인된 SourceType은 다음과 같다.

- KEPAD_RECRUITMENT
- KEPAD_JOB_CATEGORY
- KEPAD_STANDARD_WORKPLACE
- KEPAD_SUPPORT_AGENCY
- KORAIL_WEEK_PERSON_FACILITIES
- SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT
- TRANSPORT_SUPPORT_CENTER
- RAIL_WHEELCHAIR_LIFT
- RAIL_WHEELCHAIR_LIFT_MOVEMENT
- SEOUL_WHEELCHAIR_LIFT
- SEOUL_SUBWAY_ENTRANCE_LIFT
- SEOUL_WALKING_NETWORK
- NATIONWIDE_BUS_STOP
- NATIONWIDE_TRAFFIC_LIGHT
- NATIONWIDE_CROSSWALK
- VOCATIONAL_TRAINING
- JOBSEEKER_COMPETENCY_PROGRAM

## MVP 우선 데이터

MVP에서 우선 활용할 데이터는 다음과 같다.

- KEPAD_RECRUITMENT
- KEPAD_JOB_CATEGORY
- KEPAD_STANDARD_WORKPLACE
- KEPAD_SUPPORT_AGENCY
- KORAIL_WEEK_PERSON_FACILITIES
- SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT
- RAIL_WHEELCHAIR_LIFT
- RAIL_WHEELCHAIR_LIFT_MOVEMENT
- SEOUL_SUBWAY_ENTRANCE_LIFT
- SEOUL_WALKING_NETWORK
- NATIONWIDE_BUS_STOP
- NATIONWIDE_TRAFFIC_LIGHT
- NATIONWIDE_CROSSWALK

훈련 추천 관련 데이터는 후순위 기능으로 둔다.

- VOCATIONAL_TRAINING
- JOBSEEKER_COMPETENCY_PROGRAM

## 원본 저장 방식

공공데이터 원본 저장 방식은 다음 정책을 따른다.

- public_data_record에 원본 payload JSON 저장
- public_data_record에 source_type 저장
- public_data_record에 external_id 저장
- public_data_record에 hash 저장
- public_data_record에 collected_at 저장
- public_data_record_field에 payload를 field_path 단위로 펼쳐 저장
- 동일 데이터는 hash 비교로 변경 여부 판단
- 변경된 데이터만 payload와 field를 재저장
- 동일 데이터는 수집시각만 갱신
- 전체 페이지 수집 후 API 결과에 없는 기존 데이터는 삭제 처리

원본 payload를 잃지 않는 것을 우선한다.

정규화 테이블은 조회 성능과 분석 편의를 위해 별도로 둘 수 있다.

## 주요 공공데이터 사용 방향

### KEPAD_RECRUITMENT

장애인 구인 공고의 기본 데이터로 사용한다.

주요 활용 항목은 다음과 같다.

- 사업장명
- 사업장주소
- 고용형태
- 모집직종
- 요구경력
- 요구학력
- 임금
- 작업환경 관련 항목

### KEPAD_JOB_CATEGORY

직무 분류와 직무 설명 보강에 사용한다.

주요 활용 항목은 다음과 같다.

- 직종코드
- 직종명
- 수행업무
- 유사직무명
- 직무개발 tip

### KEPAD_STANDARD_WORKPLACE

장애인 표준사업장 여부 확인에 사용한다.

주요 활용 항목은 다음과 같다.

- 기업명
- 소재지 주소
- 인증일자
- 인증유형
- 주요상품

### KEPAD_SUPPORT_AGENCY

근로지원인 수행기관 안내에 사용한다.

주요 활용 항목은 다음과 같다.

- 수행기관명
- 수행기관 주소
- 수행기관 전화번호
- 시도구분

### NATIONWIDE_CROSSWALK

횡단보도 접근성 분석에 사용한다.

주요 활용 항목은 다음과 같다.

- 위도
- 경도
- 보행자신호등 유무
- 보행자작동신호기 유무
- 음향신호기 설치 여부
- 보도턱낮춤 여부
- 점자블록 유무
- 녹색신호시간
- 적색신호시간

### NATIONWIDE_TRAFFIC_LIGHT

시각장애인 이동 지원 요소 분석에 사용한다.

주요 활용 항목은 다음과 같다.

- 위도
- 경도
- 보행자작동신호기 유무
- 시각장애인용 음향신호기 유무
- 잔여시간표시기 유무

### NATIONWIDE_BUS_STOP

대중교통 접근성 분석에 사용한다.

주요 활용 항목은 다음과 같다.

- 정류장 ID
- 정류장명
- 위도
- 경도
- 도시명
- 관리도시명

### SEOUL_WALKING_NETWORK

서울 지역 보행 네트워크 분석에 사용한다.

주요 활용 항목은 다음과 같다.

- 노드 WKT
- 링크 WKT
- 링크 길이
- 횡단보도 여부
- 육교 여부
- 지하철 네트워크 여부
- 공원, 녹지 여부
- 건물내 여부

### SEOUL_SUBWAY_ENTRANCE_LIFT

지하철 출입구 리프트 위치 분석에 사용한다.

주요 활용 항목은 다음과 같다.

- 노드 WKT
- 지하철역 코드
- 지하철역명
- 시군구명
- 읍면동명

## CSV export 스크립트

CSV 내보내기 스크립트는 공공데이터 수집 검증, 샘플 분석, 컬럼 확인, AI/GIS 피처 설계에 사용한다.

기준 파일은 다음과 같다.

- scripts/export_public_data_to_csv.py

키 주입 파일은 다음과 같다.

- scripts/.env

필요 환경변수는 다음과 같다.

- DATA_GO_KR_SERVICE_KEY
- KRIC_SERVICE_KEY
- SEOUL_OPEN_API_KEY
- KRIC_STATION_CODE_XLSX_PATH
- WORK24_VOCATIONAL_TRAINING_AUTH_KEY
- WORK24_COMPETENCY_AUTH_KEY

CSV 스크립트 정책은 다음과 같다.

- 무데이터 또는 오류 메시지는 CSV 행으로 기록하지 않는다.
- 실행 로그에 요청 URL, 파라미터, 재시도, 감지 건수를 출력한다.
- 특정 데이터명 실행은 한글명과 영문 slug를 모두 지원한다.
- 필요한 라이브러리는 requests, pandas이다.

## 비밀키 관리

다음 값은 절대 Git에 커밋하지 않는다.

- DATA_GO_KR_SERVICE_KEY
- KRIC_SERVICE_KEY
- SEOUL_OPEN_API_KEY
- WORK24 인증키
- DB 비밀번호
- OAuth secret
- LLM 서버 인증키