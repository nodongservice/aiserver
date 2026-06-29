# API 테스트용 더미 JSON

이 문서는 Spring 또는 Swagger/Postman에서 FastAPI 내부 API를 수동 테스트할 때 사용할 더미 JSON 예시다.

현재 기능정의서 기준 FastAPI 노출 API:

- `POST /api/v1/score/quick`
- `POST /api/v1/score/map`
- `POST /api/v1/explain/recommendation`

## `POST /api/v1/score/quick`

### Request

```json
{
  "profile": {
    "profile_id": 7,
    "user_id": 1,
    "name": "홍길동",
    "address": "서울특별시 중구 세종대로 110",
    "home_lat": 37.5665,
    "home_lng": 126.978,
    "desired_jobs": ["사무보조", "행정지원"],
    "skills": ["문서작성", "엑셀", "자료정리"],
    "education": "고졸",
    "career": "신입",
    "major": "경영",
    "licenses": ["컴퓨터활용능력"],
    "job_fit_statement": "문서 정리와 행정 보조 업무를 희망합니다.",
    "available_employment_types": ["정규직", "계약직"],
    "desired_salary": 2200000,
    "time_preference": "주간",
    "remote_work": false,
    "disability_types": ["wheelchair"],
    "disability_severity": "중증",
    "is_registered_disabled": true,
    "disability_description": "장시간 서 있거나 계단 이동은 어렵습니다.",
    "assistive_devices": ["휠체어"],
    "required_supports": ["elevator", "accessible_restroom"],
    "mobility_range_km": 15
  },
  "limit": 10,
  "offset": 0
}
```

### Response

```json
{
  "results": [
    {
      "job": {
        "job_post_id": 101,
        "company_name": "한국예술인복지재단",
        "job_title": "행정지원사무원",
        "work_address": "서울특별시 중구 한강대로 416 서울스퀘어 3층",
        "work_lat": 37.554678,
        "work_lng": 126.970606,
        "employment_type": "계약직",
        "enter_type": "무관",
        "salary_type": "월급",
        "salary": "2,300,000",
        "term_date": "2026-04-20~2026-04-27",
        "required_career": "0년0개월",
        "required_education": "무관",
        "required_major": null,
        "required_licenses": "컴퓨터활용능력",
        "environment": {
          "env_both_hands": "양손작업 가능",
          "env_eyesight": "일상적 활동 가능",
          "env_lstn_talk": "듣고 말하기에 어려움 없음",
          "env_hand_work": "손작업 적음",
          "env_lift_power": "드는힘 거의 없음",
          "env_stnd_walk": "앉아서 근무 가능"
        },
        "agency_name": "한국장애인고용공단 서울지역본부",
        "registered_at": "20260417",
        "source_table": "pd_kepad_recruitment",
        "source_id": 101,
        "external_id": "KEPAD_RECRUITMENT-101"
      },
      "job_fit_score": 88,
      "reasons": [
        "희망 직무와 모집 직종이 겹칩니다.",
        "보유 기술/역량이 공고 요건과 일부 일치합니다."
      ],
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

## `POST /api/v1/score/map`

### Request

```json
{
  "profile": {
    "profile_id": 7,
    "user_id": 1,
    "name": "홍길동",
    "address": "서울특별시 중구 세종대로 110",
    "home_lat": 37.5665,
    "home_lng": 126.978,
    "desired_jobs": ["사무보조", "행정지원"],
    "skills": ["문서작성", "엑셀", "자료정리"],
    "education": "고졸",
    "career": "신입",
    "major": "경영",
    "licenses": ["컴퓨터활용능력"],
    "job_fit_statement": "문서 정리와 행정 보조 업무를 희망합니다.",
    "available_employment_types": ["정규직", "계약직"],
    "desired_salary": 2200000,
    "time_preference": "주간",
    "remote_work": false,
    "disability_types": ["wheelchair"],
    "disability_severity": "중증",
    "is_registered_disabled": true,
    "disability_description": "장시간 서 있거나 계단 이동은 어렵습니다.",
    "assistive_devices": ["휠체어"],
    "required_supports": ["elevator", "accessible_restroom"],
    "mobility_range_km": 15
  },
  "limit": 10,
  "offset": 0
}
```

### Response

```json
{
  "results": [
    {
      "job": {
        "job_post_id": 101,
        "company_name": "한국예술인복지재단",
        "job_title": "행정지원사무원",
        "work_address": "서울특별시 중구 한강대로 416 서울스퀘어 3층",
        "work_lat": 37.554678,
        "work_lng": 126.970606,
        "employment_type": "계약직",
        "enter_type": "무관",
        "salary_type": "월급",
        "salary": "2,300,000",
        "term_date": "2026-04-20~2026-04-27",
        "required_career": "0년0개월",
        "required_education": "무관",
        "required_major": null,
        "required_licenses": "컴퓨터활용능력",
        "environment": {
          "env_both_hands": "양손작업 가능",
          "env_eyesight": "일상적 활동 가능",
          "env_lstn_talk": "듣고 말하기에 어려움 없음",
          "env_hand_work": "손작업 적음",
          "env_lift_power": "드는힘 거의 없음",
          "env_stnd_walk": "앉아서 근무 가능"
        },
        "agency_name": "한국장애인고용공단 서울지역본부",
        "registered_at": "20260417",
        "source_table": "pd_kepad_recruitment",
        "source_id": 101,
        "external_id": "KEPAD_RECRUITMENT-101"
      },
      "score_detail": {
        "job_fit_score": 88,
        "work_condition_score": 72,
        "disability_support_score": 83,
        "work_environment_score": 80,
        "company_stability_score": 86,
        "accessibility_score": 74
      },
      "total_score": 81,
      "reasons": [
        "6개 항목을 동일 비중으로 계산했습니다.",
        "직무 적합도 점수가 높습니다.",
        "장애인 표준사업장 데이터와 매칭되어 장애 지원/기업 안정성 점수에 반영했습니다."
      ],
      "risk_factors": [
        "일부 접근성 정보는 현재 공공데이터 기준 추가 확인이 필요합니다."
      ],
      "evidence_items": [
        {
          "source_type": "KEPAD_RECRUITMENT",
          "source_name": "한국장애인고용공단 장애인 구인 실시간 현황",
          "description": "공고 원천 데이터입니다.",
          "distance_meters": null,
          "source_table": "pd_kepad_recruitment",
          "record_id": 101,
          "fields": {}
        },
        {
          "source_type": "KEPAD_STANDARD_WORKPLACE",
          "source_name": "한국장애인고용공단 장애인 표준사업장 정보",
          "description": "장애인 표준사업장 데이터와 매칭됩니다.",
          "distance_meters": null,
          "source_table": "pd_kepad_standard_workplace",
          "record_id": 501,
          "fields": {
            "company_name": "한국예술인복지재단",
            "cert_status": "인증",
            "auth_date": "2026-01-15",
            "cancel_date": null
          }
        },
        {
          "source_type": "NATIONWIDE_BUS_STOP",
          "source_name": "전국 버스정류장 위치정보",
          "description": "근무지 주변 버스정류장 정보가 확인됩니다.",
          "distance_meters": 180.3,
          "source_table": "pd_nationwide_bus_stop",
          "record_id": 9001,
          "fields": {
            "name": "서울역버스환승센터"
          }
        }
      ]
    }
  ]
}
```

## `POST /api/v1/explain/recommendation`

### Request

```json
{
  "profile": {
    "profile_id": 7,
    "user_id": 1,
    "name": "홍길동",
    "address": "서울특별시 중구 세종대로 110",
    "home_lat": 37.5665,
    "home_lng": 126.978,
    "desired_jobs": ["사무보조", "행정지원"],
    "skills": ["문서작성", "엑셀", "자료정리"],
    "education": "고졸",
    "career": "신입",
    "available_employment_types": ["정규직", "계약직"],
    "disability_types": ["wheelchair"],
    "disability_severity": "중증",
    "is_registered_disabled": true,
    "assistive_devices": ["휠체어"],
    "required_supports": ["elevator", "accessible_restroom"],
    "mobility_range_km": 15
  },
  "job": {
    "job_post_id": 101,
    "company_name": "한국예술인복지재단",
    "job_title": "행정지원사무원",
    "work_address": "서울특별시 중구 한강대로 416 서울스퀘어 3층",
    "work_lat": 37.554678,
    "work_lng": 126.970606,
    "employment_type": "계약직",
    "enter_type": "무관",
    "salary_type": "월급",
    "salary": "2,300,000",
    "term_date": "2026-04-20~2026-04-27",
    "required_career": "0년0개월",
    "required_education": "무관",
    "required_major": null,
    "required_licenses": "컴퓨터활용능력",
    "environment": {
      "env_both_hands": "양손작업 가능",
      "env_eyesight": "일상적 활동 가능",
      "env_lstn_talk": "듣고 말하기에 어려움 없음",
      "env_hand_work": "손작업 적음",
      "env_lift_power": "드는힘 거의 없음",
      "env_stnd_walk": "앉아서 근무 가능"
    },
    "agency_name": "한국장애인고용공단 서울지역본부",
    "registered_at": "20260417",
    "source_table": "pd_kepad_recruitment",
    "source_id": 101,
    "external_id": "KEPAD_RECRUITMENT-101"
  },
  "score_detail": {
    "job_fit_score": 88,
    "work_condition_score": 72,
    "disability_support_score": 83,
    "work_environment_score": 80,
    "company_stability_score": 86,
    "accessibility_score": 74
  },
  "total_score": 81,
  "job_fit_score": null,
  "reasons": [
    "6개 항목을 동일 비중으로 계산했습니다.",
    "직무 적합도 점수가 높습니다."
  ],
  "risk_factors": [
    "일부 접근성 정보는 현재 공공데이터 기준 추가 확인이 필요합니다."
  ],
  "evidence_items": [
    {
      "source_type": "KEPAD_RECRUITMENT",
      "source_name": "한국장애인고용공단 장애인 구인 실시간 현황",
      "description": "공고 원천 데이터입니다.",
      "distance_meters": null,
      "source_table": "pd_kepad_recruitment",
      "record_id": 101,
      "fields": {}
    }
  ]
}
```

### Response

```json
{
  "short_summary": "현재 조건 기준으로 비교적 안정적으로 추천되는 일자리예요. 이동 환경과 업무 조건이 전반적으로 긍정적으로 반영되었어요.",
  "recommendation_reasons": [
    "6개 항목을 동일 비중으로 계산했습니다.",
    "직무 적합도 점수가 높습니다."
  ],
  "caution_points": [
    "일부 접근성 정보는 현재 공공데이터 기준 추가 확인이 필요합니다."
  ],
  "checklist": [
    "실제 근무지 출입구, 엘리베이터, 화장실 접근성을 지원 전 확인하세요.",
    "채용 담당자에게 필요한 지원사항 제공 가능 여부를 확인하세요.",
    "모집기간, 고용형태, 급여 조건이 현재 희망 조건과 맞는지 확인하세요.",
    "점수 근거로 사용된 공공데이터가 최신 운영 상황과 일치하는지 확인하세요."
  ],
  "used_llm": false
}
```
