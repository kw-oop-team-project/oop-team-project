"""서울체육맵: 공공 API 기반 시설 검색·상세·예약 안내."""

import streamlit as st

from src.config import ApiSettings
from src.facility_manager import FacilityManager
from src.views.main_view import MainView
from src.views.common import show_api_status
from src.views.detail_view import (
    show_detail,
    show_facility_links,
    show_paged_facility_list,
)
from src.views.reservation_view import show_reservations


@st.cache_resource(show_spinner=False)
def get_manager(settings):
    return FacilityManager.from_settings(settings)


def main():
    st.set_page_config(page_title="서울체육맵 · 공공체육시설 찾기", layout="wide")
    st.title("서울체육맵")
    st.caption("우리 동네 공공체육시설 찾기 · 상세정보와 공식 예약 안내")
    try:
        settings = ApiSettings.from_environment(st.secrets)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        settings = ApiSettings.from_environment()
    manager = get_manager(settings)
    view = MainView()
    view.show_sidebar(manager)
    submitted, query = view.search_form()
    if submitted:
        st.session_state.search_query = query
        st.session_state.selected_facility_id = None
    if "search_query" not in st.session_state:
        st.info(
            "자치구·시설명·종목을 입력하고 시설 검색을 눌러 주세요. 조건을 비우면 전체 공공시설을 찾습니다."
        )
        if not settings.seoul_key:
            st.warning(
                "서울시 API 키 미설정: SEOUL_OPEN_API_KEY를 환경변수 또는 Streamlit secrets에 설정해 주세요."
            )
        if not settings.national_key:
            st.warning(
                "전국체육시설 API 키 미설정: DATA_GO_KR_SERVICE_KEY를 환경변수 또는 Streamlit secrets에 설정해 주세요."
            )
        return
    with st.spinner("공공체육시설을 조회하고 있습니다…"):
        catalog = manager.load_data()
    for status in catalog.statuses:
        show_api_status(status)
    district, name, sport = st.session_state.search_query
    results = manager.search(catalog.facilities, district, name, sport)
    available = any(s.state in {"ok", "partial"} for s in catalog.statuses)
    st.subheader(
        f"검색 결과 {len(results)}개" if available else "검색 결과를 불러올 수 없습니다"
    )
    if any(s.state != "ok" for s in catalog.statuses):
        st.caption(
            "정상 응답한 API와 이미 조회된 페이지의 결과를 표시합니다. 전체 시설을 포함하지 않을 수 있습니다."
        )
    if not results:
        if available:
            st.info("현재 조회 가능한 데이터에 검색 조건과 일치하는 시설이 없습니다.")
        else:
            st.info(
                "시설 데이터를 가져오지 못했습니다. 위의 키 설정 또는 API 오류를 확인해 주세요."
            )
        return

    left, right = st.columns([1.2, 1])
    with left:
        view.show_map(results)
        selected_id = show_paged_facility_list(
            results, st.session_state.get("selected_facility_id")
        )
    st.session_state.selected_facility_id = selected_id
    selected = next((f for f in results if f.facility_id == selected_id), None)
    with right:
        show_detail(selected)
        if selected is not None:
            show_facility_links(selected)
            with st.spinner("예약 일정을 확인하고 있습니다…"):
                reservations = manager.get_reservations(selected, catalog.facilities)
            show_reservations(reservations)


if __name__ == "__main__":
    main()
