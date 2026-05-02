# 프론트 응답 조합 예시

## 목적

이 문서는 Spring Backend가 FastAPI 분석 결과를 받아 프론트엔드 응답 DTO로 조합할 때 사용할 예시를 제공한다.

이 문서는 계약을 새로 정의하는 문서가 아니다.

기준 문서:

- `docs/fastapi_internal_api_contract.md`
- `docs/spring_analysis_storage_cache_policy.md`
- `docs/spring_fastapi_call_scenarios.md`

핵심 원칙:

- 프론트는 FastAPI 응답을 직접 받지 않는다.
- Spring은 공고 원본 정보와 분석 결과를 화면 목적에 맞게 조합한다.
- 목록 화면과 상세 화면 DTO는 분리하는 것을 권장한다.

---

## 1. 목록 화면 응답 예시

목록 화면, 지도 카드, 추천 리스트는 빠른 응답과 간결한 정보가 우선이다.

권장 조합:

- Spring 원본 공고 정보
- FastAPI `analyze-batch`의 점수/등급/summary
- 핵심 긍정 요인 1~2개
- 핵심 위험 요인 1~2개

예시:

```json
{
  "jobPostId": 101,
  "companyId": 55,
  "companyName": "ABC복지센터",
  "jobTitle": "사무보조",
  "workAddress": "서울특별시 중구 세종대로 110",
  "accessibility": {
    "score": 88,
    "grade": "GOOD",
    "summary": "현재 데이터 기준 접근성 조건이 비교적 양호한 공고입니다.",
    "positiveFactors": [
      "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다."
    ],
    "riskFactors": [
      "저상버스 이용 가능 여부는 지원 전 확인을 권장합니다."
    ]
  }
}
```

권장 필드:

- `jobPostId`
- `companyId`
- `companyName`
- `jobTitle`
- `workAddress`
- `accessibility.score`
- `accessibility.grade`
- `accessibility.summary`

선택 필드:

- `accessibility.positiveFactors`
- `accessibility.riskFactors`

권장하지 않는 것:

- `score_detail` 전체 노출
- `evidence_items` 전체 노출
- `detail_explanation` 포함

---

## 2. 지도 마커 응답 예시

지도 화면에서는 카드보다 더 가벼운 응답이 적합하다.

예시:

```json
{
  "jobPostId": 101,
  "companyName": "ABC복지센터",
  "jobTitle": "사무보조",
  "lat": 37.5701,
  "lng": 126.9823,
  "accessibility": {
    "score": 88,
    "grade": "GOOD"
  }
}
```

권장 이유:

- 마커 렌더링에는 점수와 등급만으로 충분한 경우가 많다.
- 세부 문구는 카드 오픈 시점에만 내려도 된다.

---

## 3. 공고 상세 화면 응답 예시

상세 화면은 근거와 설명을 함께 보여줄 수 있어야 한다.

권장 조합:

- Spring 원본 공고 정보
- FastAPI `analyze-batch` 전체 핵심 결과
- 필요 시 `explanations/accessibility` 응답

예시:

```json
{
  "jobPostId": 101,
  "companyId": 55,
  "companyName": "ABC복지센터",
  "jobTitle": "사무보조",
  "workAddress": "서울특별시 중구 세종대로 110",
  "isStandardWorkplace": true,
  "isDisabilityFriendlyPost": true,
  "accessibility": {
    "score": 88,
    "grade": "GOOD",
    "scoreDetail": {
      "transportScore": 20,
      "stationAccessScore": 20,
      "crosswalkScore": 20,
      "facilityScore": 18,
      "workEnvironmentScore": 20,
      "riskPenalty": 0
    },
    "summary": "현재 데이터 기준 접근성 조건이 비교적 양호한 공고입니다.",
    "positiveFactors": [
      "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다."
    ],
    "riskFactors": [
      "저상버스 이용 가능 여부는 지원 전 확인을 권장합니다."
    ],
    "evidenceItems": [
      {
        "sourceType": "NATIONWIDE_BUS_STOP",
        "sourceName": "전국 버스정류장 위치정보",
        "description": "근무지 반경 내 버스정류장 4개가 확인됩니다.",
        "distanceMeters": 180.0,
        "recordId": 123
      }
    ],
    "explanation": {
      "version": "v1-rule-fallback",
      "shortSummary": "사무보조 공고는 현재 조건 기준 접근성이 비교적 양호합니다.",
      "detailExplanation": "ABC복지센터의 사무보조 공고는 접근성 점수 88점, 등급 GOOD으로 분석되었습니다.",
      "checkPoints": [
        "저상버스 이용 가능 여부는 지원 전 확인을 권장합니다."
      ],
      "usedLlm": false
    }
  }
}
```

권장 필드:

- `accessibility.score`
- `accessibility.grade`
- `accessibility.scoreDetail`
- `accessibility.summary`
- `accessibility.positiveFactors`
- `accessibility.riskFactors`
- `accessibility.evidenceItems`

설명 API를 사용하는 경우 추가 권장 필드:

- `accessibility.explanation.version`
- `accessibility.explanation.shortSummary`
- `accessibility.explanation.detailExplanation`
- `accessibility.explanation.checkPoints`
- `accessibility.explanation.usedLlm`

---

## 4. 설명 API를 생략한 상세 화면 예시

초기 MVP에서는 설명 API 없이도 상세 화면을 열 수 있어야 한다.

예시:

```json
{
  "jobPostId": 101,
  "companyName": "ABC복지센터",
  "jobTitle": "사무보조",
  "accessibility": {
    "score": 88,
    "grade": "GOOD",
    "summary": "현재 데이터 기준 접근성 조건이 비교적 양호한 공고입니다.",
    "positiveFactors": [
      "현재 공공데이터 기준으로 근무지 주변 버스정류장 정보가 확인됩니다."
    ],
    "riskFactors": [
      "저상버스 이용 가능 여부는 지원 전 확인을 권장합니다."
    ],
    "evidenceItems": [
      {
        "sourceType": "NATIONWIDE_BUS_STOP",
        "sourceName": "전국 버스정류장 위치정보",
        "description": "근무지 반경 내 버스정류장 4개가 확인됩니다.",
        "distanceMeters": 180.0,
        "recordId": 123
      }
    ]
  }
}
```

이 경우 프론트는 다음 우선순위로 문구를 사용할 수 있다.

1. `summary`
2. `positiveFactors`
3. `riskFactors`
4. `evidenceItems`

---

## 5. 분석 실패 상태 응답 예시

FastAPI 호출 실패 시 Spring은 프론트에 빈 성공 DTO를 주기보다 상태를 명시하는 것을 권장한다.

예시:

```json
{
  "jobPostId": 101,
  "companyName": "ABC복지센터",
  "jobTitle": "사무보조",
  "accessibility": {
    "status": "UNAVAILABLE",
    "message": "현재 접근성 분석 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

캐시된 마지막 성공 결과가 있으면 다음 형태도 가능하다.

```json
{
  "jobPostId": 101,
  "companyName": "ABC복지센터",
  "jobTitle": "사무보조",
  "accessibility": {
    "status": "STALE",
    "score": 88,
    "grade": "GOOD",
    "summary": "현재 데이터 기준 접근성 조건이 비교적 양호한 공고입니다.",
    "message": "최신 분석을 불러오지 못해 최근 결과를 표시합니다."
  }
}
```

권장 상태값:

- `READY`
- `UNAVAILABLE`
- `STALE`

---

## 6. 필드 네이밍 조합 원칙

FastAPI 내부 계약은 snake_case다.

Spring이 프론트 DTO를 camelCase로 변환하는 것은 허용된다. 다만 의미 변경은 하면 안 된다.

예:

- `accessibility_score` -> `score`
- `accessibility_grade` -> `grade`
- `score_detail.transport_score` -> `scoreDetail.transportScore`
- `evidence_items` -> `evidenceItems`
- `used_llm` -> `usedLlm`

주의:

- `summary`를 `detailExplanation`으로 대체하지 않는다.
- `risk_factors`를 숨기지 않는다.
- `check_points`를 누락하더라도 설명 API를 썼다면 저장은 유지하는 것을 권장한다.

---

## 7. 현재 권장 결론

현재 MVP 단계에서는 다음 조합을 권장한다.

1. 목록/지도: `score + grade + summary`
2. 상세: `score + grade + scoreDetail + factors + evidenceItems`
3. 긴 설명이 필요할 때만 `explanation` 블록 추가
4. FastAPI 실패 시 `UNAVAILABLE` 또는 `STALE` 상태를 명시
