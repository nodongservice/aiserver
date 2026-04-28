# PostGIS 공간 데이터 설계 가이드

## 1. 목적

이 문서는 BridgeWork FastAPI AI/GIS Service에서 PostGIS 기반 근접 검색을 수행하기 위한 공간 데이터 설계 기준을 정의한다.

현재 Spring Backend는 공공데이터 원본을 `public_data_record`, `public_data_record_field`에 저장한다.

FastAPI는 이 데이터를 읽어 접근성 분석에 활용한다.

Phase 23의 목표는 다음과 같다.

- 어떤 공공데이터가 공간 검색 대상인지 분류한다.
- 어떤 SourceType에 위도/경도 또는 WKT가 있는지 정리한다.
- PostGIS 전용 가공 테이블 구조를 설계한다.
- 추후 `ST_DWithin`, `ST_DistanceSphere`, `ST_Intersects` 기반 검색으로 교체할 수 있게 한다.

---

## 2. 현재 저장 구조

Spring은 공공데이터를 다음 구조로 저장한다.

### public_data_record

원본 공공데이터 레코드 단위 저장 테이블이다.

저장 정보:

- 원본 payload JSON
- payload hash
- external_id
- source_type
- 수집 시각
- 활성 여부

### public_data_record_field

원본 payload를 `field_path` 단위로 펼쳐 저장한 테이블이다.

예시:

| record_id | source_type | field_path | field_value |
|---:|---|---|---|
| 1 | NATIONWIDE_BUS_STOP | GPS_LATI | 37.5665 |
| 1 | NATIONWIDE_BUS_STOP | GPS_LONG | 126.9780 |
| 2 | NATIONWIDE_CROSSWALK | latitude | 37.5701 |
| 2 | NATIONWIDE_CROSSWALK | longitude | 126.9823 |

이 구조는 원본 보존과 일반 검색에는 적합하지만, 대량 공간 검색에는 비효율적이다.

따라서 PostGIS 기반 검색을 위해 별도 가공 테이블을 둔다.

---

## 3. 설계 원칙

### 3.1 원본 테이블과 GIS 가공 테이블을 분리한다

`public_data_record`는 원본 보존용이다.

`public_accessibility_gis_feature`는 공간 검색용 가공 테이블이다.

이렇게 분리하는 이유:

- 원본 payload 구조가 SourceType마다 다르다.
- 공간 검색에는 geometry/geography 컬럼과 인덱스가 필요하다.
- 원본 필드 구조를 직접 쿼리하면 성능이 낮다.
- GIS 분석 로직은 정규화된 테이블을 보는 편이 안정적이다.

### 3.2 FastAPI는 기본적으로 읽기 전용이다

MVP에서는 Spring이 원본 동기화를 담당한다.

GIS 가공 테이블 생성/갱신 주체는 둘 중 하나로 정할 수 있다.

1. Spring이 원본 저장 후 GIS feature까지 생성
2. FastAPI가 읽기용 원본을 바탕으로 별도 batch에서 GIS feature 생성

현재 추천은 1번이다.

Spring이 공공데이터 동기화 후 `public_accessibility_gis_feature`까지 생성하면, FastAPI는 읽기만 하면 된다.

다만 MVP에서는 FastAPI에서 임시 가공 API를 만들어도 된다.

### 3.3 좌표계는 WGS84, SRID 4326을 기본으로 한다

대부분 공공데이터의 위도/경도는 WGS84 좌표계로 제공된다.

기본 geometry는 다음 기준을 사용한다.

- geometry type: POINT, LINESTRING, MULTILINESTRING 등
- SRID: 4326
- 거리 검색용 geography 컬럼 또는 geography cast 사용

---

## 4. 공간 검색 대상 SourceType 분류

### 4.1 위도/경도가 명확한 SourceType

아래 데이터는 위도/경도 필드가 명확하므로 POINT geometry를 만들 수 있다.

| SourceType | 위도 필드 | 경도 필드 | GIS 활용 |
|---|---|---|---|
| NATIONWIDE_BUS_STOP | GPS_LATI | GPS_LONG | 근처 버스정류장 검색 |
| NATIONWIDE_CROSSWALK | latitude | longitude | 근처 횡단보도 검색 |
| NATIONWIDE_TRAFFIC_LIGHT | latitude | longitude | 근처 신호등/음향신호기 검색 |
| TRANSPORT_SUPPORT_CENTER | LATITUDE | LONGITUDE | 근처 교통약자 이동지원센터 검색 |

### 4.2 WKT가 제공되는 SourceType

아래 데이터는 WKT 필드가 있으므로 `ST_GeomFromText`로 geometry를 만들 수 있다.

| SourceType | WKT 필드 | geometry 유형 | GIS 활용 |
|---|---|---|---|
| SEOUL_SUBWAY_ENTRANCE_LIFT | NODE_WKT | POINT 예상 | 지하철 출입구 리프트 위치 검색 |
| SEOUL_WALKING_NETWORK | NODE_WKT | POINT 예상 | 보행 네트워크 노드 |
| SEOUL_WALKING_NETWORK | LNKG_WKT | LINESTRING 예상 | 보행 네트워크 링크 |

### 4.3 좌표가 직접 없는 SourceType

아래 데이터는 주소, 역명, 코드 중심이므로 별도 보강이 필요하다.

| SourceType | 주요 위치 정보 | 보강 방식 |
|---|---|---|
| KEPAD_RECRUITMENT | compAddr | 주소 지오코딩 필요 |
| KEPAD_STANDARD_WORKPLACE | address | 주소 지오코딩 필요 |
| KEPAD_SUPPORT_AGENCY | excInstnAddr | 주소 지오코딩 필요 |
| KORAIL_WEEK_PERSON_FACILITIES | stn_cd, stn_nm | 역 코드/역 좌표 매핑 필요 |
| SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT | stnCd, stnNm, vcntEntrcNo | 역/출입구 좌표 매핑 필요 |
| RAIL_WHEELCHAIR_LIFT | stinCd, exitNo | 역/출입구 좌표 매핑 필요 |
| RAIL_WHEELCHAIR_LIFT_MOVEMENT | stinCd | 역 좌표 매핑 필요 |
| SEOUL_WHEELCHAIR_LIFT | STATION NAME, ENTRANCE NUMBER | 역/출입구 좌표 매핑 필요 |
| VOCATIONAL_TRAINING | ADDRESS | 주소 지오코딩 필요 |
| JOBSEEKER_COMPETENCY_PROGRAM | openPlcCont | 주소/장소명 지오코딩 필요 |

---

## 5. GIS 가공 테이블 설계

### 5.1 public_accessibility_gis_feature

공공데이터 원본 레코드 중 접근성 분석에 사용할 수 있는 공간 데이터를 정규화한 테이블이다.

권장 컬럼:

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | bigint | PK |
| public_data_record_id | bigint | public_data_record.id |
| source_type | varchar(100) | SourceType |
| feature_type | varchar(100) | BUS_STOP, CROSSWALK, TRAFFIC_LIGHT 등 |
| name | varchar(255) | 시설명 또는 장소명 |
| address | text | 주소 |
| latitude | double precision | 위도 |
| longitude | double precision | 경도 |
| geom | geometry(Geometry, 4326) | PostGIS geometry |
| geog | geography(Geometry, 4326) | 거리 검색용 geography |
| properties | jsonb | 원본 중 분석에 필요한 속성 |
| is_active | boolean | 활성 여부 |
| created_at | timestamp | 생성 시각 |
| updated_at | timestamp | 수정 시각 |

### feature_type 예시

| feature_type | 설명 |
|---|---|
| BUS_STOP | 버스정류장 |
| CROSSWALK | 횡단보도 |
| TRAFFIC_LIGHT | 신호등 |
| AUDIBLE_SIGNAL | 음향신호기 |
| SUBWAY_ENTRANCE_LIFT | 지하철 출입구 리프트 |
| WHEELCHAIR_LIFT | 휠체어 리프트 |
| ACCESSIBLE_RESTROOM | 장애인 화장실 |
| STEP_FREE_ACCESS | 계단 없는 접근 |
| TRANSPORT_SUPPORT_CENTER | 교통약자 이동지원센터 |
| WALKING_NODE | 보행 네트워크 노드 |
| WALKING_LINK | 보행 네트워크 링크 |

---

## 6. DDL 초안

운영에서는 Spring migration 또는 별도 migration 도구로 관리한다.

MVP 기준 DDL 초안은 다음과 같다.

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

    CREATE INDEX IF NOT EXISTS idx_accessibility_gis_geom
    ON public_accessibility_gis_feature
    USING GIST (geom);

주의:

- `geog`는 meter 단위 거리 검색에 유리하다.
- `geom`은 공간 연산과 WKT 원형 보존에 유리하다.
- POINT만 저장할 거면 `geometry(Point, 4326)`로 제한할 수 있다.
- 보행 네트워크 LINESTRING까지 고려하면 `geometry(Geometry, 4326)`이 더 유연하다.

---

## 7. SourceType별 feature 변환 규칙

### 7.1 NATIONWIDE_BUS_STOP

입력 필드:

- NODE_ID
- NODE_NM
- GPS_LATI
- GPS_LONG
- CITY_NAME
- ADMIN_NM

변환:

| GIS 컬럼 | 값 |
|---|---|
| public_data_record_id | public_data_record.id |
| source_type | NATIONWIDE_BUS_STOP |
| feature_type | BUS_STOP |
| name | NODE_NM |
| latitude | GPS_LATI |
| longitude | GPS_LONG |
| geom | ST_SetSRID(ST_MakePoint(GPS_LONG, GPS_LATI), 4326) |
| geog | geom::geography |
| properties | NODE_ID, NODE_MOBILE_ID, CITY_NAME, ADMIN_NM |

### 7.2 NATIONWIDE_CROSSWALK

입력 필드:

- crslkManageNo
- latitude
- longitude
- rdnmadr
- lnmadr
- tfclghtYn
- fnctngSgngnrYn
- sondSgngnrYn
- ftpthLowerYn
- brllBlckYn

변환:

| GIS 컬럼 | 값 |
|---|---|
| source_type | NATIONWIDE_CROSSWALK |
| feature_type | CROSSWALK |
| name | crslkManageNo |
| address | rdnmadr 또는 lnmadr |
| latitude | latitude |
| longitude | longitude |
| geom | ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) |
| geog | geom::geography |
| properties | 신호등/음향신호기/턱낮춤/점자블록 여부 |

### 7.3 NATIONWIDE_TRAFFIC_LIGHT

입력 필드:

- tfclghtManageNo
- latitude
- longitude
- tfclghtSe
- sondSgngnrYn
- fnctngSgngnrYn
- remndrIdctYn

변환:

| GIS 컬럼 | 값 |
|---|---|
| source_type | NATIONWIDE_TRAFFIC_LIGHT |
| feature_type | TRAFFIC_LIGHT 또는 AUDIBLE_SIGNAL |
| name | tfclghtManageNo |
| latitude | latitude |
| longitude | longitude |
| geom | ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) |
| geog | geom::geography |
| properties | 신호등 구분, 음향신호기 여부, 잔여시간표시 여부 |

sondSgngnrYn이 Y인 경우 접근성 요인으로 더 강하게 활용할 수 있다.

### 7.4 SEOUL_SUBWAY_ENTRANCE_LIFT

입력 필드:

- NODE_WKT
- NODE_ID
- SBWY_STN_CD
- SBWY_STN_NM
- SGG_NM
- EMD_NM

변환:

| GIS 컬럼 | 값 |
|---|---|
| source_type | SEOUL_SUBWAY_ENTRANCE_LIFT |
| feature_type | SUBWAY_ENTRANCE_LIFT |
| name | SBWY_STN_NM |
| geom | ST_SetSRID(ST_GeomFromText(NODE_WKT), 4326) |
| geog | geom::geography |
| properties | NODE_ID, 역코드, 역명, 자치구, 행정동 |

### 7.5 SEOUL_WALKING_NETWORK

입력 필드:

- NODE_WKT
- LNKG_WKT
- NODE_ID
- LNKG_ID
- LNKG_LEN
- CRSWK
- BRG
- TNL
- OVRP
- PARK
- BLDG

변환:

| GIS 컬럼 | 값 |
|---|---|
| source_type | SEOUL_WALKING_NETWORK |
| feature_type | WALKING_NODE 또는 WALKING_LINK |
| geom | NODE_WKT 또는 LNKG_WKT |
| geog | geom::geography |
| properties | 링크 길이, 횡단보도 여부, 교량, 터널, 육교, 공원, 건물내 여부 |

주의:

- NODE_WKT는 POINT일 가능성이 높다.
- LNKG_WKT는 LINESTRING일 가능성이 높다.
- 보행 네트워크는 단순 반경 검색보다 경로 분석에 활용될 수 있으므로 MVP에서는 후순위로 둔다.

### 7.6 TRANSPORT_SUPPORT_CENTER

입력 필드:

- TFCWKER_MVMN_CNTER_NM
- RDNMADR
- LNMADR
- LATITUDE
- LONGITUDE
- RCEPT_PHONE_NUMBER
- APP_SVC_NM

변환:

| GIS 컬럼 | 값 |
|---|---|
| source_type | TRANSPORT_SUPPORT_CENTER |
| feature_type | TRANSPORT_SUPPORT_CENTER |
| name | TFCWKER_MVMN_CNTER_NM |
| address | RDNMADR 또는 LNMADR |
| latitude | LATITUDE |
| longitude | LONGITUDE |
| geom | ST_SetSRID(ST_MakePoint(LONGITUDE, LATITUDE), 4326) |
| geog | geom::geography |
| properties | 예약 전화번호, 앱서비스명, 운영시간, 이용대상 |

---

## 8. 좌표가 없는 데이터의 처리 기준

좌표가 없는 데이터는 바로 `public_accessibility_gis_feature`에 넣지 않는다.

먼저 다음 중 하나의 보강 과정이 필요하다.

### 8.1 주소 지오코딩 필요

대상:

- KEPAD_RECRUITMENT
- KEPAD_STANDARD_WORKPLACE
- KEPAD_SUPPORT_AGENCY
- VOCATIONAL_TRAINING
- JOBSEEKER_COMPETENCY_PROGRAM

처리 방식:

1. 주소 필드를 추출한다.
2. 주소 정규화를 수행한다.
3. 외부 지오코딩 API 또는 내부 주소 좌표 DB를 통해 위도/경도를 얻는다.
4. geocoding_status를 기록한다.
5. 성공한 데이터만 GIS feature로 생성한다.

### 8.2 역/출입구 좌표 매핑 필요

대상:

- KORAIL_WEEK_PERSON_FACILITIES
- SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT
- RAIL_WHEELCHAIR_LIFT
- RAIL_WHEELCHAIR_LIFT_MOVEMENT
- SEOUL_WHEELCHAIR_LIFT

처리 방식:

1. 역코드 또는 역명을 기준으로 역 좌표 테이블과 매핑한다.
2. 출입구 번호가 있으면 출입구 좌표 테이블과 매핑한다.
3. 출입구 좌표가 없으면 역 중심 좌표를 fallback으로 사용한다.
4. 매핑 신뢰도를 properties에 기록한다.

---

## 9. 조회 쿼리 예시

### 9.1 반경 내 버스정류장 조회

    SELECT
        id,
        public_data_record_id,
        source_type,
        feature_type,
        name,
        ST_Distance(
            geog,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
        ) AS distance_meters
    FROM public_accessibility_gis_feature
    WHERE source_type = 'NATIONWIDE_BUS_STOP'
      AND feature_type = 'BUS_STOP'
      AND is_active = TRUE
      AND ST_DWithin(
            geog,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius_meters
          )
    ORDER BY distance_meters ASC
    LIMIT :limit;

### 9.2 반경 내 횡단보도 조회

    SELECT
        id,
        public_data_record_id,
        source_type,
        feature_type,
        name,
        properties,
        ST_Distance(
            geog,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
        ) AS distance_meters
    FROM public_accessibility_gis_feature
    WHERE source_type = 'NATIONWIDE_CROSSWALK'
      AND feature_type = 'CROSSWALK'
      AND is_active = TRUE
      AND ST_DWithin(
            geog,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius_meters
          )
    ORDER BY distance_meters ASC
    LIMIT :limit;

### 9.3 반경 내 지하철 출입구 리프트 조회

    SELECT
        id,
        public_data_record_id,
        source_type,
        feature_type,
        name,
        ST_Distance(
            geog,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
        ) AS distance_meters
    FROM public_accessibility_gis_feature
    WHERE source_type = 'SEOUL_SUBWAY_ENTRANCE_LIFT'
      AND feature_type = 'SUBWAY_ENTRANCE_LIFT'
      AND is_active = TRUE
      AND ST_DWithin(
            geog,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius_meters
          )
    ORDER BY distance_meters ASC
    LIMIT :limit;

---

## 10. FastAPI 모델 방향

FastAPI에서 읽기용 SQLAlchemy 모델을 둘 경우 다음 이름을 권장한다.

- AccessibilityGisFeature

파일 위치:

- app/db/models.py

권장 필드:

- id
- public_data_record_id
- source_type
- feature_type
- name
- address
- latitude
- longitude
- properties
- is_active
- created_at
- updated_at

PostGIS `geometry/geography` 타입은 SQLAlchemy 기본 타입만으로는 다루기 불편하므로 선택지가 있다.

### 선택 A: geoalchemy2 사용

장점:

- geometry/geography 컬럼을 ORM에서 명확히 다룰 수 있다.
- PostGIS 쿼리 작성이 편해진다.

단점:

- 의존성이 추가된다.
- 초기 MVP에서는 약간 과할 수 있다.

### 선택 B: text SQL 사용

장점:

- 의존성 추가 없이 바로 ST_DWithin 쿼리 가능
- 현재 구조에 빠르게 붙일 수 있음

단점:

- ORM 모델과 타입 안정성이 낮다.
- 쿼리 문자열 관리가 필요하다.

MVP 추천은 선택 B다.

즉, 모델에는 일반 컬럼만 두고, 공간 검색은 repository에서 `sqlalchemy.text()` 기반 SQL로 처리한다.

---

## 11. MVP 구현 순서

추천 구현 순서는 다음과 같다.

1. `public_accessibility_gis_feature` 테이블 DDL 작성
2. `AccessibilityGisFeature` 읽기용 모델 추가
3. `gis_feature_repository.py` 추가
4. `find_nearby_gis_features()` 함수 추가
5. Python Haversine 기반 `nearby_public_data_repository.py`와 같은 DTO 반환
6. `gis_repository.py`에서 기존 검색 함수를 PostGIS 기반 repository로 교체
7. 테스트 데이터 insert
8. ST_DWithin 기반 조회 테스트 추가

---

## 12. 주의 사항

### 12.1 좌표 순서

PostGIS에서 `ST_MakePoint`는 경도, 위도 순서다.

올바른 순서:

    ST_MakePoint(longitude, latitude)

잘못된 순서:

    ST_MakePoint(latitude, longitude)

### 12.2 거리 단위

geometry 타입에서 `ST_Distance`는 좌표계 단위로 계산된다.

meter 단위 거리 계산은 geography를 사용한다.

권장:

    geom::geography

또는 geog 컬럼을 별도로 저장한다.

### 12.3 인덱스

반경 검색 성능을 위해 geography 컬럼에 GIST 인덱스를 둔다.

    CREATE INDEX idx_accessibility_gis_geog
    ON public_accessibility_gis_feature
    USING GIST (geog);

### 12.4 데이터 품질

좌표가 없거나 잘못된 데이터는 GIS feature로 만들지 않는다.

처리 상태는 properties 또는 별도 로그에 남긴다.

예시:

- geocoding_status
- coordinate_source
- coordinate_quality
- mapping_confidence

---

## 13. 현재 Phase 결론

현재 BridgeWork의 GIS 검색 구조는 다음 방향이 적합하다.

- 원본 데이터는 `public_data_record`에 유지
- field_path 검색은 보조 수단으로 유지
- 공간 검색은 `public_accessibility_gis_feature`에서 수행
- 좌표/WKT가 명확한 SourceType부터 GIS feature 생성
- 주소/역명 기반 데이터는 후속 보강 후 GIS feature 생성
- FastAPI는 PostGIS 테이블을 읽고 분석에 사용
- evidence_items.record_id는 `public_data_record_id`를 사용