import json
import sys

import plotly.express as px
import streamlit as st

# src 폴더 안의 팀원 클래스를 불러올 수 있도록 경로 추가
sys.path.append("src")
from facility_analyzer import FacilityAnalyzer
from facility_manager import FacilityManager

st.set_page_config(page_title="서울체육맵", layout="wide")
st.title("서울시 체육시설은 어디에?")


# 1. 자치구 경계 불러오기 (한 번만 읽도록 캐싱)
@st.cache_data
def load_geojson():
    with open("data/seoul_districts.geojson", encoding="utf-8") as f:
        return json.load(f)


# 2. 시설 데이터와 분석기 준비 (한 번만 만들도록 캐싱)
@st.cache_resource
def load_data(district_names):
    manager = FacilityManager("data/공공체육시설.csv")
    analyzer = FacilityAnalyzer(manager.get_all_facilities(), district_names)
    return manager, analyzer


geo = load_geojson()
district_names = tuple(feat["properties"]["name"] for feat in geo["features"])
manager, analyzer = load_data(district_names)

# 3. 시설 종류 선택 (목록은 FacilityManager가 알려줌)
facility_type = st.selectbox("시설 종류", manager.get_facility_types())

# 4. 통계 요청 (계산은 FacilityAnalyzer가 함)
counts = analyzer.get_count_by_district(facility_type)
total = analyzer.get_total_count(facility_type)
top_districts, top_count = analyzer.get_top_district(facility_type)
coverage = analyzer.get_district_coverage(facility_type)

# 5. 지도 그리기
fig = px.choropleth(
    locations=list(counts.keys()),
    color=list(counts.values()),
    geojson=geo,
    featureidkey="properties.name",
    color_continuous_scale="Blues",
    labels={"color": "시설 수", "locations": "자치구"},
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=550, margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig, width="stretch")

# 6. 통계 카드 3개
if top_count == 0:
    top_text = "없음"
elif len(top_districts) == 1:
    top_text = f"{top_districts[0]} ({top_count}개)"
else:
    top_text = f"{top_districts[0]} 외 {len(top_districts) - 1}곳 ({top_count}개)"

c1, c2, c3 = st.columns(3)
c1.metric(f"서울 전체 {facility_type}", f"{total}개")
c2.metric("최다 보유 자치구", top_text)
c3.metric("보유 자치구", f"{coverage} / {len(district_names)}")