# FastAPI Internal API Contract

## 목적

이 문서는 Spring Backend가 BridgeWork FastAPI AI/GIS Service를 내부 호출할 때 따라야 하는 현재 계약을 고정한다.

기준:

- 실제 구현 스키마는 `app/schemas/*.py`를 따른다.
- 실제 엔드포인트는 `app/api/v1/routes_*.py`를 따른다.
- 에러 응답 형식은 `app/core/exceptions.py`를 따른다.
- 공공데이터 범위는 `README.md`의 `사용데이터 목록`만 따른다.

---

## 공통 원칙

- FastAPI는 프론트엔드가 직접 호출하지 않는다.
- 호출 흐름은 `Next.js -> Spring -> FastAPI`다.
- 점수 계산은 룰 기반이다.
- LLM은 설명 생성 전용이다.
- README에 없는 데이터는 직접 확정하지 않고 `확인 필요`로 표현한다.
- `X-Request-Id`를 넘기면 에러 응답의 `request_id`에 그대로 반영된다.

---

## 엔드포인트 목록

### `GET /api/v1/gis/nearby-features`

목적:

- 기준 좌표 주변의 접근성 근거 데이터를 디버깅/검증용으로 조회

쿼리 파라미터:

- `lat`: 필수, 기준 위도
- `lng`: 필수, 기준 경도
- `radius`: 선택, meter, 기본값 `500`
- `source_type`: 선택, 특정 SourceType만 조회할 때 사용
- `limit`: 선택, 기본값 `20`

현재 지원하는 `source_type`:

- `NATIONWIDE_BUS_STOP`
- `NATIONWIDE_CROSSWALK`
- `NATIONWIDE_TRAFFIC_LIGHT`
- `SEOUL_SUBWAY_ENTRANCE_LIFT`
- `SEOUL_WHEELCHAIR_LIFT`

응답 스키마:

```json
{
  "lat": 37.5701,
  "lng": 126.9823,
  "radius_meters": 500,
  "source_type": "NATIONWIDE_BUS_STOP",
  "limit": 20,
  "count": 1,
  "items": [
    {
      "record_id": 123,
      "source_type": "NATIONWIDE_BUS_STOP",
      "source_name": "전국 버스정류장 위치정보",
      "feature_type": "BUS_STOP",
      "feature_type_name": "버스정류장",
      "external_id": "BUS-001",
      "distance_meters": 180.0,
      "field_map": {
        "feature_type": "BUS_STOP",
        "name": "시청앞"
      }
    }
  ]
}
```

계약 주의사항:

- 이 API는 점수 계산 전 근거 데이터 확인용이다.
- `items`는 거리 오름차순으로 정렬된다.
- 지원하지 않는 `source_type`은 HTTP 400으로 반환한다.

---

### `POST /api/v1/tags/normalize`

목적:

- 화면의 한글 선택값을 FastAPI 내부 분석용 표준 태그로 정규화

요청 스키마:

```json
{
  "user_id": 1,
  "disability_labels": ["지체 - 휠체어"],
  "required_support_labels": [
    "계단 없는 출입 필요",
    "엘리베이터 필요",
    "장애인 화장실 필요"
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
```

응답 스키마:

```json
{
  "disability_types": ["wheelchair"],
  "required_supports": [
    "step_free_access",
    "elevator",
    "accessible_restroom"
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
```

필드 정책:

- `user_id`: 선택
- 라벨 배열 필드: 선택, 기본값 빈 배열
- `transport_preferences`: 선택, 기본값 사용 가능
- 매핑 실패 라벨은 `unknown_labels`에 누적
- 장애 유형 라벨이 비어 있으면 `disability_types=["unknown"]`

---

### `POST /api/v1/accessibility/analyze-batch`

목적:

- 사용자 조건과 공고 후보 목록을 받아 공고별 접근성 분석 수행

요청 스키마:

```json
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
      "prefer_computer_based_work",
      "prefer_document_work",
      "prefer_quiet_environment"
    ],
    "transport_preferences": {
      "prefer_subway": true,
      "prefer_bus": true,
      "prefer_transfer": false,
      "prefer_direct_route": true
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

응답 스키마:

```json
{
  "results": [
    {
      "job_post_id": 101,
      "company_id": 55,
      "accessibility_score": 88,
      "accessibility_grade": "GOOD",
      "score_detail": {
        "transport_score": 20,
        "station_access_score": 20,
        "crosswalk_score": 20,
        "facility_score": 18,
        "work_environment_score": 20,
        "risk_penalty": 0
      },
      "positive_factors": [
        "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다."
      ],
      "risk_factors": [
        "현재 확인된 주요 위험 요인은 없습니다."
      ],
      "evidence_items": [
        {
          "source_type": "NATIONWIDE_BUS_STOP",
          "source_name": "전국 버스정류장 위치정보",
          "description": "근무지 반경 내 버스정류장 4개가 확인됩니다.",
          "distance_meters": 180.0,
          "record_id": null
        }
      ],
      "summary": "현재 데이터 기준 접근성 조건이 비교적 양호한 공고입니다."
    }
  ]
}
```

필드 정책:

- `user.user_id`, `home_lat`, `home_lng`, `commute_limit_minutes`: 필수
- `disability_types`, `required_supports`, `work_environment_preferences`: 선택, 기본값 빈 배열
- `transport_preferences`: 선택, 기본값 사용 가능
- `jobs`: 1개 이상 권장
- `work_address`, `is_standard_workplace`, `is_disability_friendly_post`: 선택
- `work_environment_tags`, `support_tags`: 선택, 기본값 빈 배열
- `evidence_items.record_id`: 근거 레코드가 연결되면 정수, 아니면 `null`

계약 주의사항:

- `transport_preferences.prefer_direct_route`는 현재 점수 계산에서 직접 사용하지 않더라도 계약 필드로 유지한다.
- `company_name`, `job_title`은 분석 결과 응답에 재반환하지 않는다. Spring이 원본 공고 후보와 결합해 사용한다.
- 현재 구현 엔드포인트는 `analyze-one`이 아니라 `analyze-batch`다.

---

### `POST /api/v1/explanations/accessibility`

목적:

- 분석 결과를 사용자용 설명으로 변환

요청 스키마:

```json
{
  "user_id": 1,
  "job_post_id": 101,
  "company_name": "ABC복지센터",
  "job_title": "사무보조",
  "accessibility_score": 88,
  "accessibility_grade": "GOOD",
  "score_detail": {
    "transport_score": 20,
    "station_access_score": 20,
    "crosswalk_score": 20,
    "facility_score": 18,
    "work_environment_score": 20,
    "risk_penalty": 0
  },
  "positive_factors": [
    "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다."
  ],
  "risk_factors": [
    "현재 확인된 주요 위험 요인은 없습니다."
  ],
  "evidence_items": [
    {
      "source_type": "NATIONWIDE_BUS_STOP",
      "source_name": "전국 버스정류장 위치정보",
      "description": "근무지 반경 내 버스정류장 4개가 확인됩니다.",
      "distance_meters": 180.0,
      "record_id": null
    }
  ]
}
```

응답 스키마:

```json
{
  "explanation_version": "v1-rule-fallback",
  "short_summary": "사무보조 공고는 현재 조건 기준 접근성이 비교적 양호합니다.",
  "detail_explanation": "ABC복지센터의 사무보조 공고는 접근성 점수 88점, 등급 GOOD으로 분석되었습니다.",
  "check_points": [
    "면접 또는 지원 전 실제 근무지 접근성을 한 번 더 확인하는 것이 좋습니다."
  ],
  "used_llm": false
}
```

필드 정책:

- `user_id`: 선택
- 나머지 핵심 분석 필드: 필수
- 설명 API는 점수/등급/근거를 바꾸지 않는다
- 현재 구현은 rule fallback만 사용한다

---

## 공통 에러 응답 형식

모든 에러 응답은 아래 구조를 따른다.

```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "요청 값 검증에 실패했습니다.",
  "detail": [],
  "request_id": "external-request-id"
}
```

대표 `error_code`:

- `VALIDATION_ERROR`
- `NOT_FOUND`
- `UNAUTHORIZED_INTERNAL_REQUEST`
- `FORBIDDEN_INTERNAL_REQUEST`
- `HTTP_ERROR`
- `AI_SERVICE_INTERNAL_ERROR`

에러 정책:

- 검증 실패: HTTP 422
- 존재하지 않는 경로: HTTP 404
- 예상하지 못한 서버 오류: HTTP 500
- `request_id`는 `X-Request-Id` 헤더를 그대로 반영한다.

---

## Spring 연동 체크리스트

- `tags/normalize` 응답을 그대로 저장하거나 후속 분석 요청에 재사용 가능
- `analyze-batch` 요청에는 정규화된 태그만 넣는다
- `analyze-batch` 응답의 공고 제목/회사명은 Spring 원본 데이터와 조합해 사용한다
- 설명 캐시 키에는 `job_post_id`, `user_id`, `scoring_version`, `explanation_version`을 포함하는 것을 권장한다
- README에 없는 데이터는 프론트 문구에서도 확정 표현을 피한다
