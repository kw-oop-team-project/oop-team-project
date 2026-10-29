import json
import random

import plotly.express as px
import streamlit as st

st.set_page_config(page_title="서울체육맵", layout="wide")
st.title("서울시 체육시설은 어디에?")

# 1. 시설 종류 선택
facility_type = st.selectbox("시설 종류", ["수영장", "축구장", "테니스장", "간이운동장"])

# 2. 자치구 경계 불러오기 (한 번만 읽도록 캐싱)
@st.cache_data
def load_geojson():
    with open("data/seoul_districts.geojson", encoding="utf-8") as f:
        return json.load(f)

geo = load_geojson()

# 3. 더미 데이터 (나중에 analyzer.get_count_by_district(facility_type)로 교체)
districts = [feat["properties"]["name"] for feat in geo["features"]]
rng = random.Random(facility_type)  # 같은 종류면 항상 같은 숫자가 나오게
counts = {d: rng.randint(0, 12) for d in districts}

# 4. 지도 그리기
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
st.plotly_chart(fig, use_container_width=True)

# 5. 통계 카드 3개
top = max(counts, key=counts.get)
c1, c2, c3 = st.columns(3)
c1.metric(f"서울 전체 {facility_type}", f"{sum(counts.values())}개")
c2.metric("최다 보유 자치구", f"{top} ({counts[top]}개)")
c3.metric("보유 자치구", f"{sum(v > 0 for v in counts.values())} / 25")