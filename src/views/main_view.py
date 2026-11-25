"""서울 지도와 지역·종목별 시설 탐색 화면."""

from html import escape

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.config import DISTRICTS
from src.normalization import sport_key


def map_facility_id(event, allowed_ids):
    """지도 선택 정보에서 현재 표시 중인 시설의 ID만 읽는다."""
    objects = (
        (event or {}).get("selection", {}).get("objects", {}).get("facilities", [])
    )
    if not objects or not isinstance(objects[0], dict):
        return None
    facility_id = objects[0].get("facility_id")
    return facility_id if facility_id in allowed_ids else None


def select_facility(facility_id):
    st.session_state.selected_facility_id = facility_id
    st.session_state.focus_facility_id = facility_id


def clear_search():
    st.session_state.search_query = ("", "", "")
    st.session_state.search_district = "서울 전체"
    st.session_state.search_sport = "전체 종목"
    st.session_state.search_name = ""
    st.session_state.selected_facility_id = None
    st.session_state.result_page = 1
    st.session_state.pop("focus_facility_id", None)


def _map_selected(allowed_ids):
    selected = map_facility_id(st.session_state.get("facility_map"), allowed_ids)
    if selected:
        select_facility(selected)


class MainView:
    def intro(self):
        st.markdown(
            """<div class="section-heading"><div class="eyebrow">FIND A PLACE TO MOVE</div>
            <h1>우리 동네, 운동할 곳</h1><p>서울 지도에서 가까운 체육시설을 둘러보세요.<br>
            아래에서 자치구와 종목을 선택하면 원하는 시설을 더 쉽게 찾을 수 있습니다.</p></div>""",
            unsafe_allow_html=True,
        )

    def search_form(self, facilities):
        district, name, sport = st.session_state.get("search_query", ("", "", ""))
        st.session_state.setdefault("search_district", district or "서울 전체")
        st.session_state.setdefault("search_name", name)
        st.session_state.setdefault("search_sport", sport or "전체 종목")
        sports = sorted(
            {
                sport_key(f.facility_type)
                for f in facilities
                if sport_key(f.facility_type)
            }
        )
        options = ["전체 종목", *sports]
        if st.session_state.get("search_sport", "전체 종목") not in options:
            st.session_state.search_sport = "전체 종목"
        st.markdown(
            '<div id="facility-filter" class="section-heading"><div class="eyebrow">FIND YOUR FACILITY</div><h2>지역과 종목으로 찾아보세요</h2></div>',
            unsafe_allow_html=True,
        )
        with st.form("facility_search"):
            district_col, sport_col, name_col = st.columns([1, 1, 2])
            district = district_col.selectbox(
                "자치구", ["서울 전체", *DISTRICTS], key="search_district"
            )
            sport = sport_col.selectbox("종목", options, key="search_sport")
            name = name_col.text_input(
                "시설명",
                placeholder="찾으시는 시설 이름을 입력하세요",
                key="search_name",
            )
            submitted = st.form_submit_button(
                "시설 검색", type="primary", use_container_width=True
            )
        st.button("검색 조건 초기화", on_click=clear_search, key="reset_search")
        return submitted, (
            "" if district == "서울 전체" else district,
            name.strip(),
            "" if sport == "전체 종목" else sport,
        )

    def show_map(self, facilities, selected_id=None):
        located = [
            f for f in facilities if f.latitude is not None and f.longitude is not None
        ]
        st.subheader("서울시 공공체육시설 지도")
        points = pd.DataFrame(
            [
                {
                    "lat": f.latitude,
                    "lon": f.longitude,
                    "name": escape(f.name),
                    "address": escape(f.address),
                    "sport": escape(f.facility_type),
                    "facility_id": f.facility_id,
                    "color": [198, 245, 107, 255]
                    if f.facility_id == selected_id
                    else [23, 100, 232, 210],
                    "radius": 115 if f.facility_id == selected_id else 60,
                }
                for f in located
            ],
            columns=[
                "lat",
                "lon",
                "name",
                "address",
                "sport",
                "facility_id",
                "color",
                "radius",
            ],
        )
        selected = next((f for f in located if f.facility_id == selected_id), None)
        if selected:
            latitude, longitude, zoom = selected.latitude, selected.longitude, 12.5
        elif located:
            latitude, longitude = float(points.lat.mean()), float(points.lon.mean())
            zoom = 10.2 if len({f.district for f in located}) > 1 else 12
        else:
            latitude, longitude, zoom = 37.5665, 126.9780, 10.2
        layer = pdk.Layer(
            "ScatterplotLayer",
            points,
            id="facilities",
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius="radius",
            radius_min_pixels=5,
            radius_max_pixels=14, # 지도확대시 점 크기 제한
            get_line_color=[255, 255, 255],
            line_width_min_pixels=1,
            stroked=True,
            pickable=True,
            auto_highlight=True,
        ) 
        allowed_ids = {f.facility_id for f in located}
        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=pdk.ViewState(
                    latitude=latitude, longitude=longitude, zoom=zoom
                ),
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                tooltip={"html": "<b>{name}</b><br/>{sport}<br/>{address}"},
            ),
            height=540,
            key="facility_map",
            on_select=lambda: _map_selected(allowed_ids),
            selection_mode="single-object",
        )
        if not located:
            st.info(
                "현재 결과에 위치 좌표가 없습니다. 아래 목록과 상세 주소로 시설을 확인해 주세요."
            )
        else:
            st.caption(
                f"지도에 {len(located):,}개 시설을 표시합니다. 표시를 누르면 아래에서 상세정보와 예약 안내를 확인할 수 있습니다."
            )
        missing = len(facilities) - len(located)
        if missing:
            st.caption(
                f"좌표가 제공되지 않은 {missing:,}개 시설도 아래 검색 목록에는 포함됩니다."
            )
