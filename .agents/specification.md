## 1. 서비스 목표

장애인 구직자에게 직무 적합성, 접근성, 지원 인프라를 반영한 실제 근속 가능한 일자리를 추천한다.

## 2. 시스템 역할 분리

1. Java Spring Backend
- 인증/회원/프로필/~~OCR/~~공공데이터 동기화/API 게이트웨이
- FastAPI 요청/응답 중계
- FastAPI에는 사용자 선택 프로필만 전달

1. FastAPI
- 스코어링 계산, 추천 순위 산출, LLM 설명 생성
- PostgreSQL 직접 조회(공고/공공데이터)

## 3. 수집 및 가공 데이터

1. 한국장애인고용공단_장애인 구인 실시간 현황https://www.data.go.kr/data/15117692/openapi.do + 지오코딩(네이버 NCP Geocoding API)
2. 한국장애인고용공단_장애인 고용직무분류https://www.data.go.kr/data/15157071/openapi.do
3. 한국장애인고용공단_장애인 표준사업장 실시간 조회https://www.data.go.kr/data/15119304/openapi.do
4. 한국장애인고용공단_근로지원인 수행기관 실시간 정보https://www.data.go.kr/data/15131282/openapi.do + 지오코딩(네이버 NCP Geocoding API)
5. 한국철도공사_편의시설정보[https://www.data.go.kr/data/15125774/openapi.do#/API 목록/weekPersonFacilities](https://www.data.go.kr/data/15125774/openapi.do#/API%20%EB%AA%A9%EB%A1%9D/weekPersonFacilities)
6. 서울교통공사_교통약자이용정보(휠체어리프트)https://www.data.go.kr/data/15143843/openapi.do#/
7. 전국교통약자이동지원센터정보표준데이터https://www.data.go.kr/tcs/dss/selectStdDataDetailView.do?publicDataPk=15028207
8. 국가철도공단_역사별 휠체어리프트 위치https://data.kric.go.kr/rips/M_01_02/detail.do?id=205&service=vulnerableUserInfo&operation=stationWheelchairLiftLocation
9. 역사별 휠체어리프트 이동동선https://data.kric.go.kr/rips/M_01_02/detail.do?id=209&service=vulnerableUserInfo&operation=stationWheelchairLiftMovement
10. 서울교통공사_휠체어리프트 설치현황https://www.data.go.kr/data/15044262/fileData.do
11. 서울시 지하철 출입구 리프트 위치정보https://data.seoul.go.kr/dataList/OA-21211/S/1/datasetView.do
12. 서울특별시_자치구별 도보 네트워크 공간정보https://data.seoul.go.kr/dataList/OA-21208/S/1/datasetView.do
13. 국토교통부_전국 버스정류장 위치정보https://www.data.go.kr/data/15067528/fileData.do#tab-layer-openapi
14. 전국신호등표준데이터https://www.data.go.kr/data/15028198/standard.do#
15. 전국횡단보도표준데이터https://www.data.go.kr/data/15028201/standard.do
16. 서울교통공사_휠체어경사로 설치 현황https://data.seoul.go.kr/dataList/OA-13116/S/1/datasetView.do
17. 서울시 저상버스 도입 노선 및 노선별 보유율https://data.seoul.go.kr/dataList/OA-22229/F/1/datasetView.do
18. 한국고용정보원_직업훈련_국민내일배움카드 훈련과정https://www.work24.go.kr/cm/e/a/0110/selectOpenApiSvcInfo.do?apiSvcId=&upprApiSvcId=&fullApiSvcId=000000000000000000000000000004
19. 한국고용정보원_구직자취업역량 강화프로그램https://www.work24.go.kr/cm/e/a/0110/selectOpenApiSvcInfo.do?apiSvcId=&upprApiSvcId=&fullApiSvcId=000000000000000000000000000098

## 4. 입력 정의

### 4-1. 가입 완료 입력(온보딩)

- 가입 완료 시 기본 프로필 1개를 반드시 생성한다. 또한 온보딩(가입 완료에 필요한 추가 정보 기입)은 4-2 프로필 입력에서의 필수 입력들만 진행.

### 4-2. 프로필 입력

가입 이탈을 줄이기 위해 스코어링 필수 최소 항목만 필수 유지. 스코어링 품질에 강한 영향이 있는 항목만 필수로 유지.

- 프로필은 사용자당 최대 3개.
- 기본 프로필 1개는 필수 보유(삭제 불가, 기본 변경 가능).
- 내정보에서 등록/수정/삭제.

필수 입력:

- 기본: 이름, 성별, 연락처, 이메일, 생년월일, 거주지 상세 주소
- 학력/경력: 최종 학력, 주요 경력(없으면 신입 표기)
- 직무: 지원 직무, 보유 기술/역량
- 장애: 장애 여부, 장애 유형, 장애 정도, 장애인 등록 여부
- 근무조건: 가능한 고용형태
- 소개: 자기소개

선택 입력:

- 비상 연락처
- 전공, 세부 경력, 프로젝트, 공백 사유
- 자격증, 포트폴리오 URL/파일, 수상, 교육 이수
- 상세 장애 설명, 보조기기, 필요 지원사항
- 근무 가능 시점, 희망 연봉, 시간 선호, 재택 여부, 이동 가능 범위
- 지원 동기, 직무 적합성 설명, 커리어 목표, 강점/약점
- 병역, 국가유공자, SNS/개인 웹사이트

### 4-3. 화면 필터 입력 (기능2/3 공통, 저장 없음)

프론트에서 매 요청마다 선택. 모든 항목은 선택형(옵션)이며 중복 가능

- 희망 직무 (선택 목록은 Spring이 매일 스케줄러로 수집한 `한국장애인고용공단_장애인 고용직무분류` DB 데이터를 트리(대분류 > 중분류 > 소분류)로 별도 api를 통해 제공)
- 희망 근무지역(전국 17개 시/도) - 서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 경기, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주
- 고용형태 - 정규직, 계약직, 무기계약직, 시간제, 일용직, 인턴, 파견/용역, 재택/원격
- 급여 방식 - 월급, 연봉, 시급, 일급, 건별/성과급, 회사 내규에 따름, 면접 후 협의

## 5. 기능 정의

### 기능 0. 로그인/회원가입

- 카카오/네이버 로그인
- 최초 로그인 시 기본 프로필 필수 항목 입력 완료 후 가입 완료

### 기능 1. 프로필 생성/관리

- 직접 입력 저장
- 또는 포트폴리오로 생성하기(2차) : 입력할 때 포트폴리오 파일 업로드 시 Spring OCR + LLM 기반 프로필 초안 생성 가능
- 프로필 최대 3개 관리
- 기본 프로필 지정/변경

### 기능 2. 퀵 맞춤 일자리 추천 (최신 + 직무 적합)

- 프론트는 별도 퀵공고 페이지에서 Spring Backend만 호출한다.
- Spring Backend는 AI ON 추천을 비동기 task로 관리하고, 20개 배치를 1개 단위 FastAPI 요청으로 나눠 부분 결과를 누적할 수 있다.
- FastAPI는 `limit`/`offset`을 안정적으로 처리하고, `limit=1` 요청도 일반 요청과 동일한 응답 구조로 반환한다.
- 후보 공고는 모집 중이고 마감일이 지나지 않은 공고를 기준으로 하며 좌표가 있는 공고를 우선한다.

1. AI 직무 적합도 토글 ON
    - 프론트에서 프로필 1개 선택(기본 프로필 최상단 노출)
    - Spring → FastAPI: 사용자 선택 프로필만 전달
    - FastAPI: DB 공고를 최신순 조회 후 직무 적합도만 계산
    - FastAPI → Spring: 공고별 직무 적합도 포함 결과 반환
    - Spring → 프론트: 결과 전달
    - 프론트: 화면 필터 적용, 일정 점수 이상 공고 강조
2. AI 직무 적합도 토글 OFF
    - FastAPI 호출 없음
    - Spring이 DB 공고 최신순 반환
    - 프론트가 화면 필터 적용

### 기능 3. 지역 접근성 지도 추천 (종합 점수)

지도상에 공고 + 기업정보를 나타내며 추가로 근로지원인 수행기관 마커를 함께 표시. (백엔드 api)
(근로지원인 수행기관 데이터는 점수 미반영, 지도 레이어 전용)

1. AI 스코어링 토글 ON
    - 프론트에서 프로필 1개 선택
    - Spring → FastAPI: 사용자 선택 프로필만 전달
    - FastAPI: DB 공고/공공데이터 직접 조회, 동일 비중 종합 점수 계산
    - FastAPI → Spring: 항목별 점수 + 총점 + 내림차순 결과 반환
    - Spring → 프론트: 결과 전달
    - 프론트: 화면 필터 적용
    - 지도 추천은 후보 점수 계산 후 정렬하고 `limit`/`offset`을 적용한다.
    - Spring Backend가 20개 배치를 1개 단위 FastAPI 요청으로 나눠 부분 결과를 누적할 수 있다.
    - 프론트는 부분 결과를 1개씩 반영하고 최대 100개까지만 표시한다.
2. AI 스코어링 토글 OFF
    - FastAPI 호출 없음
    - Spring이 DB 공고 반환
    - 프론트가 화면 필터 적용

- 2차(현재 미포함)
    
    ### 기능 4. 지원 인프라/체크리스트 안내(추가)
    
    - 공고 상세에서 지원기관/편의정보/체크리스트 제공
    
    ### 기능 5. 훈련 연계 추천(추가)
    
    - 직무 격차 기반 훈련/프로그램 추천

## 6. FastAPI 스코어링 정의

### 6-1. 기능별 적용

- 기능2: 직무 적합도만 적용
- 기능3: 6개 항목 동일 비중 종합 점수 적용

### 6-2. 점수 항목별 사용 데이터/컬럼/프로필 항목

| **점수 항목** | **공공데이터(명칭/URL)** | **사용 컬럼** | **사용자 프로필 사용 항목(input)** |
| --- | --- | --- | --- |
| 직무 적합도 | - 한국장애인고용공단_장애인 구인 실시간 현황 ([**15117692**](https://www.data.go.kr/data/15117692/openapi.do)) | - jobNm(모집직종)<br>- reqCareer(요구경력)<br>- reqEduc(요구학력)<br>- reqMajor(요구전공)<br>- reqLicens(요구자격증)<br>- envHandWork(손작업)<br>- envLiftPower(드는힘)<br>- envStndWalk(서거나 걷기) | **필수**<br>- 지원 직무<br>- 보유 기술/역량<br>- 최종 학력<br>- 주요 경력<br><br>**선택**<br>- 전공<br>- 자격증<br>- 직무 적합성 설명 |
| 근무조건 적합도 | - 한국장애인고용공단_장애인 구인 실시간 현황 ([**15117692**](https://www.data.go.kr/data/15117692/openapi.do)) | - empType(고용형태)<br>- enterType(입사형태)<br>- salaryType(임금형태)<br>- salary(임금)<br>- termDate(모집기간) | **필수**<br>- 가능한 고용형태<br><br>**선택**<br>- 근무 가능 시점<br>- 희망 연봉<br>- 시간 선호<br>- 재택 여부 |
| 장애 지원 적합도 | - 한국장애인고용공단_장애인 표준사업장 실시간 조회 ([**15119304**](https://www.data.go.kr/data/15119304/openapi.do))<br>- 한국장애인고용공단_장애인 구인 실시간 현황 ([**15117692**](https://www.data.go.kr/data/15117692/openapi.do)) | **표준사업장**<br>- compName(기업명)<br>- compBizNo(사업자등록번호)<br>- compRegNo(인증번호)<br>- compTypeNm(인증유형)<br>- authDate(인증일자)<br>- cancelDate(취소일자)<br>- compCert(인증상태)<br><br>**공고**<br>- enterType(입사형태)<br>- jobNm(직종)<br>- compAddr(사업장주소) | **필수**<br>- 장애 유형<br>- 장애 정도<br>- 장애인 등록 여부<br><br>**선택**<br>- 필요 지원사항<br>- 상세 장애 설명<br>- 보조기기 |
| 업무환경 적합도 | - 한국장애인고용공단_장애인 구인 실시간 현황 ([**15117692**](https://www.data.go.kr/data/15117692/openapi.do)) | - envBothHands(양손사용)<br>- envEyesight(시력)<br>- envLstnTalk(듣고말하기)<br>- envHandWork(손작업)<br>- envLiftPower(드는힘)<br>- envStndWalk(서거나걷기)<br>- jobNm(직종) | **필수**<br>- 장애 유형<br>- 장애 정도<br><br>**선택**<br>- 상세 장애 설명<br>- 보조기기<br>- 이동 가능 범위 |
| 기업 안정성/채용 친화도 | - 한국장애인고용공단_장애인 표준사업장 실시간 조회 ([**15119304**](https://www.data.go.kr/data/15119304/openapi.do))<br>- 한국장애인고용공단_장애인 구인 실시간 현황 ([**15117692**](https://www.data.go.kr/data/15117692/openapi.do)) | **표준사업장**<br>- compName(기업명)<br>- compBizNo(사업자번호)<br>- authDate(인증일)<br>- cancelDate(취소일)<br>- compTypeNm(인증유형)<br><br>**공고**<br>- busplaName(사업장명)<br>- compAddr(사업장주소)<br>- regagnName(담당기관)<br>- offerregDt(구인신청일)<br>- regDt(등록일) | 사용 없음 |
| 접근성 요약 점수 | - 전국교통약자이동지원센터정보표준데이터 ([**15028207**](https://www.data.go.kr/tcs/dss/selectStdDataDetailView.do?publicDataPk=15028207))<br>- 국가철도공단_역사별 휠체어리프트 위치 ([**KRIC-205**](https://data.kric.go.kr/rips/M_01_02/detail.do?id=205&service=vulnerableUserInfo&operation=stationWheelchairLiftLocation))<br>- 역사별 휠체어리프트 이동동선 ([**KRIC-209**](https://data.kric.go.kr/rips/M_01_02/detail.do?id=209&service=vulnerableUserInfo&operation=stationWheelchairLiftMovement))<br>- 서울교통공사_휠체어리프트 설치현황 ([**15044262**](https://www.data.go.kr/data/15044262/fileData.do))<br>- 서울교통공사_교통약자이용정보 ([**15143843**](https://www.data.go.kr/data/15143843/openapi.do#/))<br>- 서울시 지하철 출입구 리프트 위치정보 ([**OA-21211**](https://data.seoul.go.kr/dataList/OA-21211/S/1/datasetView.do))<br>- 서울특별시_자치구별 도보 네트워크 공간정보 ([**OA-21208**](https://data.seoul.go.kr/dataList/OA-21208/S/1/datasetView.do))<br>- 국토교통부_전국 버스정류장 위치정보 ([**15067528**](https://www.data.go.kr/data/15067528/fileData.do#tab-layer-openapi))<br>- 전국신호등표준데이터 ([**15028198**](https://www.data.go.kr/data/15028198/standard.do#))<br>- 전국횡단보도표준데이터 ([**15028201**](https://www.data.go.kr/data/15028201/standard.do))<br>- 한국철도공사_편의시설정보 ([**15125774**](https://www.data.go.kr/data/15125774/openapi.do#/API%20%EB%AA%A9%EB%A1%9D/weekPersonFacilities))<br>- 서울교통공사_휠체어경사로 설치 현황 ([**OA-13116**](https://data.seoul.go.kr/dataList/OA-13116/S/1/datasetView.do))<br>- 서울시 저상버스 도입 노선 및 노선별 보유율 ([**OA-22229**](https://data.seoul.go.kr/dataList/OA-22229/F/1/datasetView.do)) | **이동지원센터**<br>- latitude(위도)<br>- longitude(경도)<br>- liftVhcleCo(리프트차량수)<br>- slopeVhcleCo(슬로프차량수)<br>- insideOpratArea(관내운행지역)<br><br>**KRIC 위치**<br>- railOprIsttCd(운영기관코드)<br>- lnCd(선코드)<br>- stinCd(역코드)<br>- exitNo(출구번호)<br>- dtlLoc(상세위치)<br>- runStinFlorFr(시작층)<br>- runStinFlorTo(종료층)<br>- len(길이)<br>- wd(폭)<br>- bndWgt(한계중량)<br>- LN_NM(선명)<br>- STIN_NM(역명)<br><br>**KRIC 동선**<br>- mvPathDvNm(이동경로구분)<br>- mvDst(이동거리)<br>- mvContDtl(상세이동내용)<br>- LN_NM(선명)<br>- STIN_NM(역명)<br><br>**서울 리프트**<br>- 역명<br>- 호선<br>- 폭<br>- 한계중량<br><br>**교통약자이용정보**<br>- stnNm(역명)<br>- lineNm(호선명)<br>- vcntEntrcNo(출입구번호)<br>- bgngFlr(시작층)<br>- endFlr(종료층)<br>- limitWht(한계중량)<br>- oprtngSitu(가동현황)<br><br>**출입구 리프트**<br>- SBWY_STN_NM(지하철역명)<br>- NODE_WKT(좌표)<br><br>**도보네트워크**<br>- LNKG_LEN(링크길이)<br>- CRSWK(횡단보도)<br>- OVRP(육교)<br>- TNL(터널)<br>- BRG(교량)<br>- BLDG(건물내)<br><br>**버스정류장**<br>- 정류장명<br>- 위도<br>- 경도<br>- 도시명<br><br>**신호등**<br>- latitude(위도)<br>- longitude(경도)<br>- fnctngSgngnrYn(보행자작동신호기)<br>- sondSgngnrYn(음향신호기)<br>- remndrIdctYn(잔여시간표시기)<br><br>**횡단보도**<br>- latitude(위도)<br>- longitude(경도)<br>- ftpthLowerYn(보도턱낮춤)<br>- brllBlckYn(점자블록)<br>- sondSgngnrYn(음향신호기)<br>- tfclghtYn(보행자신호등)<br><br>**코레일 편의시설**<br>- stn_nm(역명)<br>- pwdbs_slwy_estnc(경사로유무)<br>- pwdbs_tolt_estnc(장애인화장실유무)<br>- whlch_liftt_cnt(리프트수)<br><br>**경사로**<br>- 호선<br>- 역명<br>- 구분<br>- 위치<br><br>**저상버스**<br>- 노선번호<br>- 저상버스 대수<br>- 저상보유율 | **필수**<br>- 거주지 상세주소<br>- 장애 유형<br>- 장애 정도<br><br>**선택**<br>- 이동 가능 범위<br>- 보조기기<br>- 필요 지원사항 |
## 7. 접근성 원칙

- WCAG 2.2 AA 준수
- 스크린리더 라벨 제공
- 키보드 탐색 가능
- 색상 단독 상태표현 금지
- 지도 정보 목록 대체 제공
- 용어 설명 제공
- 구체적 오류 메시지 제공
- 단계형 온보딩

---

# 자바 스프링 API 구현 리스트

1. 인증/회원
    - `POST /api/v1/auth/social/login`
    - `POST /api/v1/auth/social/signup/complete`
    - `POST /api/v1/auth/token/refresh`
    - `POST /api/v1/auth/logout`
    - `GET /api/v1/auth/me`
2. 프로필 관리(최대 3개, 기본 프로필 1개 필수)
    - `GET /api/v1/profiles`
    - `POST /api/v1/profiles`
    - `GET /api/v1/profiles/{profileId}`
    - `PUT /api/v1/profiles/{profileId}`
    - `DELETE /api/v1/profiles/{profileId}`
    - `PATCH /api/v1/profiles/{profileId}/set-default`
3. OCR
    - `POST /api/v1/profiles/ocr/extract`
4. 화면 필터 옵션
    - `GET /api/v1/options/job-categories/tree`
    설명: 스케줄러가 동기화한 `한국장애인고용공단_장애인 고용직무분류` DB 데이터 기반 트리 반환
    - `GET /api/v1/options/regions`
    - `GET /api/v1/options/employment-types`
    - `GET /api/v1/options/salary-types`
5. 게이트웨이
    - `POST /api/v1/recommend/quick`
    - `POST /api/v1/recommend/map`
    - 동작 규칙
        - `aiEnabled=true`: FastAPI 호출
        - `aiEnabled=false`: Spring이 DB 공고 반환
        - 프론트 필터는 프론트에서 적용
6. 한국장애인고용공단_근로지원인 수행기관 실시간 정보(DB 저장본) 지도 레이어 조회
    - `GET /api/v1/map/support-agencies`
7. 공공데이터 동기화/조회
    - `POST /api/v1/sync/public-data/run`
    - `GET /api/v1/sync/public-data/logs`
    - `GET /api/v1/sync/public-data/sources`
    - `GET /api/v1/public-data/records`
    - `GET /api/v1/public-data/records/{recordId}`

---

# FastAPI 구현 리스트

1. 스코어링 API
    - `POST /api/v1/score/quick`
        - 입력: 선택 프로필 1개
        - 처리: 모집 중/마감 전/좌표 우선 공고 조회 + 직무 적합도 계산
        - 출력: 공고 + `job_fit_score` + 근거
    - `POST /api/v1/score/map`
        - 입력: 선택 프로필 1개
        - 처리: 공고/공공데이터 조회 + 6항목 동일비중 종합점수 계산 + 점수 정렬 후 페이지네이션
        - 출력: 공고 + 항목별 점수 + 총점 + 근거
2. 설명 생성 API(선택)
    - `POST /api/v1/explain/recommendation`
        - 입력: 공고/점수/프로필
        - 출력: 추천 사유/주의사항/체크리스트
3. 내부 모듈
    - 직무 유사도 모듈
    - 공고 텍스트 정규화 모듈
    - 접근성 점수 집계 모듈
    - 동일비중 종합 점수 모듈
    - 응답 포맷터(항목별 점수/총점)
4. 데이터 접근
    - PostgreSQL 직접 접근
    - 공고/공공데이터 테이블 조회
    - 필요 시 스코어링 결과 캐시 저장 (선택)
