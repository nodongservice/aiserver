# FastAPI Internal API Contract

## 목적

Spring Backend가 BridgeWork FastAPI AI/GIS Service를 내부 호출할 때 따르는 scoring v2 계약이다.

기준:

- 기능정의서: `.agents/specification.md`
- Spring DB 구조: `../backend/README.md`
- FastAPI 실제 스키마: `app/schemas/score.py`
- FastAPI 실제 엔드포인트: `app/api/v1/routes_score.py`, `app/api/v1/routes_ai_explanation.py`

## 공통 원칙

- FastAPI는 프론트엔드가 직접 호출하지 않는다.
- 호출 흐름은 `React -> Spring -> FastAPI`다.
- Spring은 선택된 프로필 1개만 FastAPI에 전달한다.
- FastAPI는 Spring DB의 `pd_*` 정규화 테이블을 직접 조회한다.
- 점수 계산은 룰 기반이다.
- LLM은 점수를 직접 결정하지 않는다.
- 데이터가 없으면 확정적으로 단정하지 않고 `unknown`, `추가 확인 필요`, `현재 공공데이터 기준`으로 표현한다.
- 장애 정보, API 키, 토큰은 로그에 남기지 않는다.

## 사용 DB 테이블

### 공고

- `pd_kepad_recruitment`
- 근무지 좌표:
  - `geo_latitude`
  - `geo_longitude`
  - `geo_matched_address`
  - `geo_original_address`

### 표준사업장

- `pd_kepad_standard_workplace`
- 매칭 기준:
  - `comp_name`
  - `address`
  - `comp_cert`
  - `auth_date`
  - `cancel_date`

### 접근성 요약

- `pd_transport_support_center`
- `pd_nationwide_bus_stop`
- `pd_nationwide_crosswalk`
- `pd_nationwide_traffic_light`
- `pd_seoul_subway_entrance_lift`
- `pd_seoul_walking_network`

### 지도 레이어

- `pd_kepad_support_agency`
- 근로지원인 수행기관은 기능정의서 기준 점수 미반영이며 지도 레이어용이다.

## `POST /ai/v1/score/quick`

목적:

- 기능 2. 퀵 맞춤 일자리 추천
- 최신 공고를 조회한 뒤 직무 적합도만 계산한다.

요청:

```json
{
  "profile": {
    "profile_id": 7,
    "user_id": 1,
    "address": "서울특별시 중구 세종대로 110",
    "home_lat": 37.5665,
    "home_lng": 126.978,
    "desired_jobs": ["사무보조"],
    "skills": ["문서작성", "엑셀"],
    "education": "고졸",
    "career": "신입",
    "major": "경영",
    "licenses": ["컴퓨터활용능력"],
    "available_employment_types": ["정규직"],
    "disability_types": ["wheelchair"],
    "disability_severity": "중증",
    "is_registered_disabled": true,
    "required_supports": ["elevator", "accessible_restroom"]
  },
  "limit": 20,
  "offset": 0
}
```

응답:

```json
{
  "results": [
    {
      "job": {
        "job_post_id": 101,
        "company_name": "ABC복지센터",
        "job_title": "사무보조",
        "work_address": "서울특별시 중구 세종대로 110",
        "work_lat": 37.5701,
        "work_lng": 126.9823,
        "employment_type": "정규직",
        "enter_type": "무관",
        "salary_type": "월급",
        "salary": "2300000",
        "term_date": "2026-04-20~2026-04-27",
        "required_career": "신입",
        "required_education": "고졸",
        "required_major": null,
        "required_licenses": "컴퓨터활용능력",
        "environment": {
          "env_both_hands": "양손작업 가능"
        },
        "agency_name": "한국장애인고용공단 서울지역본부",
        "registered_at": "20260417",
        "source_table": "pd_kepad_recruitment",
        "source_id": 101,
        "external_id": "..."
      },
      "job_fit_score": 88,
      "reasons": ["희망 직무와 모집 직종이 겹칩니다."],
      "risk_factors": [],
      "evidence_items": [
        {
          "source_type": "KEPAD_RECRUITMENT",
          "source_name": "한국장애인고용공단 장애인 구인 실시간 현황",
          "description": "한국장애인고용공단 장애인 구인 실시간 현황 공고를 기준으로 계산했습니다.",
          "distance_meters": null,
          "source_table": "pd_kepad_recruitment",
          "record_id": 101,
          "fields": {}
        }
      ]
    }
  ]
}
```

정렬:

- `job_fit_score` 내림차순

## `POST /ai/v1/score/map`

목적:

- 기능 3. 지역 접근성 지도 추천
- 최신 공고와 공공데이터를 조회해 6개 항목 동일 비중 종합 점수를 계산한다.

점수 항목:

- `job_fit_score`
- `work_condition_score`
- `disability_support_score`
- `work_environment_score`
- `company_stability_score`
- `accessibility_score`

총점:

- 6개 항목의 산술 평균
- 0~100 범위로 제한

응답:

```json
{
  "results": [
    {
      "job": {
        "job_post_id": 101,
        "company_name": "ABC복지센터",
        "job_title": "사무보조"
      },
      "score_detail": {
        "job_fit_score": 88,
        "work_condition_score": 70,
        "disability_support_score": 82,
        "work_environment_score": 76,
        "company_stability_score": 84,
        "accessibility_score": 73
      },
      "total_score": 79,
      "reasons": [
        "6개 항목을 동일 비중으로 계산했습니다."
      ],
      "risk_factors": [
        "근무지 주변 접근성 근거 데이터가 부족하여 추가 확인이 필요합니다."
      ],
      "evidence_items": []
    }
  ]
}
```

정렬:

- `total_score` 내림차순

## `POST /ai/v1/explain/recommendation`

목적:

- 이미 계산된 점수와 근거를 쉬운 한국어 추천 설명으로 변환한다.
- MVP 기본 구현은 룰 기반이다.
- LLM을 사용하더라도 점수를 재계산하지 않는다.

요청:

```json
{
  "profile": {},
  "job": {
    "job_post_id": 101,
    "company_name": "ABC복지센터",
    "job_title": "사무보조"
  },
  "total_score": 79,
  "reasons": ["6개 항목을 동일 비중으로 계산했습니다."],
  "risk_factors": ["일부 접근성 정보는 추가 확인이 필요합니다."],
  "evidence_items": []
}
```

응답:

```json
{
  "short_summary": "ABC복지센터의 사무보조 공고는 현재 기준 79점으로 평가되었습니다.",
  "recommendation_reasons": ["6개 항목을 동일 비중으로 계산했습니다."],
  "caution_points": ["일부 접근성 정보는 추가 확인이 필요합니다."],
  "checklist": [
    "실제 근무지 출입구, 엘리베이터, 화장실 접근성을 지원 전 확인하세요."
  ],
  "used_llm": false
}
```
