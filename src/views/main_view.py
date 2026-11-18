import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

GEOJSON_PATH = "data/seoul_districts.geojson"

BINS = ["0개", "1-2개", "3-5개", "6-9개", "10개 이상"]
BIN_COLORS = {
    "0개": "#EEF3FA",
    "1-2개": "#C6DBEF",
    "3-5개": "#6BAED6",
    "6-9개": "#2171B5",
    "10개 이상": "#08306B",
}
DARK_BINS = ["6-9개", "10개 이상"] # 이 구간은 글자를 흰색으로

@st.cache_data
def load_geojson():
    """자치구 경계 파일을 한 번만 읽어서 재사용"""
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def to_bin(count):
    """시설 수를 색상 구간 이름으로 바꿈"""
    if count == 0: return "0개"
    elif count <= 2: return "1-2개"
    elif count <= 5: return "3-5개"
    elif count <= 9: return "6-9개"
    else: return "10개 이상"

def get_district_centers(geo):
    """자치구마다 이름을 쓸 위치를 계산"""
    centers ={}
    for feat in geo["features"]:
        polygons = feat["geometry"]["coordinates"]
        if feat["geometry"]["type"] == "Polygon":
            polygons = [polygons]
        ring = max((polygon[0] for polygon in polygons), key=len)

        area = cx = cy = 0
        for (x1,y1),(x2,y2) in zip(ring, ring[1:]):
            cross = x1 * y2 - x2 * y1
            area += cross
            cx += (x1 + x2) * cross
            cy += (y1 + y2) * cross
        centers[feat["properties"]["name"]] = (cx / (3*area), cy / (3*area))
    return centers

class MainView:
    """메인 화면: 시설 종류 선택, 자치구별 분포 지도, 핵심 통계 카드"""

    def __init__(self, manager, analyzer):
        self._manager = manager
        self._analyzer = analyzer
        self._geo = load_geojson()
        self._centers = get_district_centers(self._geo)

    #시설 종류 선택
    def select_facility_type(self):
        """시설 종류 선택창을 보여주고, 고른 종류를 돌려줌"""
        return st.selectbox("시설 종류", self._manager.get_facility_types())

    #지도 그리기
    def show_map(self, facility_type):
        """자치구별 시설 수를 색으로 칠한 지도를 그림"""
        counts = self._analyzer.get_count_by_district(facility_type)

        df = pd.DataFrame({
            "자치구": list(counts.keys()),
            "시설 수": list(counts.values()),
        })
        df["구간"] = df["시설 수"].apply(to_bin)

        fig = px.choropleth(
            df,                                         # 표를 넘김
            geojson=self._geo,
            locations="자치구",                          # 표의 "자치구" 열
            featureidkey="properties.name",
            color="구간",                                # 숫자 대신 구간으로 색칠
            color_discrete_map=BIN_COLORS,               # 구간별 색 지정
            category_orders={"구간": BINS},              # 범례 순서
            hover_name="자치구",
            hover_data={"자치구": False, "구간": False, "시설 수": True},
        )
        fig.update_traces(marker_line_color="white", marker_line_width=1)  # 구 경계선 흰색

        # 구 이름 글자 올리기
        names = list(self._centers.keys())
        fig.add_trace(go.Scattergeo(
            lon=[self._centers[name][0] for name in names],
            lat=[self._centers[name][1] for name in names],
            text=names,
            mode="text",
            textfont=dict(
                size=12,
                color=["white" if to_bin(counts.get(name, 0)) in DARK_BINS else "#14213D"
                       for name in names],
            ),
            hoverinfo="skip",
            showlegend=False,
        ))
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(title_text=f"{facility_type} 수", y=0.5),
        )
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