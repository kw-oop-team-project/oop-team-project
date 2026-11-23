"""시설 검색과 위치 탐색을 위한 메인 화면."""

from html import escape

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.config import DISTRICTS, FACILITY_CACHE_TTL, RESERVATION_CACHE_TTL


_API_LINKS = (
    (
        "서울시 시설 API 문서",
        "https://data.seoul.go.kr/dataList/OA-21779/A/1/datasetView.do",
    ),
    ("전국 시설 API 문서", "https://www.data.go.kr/data/15113986/openapi.do"),
    (
        "서울시 예약 API 문서",
        "https://data.seoul.go.kr/dataList/OA-2266/A/1/datasetView.do",
    ),
)


class MainView:
    def show_sidebar(self, manager):
        with st.sidebar:
            st.subheader("데이터 안내")
            st.write("서울시와 국민체육진흥공단의 서울 공공체육시설을 함께 검색합니다.")
            st.caption(
                f"시설 정보는 최대 {FACILITY_CACHE_TTL // 60}분, "
                f"예약 정보는 최대 {RESERVATION_CACHE_TTL // 60}분간 메모리에서 재사용합니다."
            )
            if st.button("API 정보 새로고침"):
                manager.clear_cache()
            for label, url in _API_LINKS:
                st.link_button(label, url)

    def search_form(self):
        with st.form("facility_search"):
            district_col, name_col, sport_col = st.columns([1, 2, 1])
            district = district_col.selectbox(
                "자치구", ["서울 전체", *DISTRICTS], key="search_district"
            )
            name = name_col.text_input(
                "시설명", placeholder="예: 구민체육센터", key="search_name"
            )
            sport = sport_col.text_input(
                "종목", placeholder="예: 수영, 테니스", key="search_sport"
            )
            submitted = st.form_submit_button("시설 검색", type="primary")
        return submitted, (
            "" if district == "서울 전체" else district,
            name.strip(),
            sport.strip(),
        )

    def show_map(self, facilities):
        located = [
            f for f in facilities if f.latitude is not None and f.longitude is not None
        ]
        st.subheader("시설 위치")
        if not located:
            st.info(
                "현재 결과에 위치 좌표가 없습니다. 시설 상세의 주소와 지도 검색을 이용해 주세요."
            )
            return
        points = pd.DataFrame(
            [
                {
                    "lat": f.latitude,
                    "lon": f.longitude,
                    "name": escape(f.name),
                    "address": escape(f.address),
                    "sport": escape(f.facility_type),
                }
                for f in located
            ]
        )
        layer = pdk.Layer(
            "ScatterplotLayer",
            points,
            get_position="[lon, lat]",
            get_fill_color=[33, 113, 181, 210],
            get_radius=100,
            radius_min_pixels=6,
            pickable=True,
        )
        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=pdk.ViewState(
                    latitude=float(points.lat.mean()),
                    longitude=float(points.lon.mean()),
                    zoom=10.5,
                ),
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={"html": "<b>{name}</b><br/>{sport}<br/>{address}"},
            )
        )
        st.caption(
            f"좌표가 제공된 {len(located)}개 시설을 표시합니다. 목록에서 시설을 선택해 상세정보를 확인하세요."
        )
