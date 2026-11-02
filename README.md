# 서울체육맵: 서울 공공체육시설 탐색 대시보드

서울시 공공체육시설을 **시설 종류별·자치구별 분포**로 비교하고, 원하는 지역의 체육시설 정보를 단계적으로 탐색할 수 있는 Streamlit 대시보드입니다.

> 객체지향프로그래밍 팀 프로젝트

---

## 1. 프로젝트 개요

- 사용자가 **시설 종류**를 선택하면 서울시 25개 자치구별 시설 수를 **지도와 주요 통계 카드**로 보여줍니다.
- 지도에서 **자치구를 선택**하면 해당 지역의 **시설 목록**과 **개별 시설 상세정보**를 확인할 수 있습니다.
- 간이운동장은 상세 자료가 일부만 제공되므로 **자치구별 집계에는 포함**하고, **상세 탐색에서는 제외**합니다.

### 실행 화면

![메인 대시보드](docs/images/main_dashboard.png)

---

## 2. 실행 방법

### 요구 사항
- Python 3.9 이상

### 설치 및 실행

```bash
# 1. 레포지토리 클론
git clone https://github.com/kw-oop-team-project/oop-team-project.git
cd oop-team-project

# 2. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. 라이브러리 설치
pip install -r requirements.txt

# 4. 실행
streamlit run app.py
```

실행 후 브라우저에서 `http://localhost:8501`이 자동으로 열립니다.

### 배포 주소
- Dashboard URL: (배포 후 추가 예정)

---

## 3. 사용 데이터

| 구분 | 데이터명 | 출처 | 용도 |
|---|---|---|---|
| 기본 데이터 | 서울시 공공체육시설 현황 | 서울 열린데이터광장 | 시설 정보, 종류별·자치구별 집계 |
| 추가 데이터 | 서울시 자치구 경계 (GeoJSON) | 행정동 경계 데이터를 자치구 단위로 가공 | 자치구별 분포 지도 |

- 자치구 경계는 행정동 경계 데이터를 자치구(`sggnm`) 기준으로 병합(dissolve)하여 생성했습니다. 변환 코드는 `scripts/make_districts.py`에 있습니다.
- 각 자치구 이름은 `properties.name`에 `"강남구"` 형식으로 저장되어 있습니다.

---

## 4. 클래스 설계

| 클래스 | 주요 책임 | 주요 속성 | 주요 메서드 |
|---|---|---|---|
| `SportsFacility` | 개별 공공체육시설 정보를 하나의 객체로 표현 | 시설명, 자치구, 시설 종류, 소유기관, 관리주체, 면적 | `get_info()`, `has_detail()` |
| `FacilityManager` | 원본 데이터를 불러와 시설 객체를 생성·저장하고 조건에 맞게 검색·필터링
