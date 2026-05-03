# nodong-aiserver

FastAPI + `uv` 기반 서버 프로젝트입니다.

## 자주 쓰는 명령어

### 1. 의존성 설치

```bash
uv sync
uv sync --dev
```

`pyproject.toml` / `uv.lock` 기준으로 가상환경과 패키지를 맞춥니다.

### 2. 개발 서버 실행

```bash
uv run python -m uvicorn app.main:app --reload
```

- 기본 주소: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 3. 서버 실행 확인

```bash
curl http://127.0.0.1:8000/health
```

### 4. 패키지 추가

```bash
uv add 패키지명
```

### 5. 개발용 패키지 추가

```bash
uv add --dev pytest
```

### 6. 포매터 / 린트 실행

```bash
uv run ruff check . --fix --unsafe-fixes

uv run ruff format .
```

### 7. pre-commit 설치 및 실행

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
### 8. pytest

```bash
uv run pytest -v
```

## CI/CD

`backend/deploy/nginx/bridgework.conf` 기준으로 같은 인스턴스의 FastAPI upstream(`19000`, `19001`)만 교체하는 배포를 사용합니다.

- 워크플로우: `.github/workflows/cicd-main-ec2.yml`
- 트리거: `main` 브랜치 push, `workflow_dispatch`
- 이미지 빌드: `Dockerfile`
- 서버 배포 스크립트: `deploy/deploy.sh`
- 라우팅 전제: 서버 Nginx에 `backend/deploy/nginx/fastapi-upstream.inc`가 이미 포함돼 있어야 함

### 배포 방식

1. GitHub Actions에서 PostGIS 서비스 컨테이너를 띄운 뒤 `pytest`를 실행합니다.
2. `aiserver` Docker 이미지를 빌드하고 tar.gz로 압축합니다.
3. 압축 이미지, 운영 `.env`, 배포 스크립트를 EC2로 업로드합니다.
4. EC2에서 비활성 슬롯(`19000` 또는 `19001`)에 새 컨테이너를 띄웁니다.
5. `/health` 확인 후 Nginx `fastapi-upstream.inc`를 새 포트로 바꾸고 `nginx reload` 합니다.
6. 이전 슬롯 컨테이너를 제거합니다.

### GitHub Secrets

- `EC2_HOST`
- `EC2_PORT`
- `EC2_USER`
- `EC2_SSH_PRIVATE_KEY`
- `DATABASE_URL`
- `CORS_ALLOW_ORIGINS`
- `EXPLANATION_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `LOG_LEVEL`

비어도 되는 값은 빈 문자열로 넣어도 됩니다. 다만 `DATABASE_URL`은 필수입니다.

### EC2 선행 작업

1. Docker, Nginx, curl 설치
2. 배포 계정에 Docker 실행 권한 부여
3. 배포 계정에 `sudo nginx -t`, `sudo systemctl reload nginx`, `sudo cp` 권한 부여
4. `backend/deploy/setup_nginx.sh` 기준 Nginx 설정이 이미 적용되어 있어야 함


### 폴더구조
| **영역** | **역할** |
| --- | --- |
| `api` | Spring이 호출하는 API 엔드포인트 |
| `schemas` | 요청/응답 DTO, Pydantic 모델 |
| `services` | 점수 계산, 태그 변환, 설명 생성 로직 |
| `repositories` | PostGIS 조회 |
| `db` | DB 연결 |
| `core` | 환경변수, 로깅 |

## 사용데이터 목록 
| SourceType | 데이터명 | 안내 링크 | 실제 호출 Endpoint | 인증키 | 주요 파라미터 |
|---|---|---|---|---|---|
| `KEPAD_RECRUITMENT` | 한국장애인고용공단_장애인 구인 실시간 현황 | [15117692](https://www.data.go.kr/data/15117692/openapi.do) | `http://apis.data.go.kr/B552583/job/job_list_env` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `_type=json` |
| `KEPAD_JOB_CATEGORY` | 한국장애인고용공단_장애인 고용직무분류 | [15157071](https://www.data.go.kr/data/15157071/openapi.do) | `http://apis.data.go.kr/B552583/jobcode/job_code` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `_type=json` |
| `KEPAD_STANDARD_WORKPLACE` | 한국장애인고용공단_장애인 표준사업장 실시간 조회 | [15119304](https://www.data.go.kr/data/15119304/openapi.do) | `http://apis.data.go.kr/B552583/comp/comp_auth` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `_type=json` |
| `KEPAD_SUPPORT_AGENCY` | 한국장애인고용공단_근로지원인 수행기관 실시간 정보 | [15131282](https://www.data.go.kr/data/15131282/openapi.do) | `http://apis.data.go.kr/B552583/instn/instn_list` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `_type=json` |
| `KORAIL_WEEK_PERSON_FACILITIES` | 한국철도공사_편의시설정보(교통약자 편의시설) | [15125774](https://www.data.go.kr/data/15125774/openapi.do#/API%20목록/weekPersonFacilities) | `https://apis.data.go.kr/B551457/convenience/weekPersonFacilities` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `returnType=JSON` |
| `SEOUL_TRANSPORT_WEAK_WHEELCHAIR_LIFT` | 서울교통공사_교통약자이용정보(휠체어리프트) | [15143843](https://www.data.go.kr/data/15143843/openapi.do#/) | `https://apis.data.go.kr/B553766/wksn/getWksnWhcllift` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `dataType=JSON` |
| `TRANSPORT_SUPPORT_CENTER` | 전국교통약자이동지원센터정보표준데이터 | [15028207](https://www.data.go.kr/tcs/dss/selectStdDataDetailView.do?publicDataPk=15028207) | `https://api.data.go.kr/openapi/tn_pubr_public_tfcwker_mvmn_cnter_api` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `type=json` |
| `RAIL_WHEELCHAIR_LIFT` | 국가철도공단_역사별 휠체어리프트 위치 | [15041686](https://www.data.go.kr/data/15041686/openapi.do) | `https://openapi.kric.go.kr/openapi/vulnerableUserInfo/stationWheelchairLiftLocation` | `KRIC_SERVICE_KEY` | `service=vulnerableUserInfo`, `operation=stationWheelchairLiftLocation`, `serviceKey`, `railOprIsttCd`, `lnCd`, `stinCd`, `format=json` |
| `RAIL_WHEELCHAIR_LIFT_MOVEMENT` | 역사별 휠체어리프트 이동동선 | [KRIC 209](https://data.kric.go.kr/rips/M_01_02/detail.do?id=209&service=vulnerableUserInfo&operation=stationWheelchairLiftMovement) | `https://openapi.kric.go.kr/openapi/vulnerableUserInfo/stationWheelchairLiftMovement` | `KRIC_SERVICE_KEY` | `service=vulnerableUserInfo`, `operation=stationWheelchairLiftMovement`, `serviceKey`, `railOprIsttCd`, `lnCd`, `stinCd`, `format=json` |
| `SEOUL_WHEELCHAIR_LIFT` | 서울교통공사_휠체어리프트 설치현황 | [15044262](https://www.data.go.kr/data/15044262/fileData.do) | `https://api.odcloud.kr/api/{publicDataPk}/v1/{publicDataDetailPk}` (fileData 페이지에서 식별자 추출 후 호출) | data.go.kr 서비스키 | `serviceKey`, `page`, `perPage(max=10000)`, `returnType=JSON`, `역명`(xlsx의 `STIN_NM` 기반 순회) |
| `SEOUL_SUBWAY_ENTRANCE_LIFT` | 서울시 지하철 출입구 리프트 위치정보 | [OA-21211](https://data.seoul.go.kr/dataList/OA-21211/S/1/datasetView.do) | `http://openapi.seoul.go.kr:8088/{API_KEY}/json/tbTraficEntrcLft/{start}/{end}` | data.seoul.go.kr 키 | `start/end(페이지 범위)`, `max rows=1000` |
| `SEOUL_WALKING_NETWORK` | 서울특별시_자치구별 도보 네트워크 공간정보 | [OA-21208](https://data.seoul.go.kr/dataList/OA-21208/S/1/datasetView.do) | `http://openapi.seoul.go.kr:8088/{API_KEY}/json/TbTraficWlkNet/{start}/{end}` | data.seoul.go.kr 키 | `start/end(페이지 범위)`, `max rows=1000` |
| `NATIONWIDE_BUS_STOP` | 국토교통부_전국 버스정류장 위치정보 | [15067528](https://www.data.go.kr/data/15067528/fileData.do#tab-layer-openapi) | `https://api.odcloud.kr/api/{publicDataPk}/v1/{publicDataDetailPk}` (fileData 페이지에서 식별자 추출 후 호출) | data.go.kr 서비스키 | `serviceKey`, `page`, `perPage(max=10000)`, `returnType=JSON` |
| `NATIONWIDE_TRAFFIC_LIGHT` | 전국신호등표준데이터 | [15028198](https://www.data.go.kr/data/15028198/standard.do#) | `https://api.data.go.kr/openapi/tn_pubr_public_traffic_light_api` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `type=xml` |
| `NATIONWIDE_CROSSWALK` | 전국횡단보도표준데이터 | [15028201](https://www.data.go.kr/data/15028201/standard.do) | `https://api.data.go.kr/openapi/tn_pubr_public_crosswalk_api` | data.go.kr 서비스키 | `serviceKey`, `pageNo`, `numOfRows(max=1000)`, `type=json` |
| `VOCATIONAL_TRAINING` | 한국고용정보원_직업훈련_국민내일배움카드 훈련과정 | [work24 000004](https://www.work24.go.kr/cm/e/a/0110/selectOpenApiSvcInfo.do?apiSvcId=&upprApiSvcId=&fullApiSvcId=000000000000000000000000000004) | `https://www.work24.go.kr/cm/openApi/call/hr/callOpenApiSvcInfo310L01.do` | Work24 인증키 | `authKey`, `returnType=XML`, `pageNum`, `pageSize(max=100)` |
| `JOBSEEKER_COMPETENCY_PROGRAM` | 한국고용정보원_구직자취업역량 강화프로그램 | [work24 000098](https://www.work24.go.kr/cm/e/a/0110/selectOpenApiSvcInfo.do?apiSvcId=&upprApiSvcId=&fullApiSvcId=000000000000000000000000000098) | `https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo217L01.do` | Work24 인증키 | `authKey`, `returnType=XML`, `startPage`, `display(max=100)`, `pgmStdt(YYYYMMDD, 오늘~1개월 후 반복)` |
