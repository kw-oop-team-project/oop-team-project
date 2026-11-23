# 서울체육맵 — 공공체육시설 찾기

서울시와 국민체육진흥공단의 공공 API를 함께 조회하는 Streamlit 사이트입니다.
자치구·시설명·종목으로 검색하고 주소·운영시간·연락처·이용료 및 공식 예약 일정을 확인합니다.
시설 목록과 지도는 검색 결과를 탐색하는 용도이며 자치구별 보유량 통계는 제공하지 않습니다.

## 화면 구성

- **홈**: 체육 이미지를 배경으로 사이트의 목적을 소개하고 두 메뉴로 이동합니다.
- **체육시설 찾기**: 첫 진입 시 서울의 시설 지도를 보여줍니다. 지도를 확대·이동하여
  주변 시설을 살펴보고 표시를 클릭할 수 있습니다. 아래로 스크롤하면 자치구·종목 선택과
  시설명 검색, 25개 단위 시설 카드, 선택 시설의 상세정보·예약 안내가 이어집니다.
- **체육시설 현황**: 상단 메뉴와 준비 중 안내 화면만 제공합니다. 통계는 후속 구현 대상입니다.

지도 표시와 시설 카드 클릭은 같은 시설 선택 상태를 사용합니다. 현재 위치를 자동 수집하지 않으며,
지도 탐색과 자치구 선택으로 위치를 찾습니다. 좌표가 없는 시설도 검색 목록과 주소 지도 검색에서 확인할 수 있습니다.
홈과 현황 화면에서는 시설·예약 API를 호출하지 않습니다.

## 실행

Python 3.11 이상을 권장합니다. 저장소 루트에서 실행합니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SEOUL_OPEN_API_KEY = "발급받은 서울시 키"
$env:DATA_GO_KR_SERVICE_KEY = "발급받은 공공데이터포털 키"
# 예약용 서울시 키를 별도로 발급받았다면 추가 설정
$env:SEOUL_RESERVATION_API_KEY = "발급받은 예약 API 키"
python -m streamlit run app.py
```

환경변수 대신 `.streamlit/secrets.toml`에 같은 이름으로 설정해도 됩니다.
빈 설정 예시는 [secrets.example.toml](.streamlit/secrets.example.toml)에 있습니다.
이미 입력한 `secrets.toml`은 그대로 사용합니다.
환경변수가 우선하며 `.env` 파일은 자동으로 읽지 않습니다.
실제 키를 소스나 테스트 데이터에 넣지 마세요. secrets와 `.env`는 Git에서 제외됩니다.

```toml
SEOUL_OPEN_API_KEY = "발급받은 서울시 키"
DATA_GO_KR_SERVICE_KEY = "발급받은 공공데이터포털 키"
SEOUL_RESERVATION_API_KEY = ""
```

`SEOUL_RESERVATION_API_KEY`는 선택 설정입니다. 비워 두거나 생략하면
예약 API도 `SEOUL_OPEN_API_KEY`를 사용합니다. 별도의 예약 키가 있으면 그 키를 우선합니다.
각 서비스에 대한 이용 승인이 필요합니다. 공공데이터포털 키는 일반 인증키(Decoding)를
권장하며 Encoding 형태도 한 번 디코딩하여 처리합니다. 키를 화면이나 로그에 출력하지 않습니다.

## API와 데이터 정책

| API | 공식 명세 | 사용 방법 |
|---|---|---|
| 서울시 `facilities` | [OA-21779](https://data.seoul.go.kr/dataList/OA-21779/A/1/datasetView.do) | 시작/끝 인덱스 페이지 조회. `BK_CD_NAME=공공체육시설`을 선별하고 `FT_KIND_NAME`을 종목으로 사용 |
| 국민체육진흥공단 전국체육시설 | [15113986](https://www.data.go.kr/data/15113986/openapi.do) | `SRVC_API_SFMS_FACI/TODZ_API_SFMS_FACI`에 `cp_nm=서울특별시`, `faci_gb_nm=공공`, `pageNo`, `numOfRows`, `resultType=JSON` 전달. 응답에서도 지역·공공 구분 재검사 |
| 서울시 `ListPublicReservationSport` | [OA-2266](https://data.seoul.go.kr/dataList/OA-2266/A/1/datasetView.do) | 모든 페이지에서 선택 시설에 연결되는 예약의 접수 상태·접수/이용 기간·요금·공식 링크 표시 |

서울시 API는 공식 문서의 `http://openapi.seoul.go.kr:8088` 게이트웨이를 사용합니다.
전국체육시설 API는 HTTPS를 사용합니다. TLS 인증서 검증을 해제하지 않습니다.
서울시 시설 API에는 위경도가 없으므로, 전국 API가 보완한 유효한 좌표가 있을 때만 지도에 표시합니다.
주소만 있는 시설도 목록에 포함하며 상세 화면의 주소 지도 검색을 제공합니다.
시설 목록은 페이지당 25개씩 표시하며, 지도에는 현재 검색 결과의 유효 좌표를 표시합니다.
전국 API에 운영시간/이용료가 없으면 `정보 없음`으로 표시하고 홈페이지·연락처를 안내합니다.

- 두 시설 API의 결과를 합집합으로 표시합니다. 자치구·정규화한 시설명·주소·종목이 모두
  일치하고, 상세주소가 충돌하지 않으며, 후보가 하나일 때만 통합합니다.
- 공백/문장부호와 서울시 명칭, 수영/수영장 같은 종목 표기만 정규화합니다.
  이름 유사도나 도로명/지번의 추측 변환으로 합치지 않습니다. 주소가 없거나 판단이 모호하면 독립 결과입니다.
- 서울시 값을 우선하고 누락된 정보만 전국 API로 보완합니다. 상세 화면에서 두 제공기관의 정보를 비교할 수 있습니다.
- 예약은 자치구·종목과 장소/서비스명을 대조합니다. 전체 시설 목록에서 연결 후보가 하나일 때만 표시합니다.
  장소명이 같은 다른 코트 등은 구분하며, 모호한 예약은 자동 연결하지 않습니다.
- 한 시설의 여러 일정은 `SVCID`별로 모두 표시합니다. 링크는 `yeyak.seoul.go.kr`만 허용합니다.
  예약 상태는 API 원문이며 최신 예약 가능 여부는 공식 페이지에서 확인합니다.

## 오류·캐시·페이지

키 미설정, API 오류, 정상 응답의 검색 결과 0건은 각각 다른 안내를 표시합니다.
한 서비스가 실패해도 다른 서비스나 이미 받은 페이지를 이용할 수 있습니다.
일부 페이지만 받은 경우 불완전한 결과임을 표시하며 전체 시설 수라고 설명하지 않습니다.
연결 타임아웃은 3.05초, 읽기 타임아웃은 12초입니다.
성공한 응답만 메모리에 캐시하고 시설 300초, 예약 60초 후 다시 읽습니다.
사이드바의 `API 정보 새로고침`으로 캐시를 비울 수 있습니다.
페이지당 500건, 서비스당 최대 100페이지이며 한도/반복 페이지/중간 실패는 일부 결과로 안내합니다.

## 구조와 검증

```text
oop-team-project/
├── app.py                       # 앱 실행과 화면 흐름
├── requirements.txt
├── .streamlit/
│   ├── secrets.example.toml     # 공개 가능한 빈 인증 설정
│   └── secrets.toml             # 실제 키 (Git 제외)
├── src/
│   ├── config.py                # 인증 설정, 자치구, 타임아웃·캐시·페이지 설정
│   ├── sports_facility.py       # 공통 시설 객체
│   ├── http_client.py           # HTTP 호출·오류·TTL 캐시
│   ├── normalization.py         # 텍스트·자치구·종목·좌표·링크 처리
│   ├── api_clients.py           # API 페이징·공공시설 선별·응답 매핑
│   ├── facility_manager.py      # 검색·중복 통합·예약 연결
│   └── views/
│       ├── common.py            # 공통 표시 함수와 API 상태 안내
│       ├── site_layout.py       # 홈·상단 메뉴·현황 준비 화면·푸터
│       ├── main_view.py         # 서울 지도·검색 폼·지도 선택
│       ├── detail_view.py       # 시설 카드·선택·상세·출처 링크
│       └── reservation_view.py  # 예약 일정과 공식 링크
├── tests/                       # 모의 API 및 Streamlit 앱 검증
├── assets/                      # 홈 대표 이미지와 사이트 스타일
└── docs/
    └── api-migration-verification.md
```

`app.py`가 API 데이터를 받아 Manager로 검색하고 각 화면 모듈을 호출합니다.
인증키 없이 테스트할 수 있으며 실제 설정 파일은 테스트에서 읽지 않습니다.

```powershell
python -B -m unittest discover -s tests -v
```

테스트는 네트워크나 실제 키 없이 실행합니다. 실제 앱을 모의 API로 실행하여 검색·선택·
상세·중복 제거·예약 표시·오류 격리·결과 없음 동작을 검증합니다.
실제 키를 사용하는 전체 데이터 조회와 별개입니다. 최근 실행 결과와 제한은
[전환 검증 기록](docs/api-migration-verification.md)에 기록합니다.

기존 저장소가 관리하던 `data/공공체육시설.csv`, 해당 전처리 스크립트와
`FacilityAnalyzer` 집계 모듈은 제거했습니다. 앱은 CSV 파일을 읽지 않습니다.
사용하지 않는 자치구 경계 GeoJSON과 빈 임시 주석 파일도 정리했습니다.
`local-context/`의 이전 개인 검증 메모와 샘플 앱은 과거 작업 기록이며 새 앱의 데이터 경로가 아닙니다.
개인 자료와 가상환경은 Git에서 제외하며 이번 정리에서 삭제하지 않았습니다.

## 팀

기존 팀원의 클래스와 화면 구조를 검색·상세 조회에 맞춰 발전시켰습니다.

| 이름 | 기존 담당 |
|---|---|
| 백다현 | 데이터 전처리 / SportsFacility |
| 박준혁 | FacilityManager |
| 강지원 | FacilityAnalyzer |
| 전종석 | 메인 대시보드 / 지도 |
| 이정기 | 상세 탐색 및 통합 |
