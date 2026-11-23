"""서울체육맵: 홈·시설 찾기·시설 현황의 화면 흐름을 연결한다."""

import streamlit as st

from src.config import ApiSettings, RESULT_PAGE_SIZE
from src.facility_manager import FacilityManager
from src.views.common import show_api_status
from src.views.detail_view import show_facility_cards, show_facility_profile
from src.views.main_view import MainView, select_facility
from src.views.reservation_view import show_reservations
from src.views.site_layout import HOME, OVERVIEW, SiteLayout


@st.cache_resource(show_spinner=False)
def get_manager(settings):
    return FacilityManager.from_settings(settings)


def _load_settings():
    try:
        return ApiSettings.from_environment(st.secrets)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return ApiSettings.from_environment()


def show_finder(manager):
    view = MainView()
    view.intro()
    with st.spinner("서울의 공공체육시설을 불러오고 있습니다…"):
        catalog = manager.load_data()
    query = st.session_state.get("search_query", ("", "", ""))
    results = manager.search(catalog.facilities, *query)
    by_id = {f.facility_id: f for f in results}
    if st.session_state.get("selected_facility_id") not in by_id:
        st.session_state.selected_facility_id = None
    focus_id = st.session_state.pop("focus_facility_id", None)
    if "result_page" not in st.session_state:
        focus_id = st.session_state.get("selected_facility_id")
    if focus_id in by_id:
        position = next(i for i, f in enumerate(results) if f.facility_id == focus_id)
        st.session_state.result_page = position // RESULT_PAGE_SIZE + 1
    view.show_map(results, st.session_state.get("selected_facility_id"))
    submitted, new_query = view.search_form(catalog.facilities)
    if submitted:
        st.session_state.search_query = new_query
        st.session_state.selected_facility_id = None
        st.session_state.result_page = 1
        st.rerun()

    available = any(s.state in {"ok", "partial"} for s in catalog.statuses)
    for status in catalog.statuses:
        if status.state != "ok":
            show_api_status(status)
    st.subheader(
        f"검색 결과 {len(results)}개" if available else "검색 결과를 불러올 수 없습니다"
    )
    if any(s.state != "ok" for s in catalog.statuses):
        st.caption(
            "조회 가능한 결과를 표시합니다. 일부 제공기관의 정보가 포함되지 않았을 수 있습니다."
        )
    if not results:
        st.info(
            "현재 조회 가능한 데이터에 검색 조건과 일치하는 시설이 없습니다."
            if available
            else "시설 데이터를 가져오지 못했습니다. 인증 설정 또는 API 상태를 확인해 주세요."
        )
    else:
        st.caption("시설 이름을 누르면 이용정보와 예약 안내가 열립니다.")
        left, right = st.columns([1.15, 1], gap="large")
        with left:
            show_facility_cards(results, st.session_state.get("selected_facility_id"))
        with right, st.container(border=True, key="facility_detail"):
            selected = by_id.get(st.session_state.get("selected_facility_id"))
            show_facility_profile(selected)
            if selected is not None:
                st.button(
                    "시설 선택 해제",
                    on_click=select_facility,
                    args=(None,),
                    key="clear_facility",
                )
                with st.spinner("공식 예약 일정을 확인하고 있습니다…"):
                    reservations = manager.get_reservations(
                        selected, catalog.facilities
                    )
                show_reservations(reservations)
    with st.expander("데이터 제공 및 조회 안내"):
        for status in catalog.statuses:
            show_api_status(status)
        st.caption(
            "시설 정보는 최대 5분, 예약 정보는 최대 1분간 재사용합니다. API에 없는 정보는 정보 없음으로 표시합니다."
        )
        st.button("API 정보 새로고침", on_click=manager.clear_cache, key="refresh_api")
        st.link_button(
            "서울시 시설 데이터",
            "https://data.seoul.go.kr/dataList/OA-21779/A/1/datasetView.do",
        )
        st.link_button(
            "전국 체육시설 데이터", "https://www.data.go.kr/data/15113986/openapi.do"
        )


def main():
    st.set_page_config(
        page_title="서울체육맵 · 내 일상 가까운 운동 공간",
        page_icon="🏃",
        layout="wide",
    )
    layout = SiteLayout()
    page = layout.header()
    if page == HOME:
        layout.home()
    elif page == OVERVIEW:
        layout.overview()
    else:
        show_finder(get_manager(_load_settings()))
    layout.footer()


if __name__ == "__main__":
    main()
