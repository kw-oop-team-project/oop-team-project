import sys

import streamlit as st

# src 폴더를 import 경로에 추가
sys.path.append("src")
from facility_manager import FacilityManager
from facility_analyzer import FacilityAnalyzer
from views.main_view import MainView, load_geojson

st.set_page_config(page_title="서울체육맵", layout="wide")
st.title("서울시 체육시설은 어디에?")
st.caption("2024년 서울시 공공체육시설 현황")

@st.cache_resource
def load_data():
    """시설 데이터를 불러오고 분석기를 만듦 (한 번만 실행)"""
    geo = load_geojson()
    district_names = [feat["properties"]["name"] for feat in geo["features"]]
    manager = FacilityManager("data/공공체육시설.csv")
    analyzer = FacilityAnalyzer(manager.get_all_facilities(), district_names)
    return manager, analyzer

manager, analyzer = load_data()

# 메인 화면
main_view = MainView(manager, analyzer)
selected_type = main_view.render()