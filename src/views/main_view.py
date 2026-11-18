import json

import plotly.express as px
import streamlit as st

GEOJSON_PATH = "data/seoul_districts.geojson"

@st.cache_data
def load_geojson():
    """자치구 경계 파일을 한 번만 읽어서 재사용"""
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

class MainView:
    """메인 화면: 시설 종류 선택, 자치구별 분포 지도, 핵심 통계 카드"""

    def __init__(self, manager, analyzer):
        self._manager = manager
        self._analyzer = analyzer
        self._geo = load_geojson()

    #시설 종류 선택
    def select_facility_type(self):
        """시설 종류 선택창을 보여주고, 고른 종류를 돌려줌"""
        return st.selectbox("시설 종류", self._manager.get_facility_types())

    #지도 그리기
    def show_map(self, facility_type):
        """자치구별 시설 수를 색으로 칠한 지도를 그림"""
        counts = self._analyzer.get_count_by_district(facility_type)

        fig = px.choropleth(
            locations = list(counts.keys()),
            color = list(counts.values()),
            geojson = self._geo,
            featureidkey = "properties.name",
            color_continuous_scale = "Viridis",
            labels = {"color": "시설 수", "locations": "자치구"}
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=550, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width = "stretch")

    #통계 카드
    def show_summary(self, facility_type):
        """통계 카드 3개를 보여줌"""
        total = self._analyzer.get_total_count(facility_type)
        top_districts, top_count = self._analyzer.get_top_district(facility_type)
        coverage = self._analyzer.get_district_coverage(facility_type)

        if top_count == 0:
            top_text = "없음"
        elif len(top_districts) == 1:
            top_text = f"{top_districts[0]} ({top_count}개)"
        else:
            top_text = f"{top_districts[0]} 외 {len(top_districts)-1}개 자치구 ({top_count}개)"

        c1, c2, c3 = st.columns(3)
        c1.metric(f"서울 전체 {facility_type}", f"{total}개")
        c2.metric("최다 보유 자치구", top_text)
        c3.metric("보유 자치구", f"{coverage} / 25")

    def render(self):
        """메인 화면을 그림"""
        facility_type = self.select_facility_type()
        self.show_map(facility_type)
        self.show_summary(facility_type)
        return facility_type