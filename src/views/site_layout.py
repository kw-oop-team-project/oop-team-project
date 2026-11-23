"""첫 화면, 상단 메뉴와 공통 사이트 레이아웃."""

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets"
HOME, FINDER, OVERVIEW = "홈", "체육시설 찾기", "체육시설 현황"


@lru_cache(maxsize=1)
def hero_data_url():
    data = base64.b64encode((ASSET_DIR / "sports-hero.png").read_bytes()).decode(
        "ascii"
    )
    return "data:image/png;base64," + data


def navigate(page):
    st.session_state.main_navigation = page


class SiteLayout:
    def header(self):
        st.markdown(
            f"<style>{(ASSET_DIR / 'site.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """<div class="site-brand"><div class="brand-name">
            <span class="brand-mark" aria-hidden="true">S</span><div>
            <div class="brand-title">서울체육맵</div><div class="brand-subtitle">SEOUL SPORTS MAP</div>
            </div></div><div class="brand-note">서울의 일상에, 운동을 더 가깝게</div></div>""",
            unsafe_allow_html=True,
        )
        return st.radio(
            "주요 메뉴",
            [HOME, FINDER, OVERVIEW],
            horizontal=True,
            label_visibility="collapsed",
            key="main_navigation",
        )

    def home(self):
        st.markdown(
            f"""<section class="hero" aria-label="서울 공공체육시설 찾기 소개"
            style="background-image:linear-gradient(90deg,rgba(8,31,59,.88),rgba(8,31,59,.48) 48%,rgba(8,31,59,.03)),url('{hero_data_url()}')">
            <div class="hero-content"><div class="eyebrow">MOVE YOUR EVERYDAY</div>
            <h1>가까운 곳에서,<br>더 즐거운 움직임.</h1>
            <p>서울 곳곳의 공공체육시설을 한눈에.<br>내가 찾던 운동 공간과 예약 안내를 만나보세요.</p>
            </div></section><div class="hero-note">서비스 소개를 위해 생성한 체육 이미지입니다.</div>""",
            unsafe_allow_html=True,
        )
        left, right = st.columns(2, gap="large")
        with left, st.container(border=True, key="home_find"):
            st.markdown(
                """<div class="service-card"><span class="service-label">FIND YOUR PLACE</span>
                <h2>우리 동네 체육시설 찾기</h2><p>서울 지도에서 위치를 살펴보고,<br>자치구와 종목으로 나에게 맞는 시설을 찾아보세요.</p></div>""",
                unsafe_allow_html=True,
            )
            st.button(
                "지도에서 시설 찾기",
                type="primary",
                on_click=navigate,
                args=(FINDER,),
                key="home_find_button",
                use_container_width=True,
            )
        with right, st.container(border=True, key="home_stats"):
            st.markdown(
                """<div class="service-card"><span class="service-label">SEOUL SPORTS INSIGHT</span>
                <h2>서울시 공공체육시설 현황</h2><p>서울의 체육시설 현황을 살펴보는 공간.<br>더 유용한 정보를 담아 준비하고 있습니다.</p></div>""",
                unsafe_allow_html=True,
            )
            st.button(
                "시설 현황 살펴보기",
                on_click=navigate,
                args=(OVERVIEW,),
                key="home_overview_button",
                use_container_width=True,
            )
        st.markdown(
            """<div class="steps"><div class="step"><span>EXPLORE</span><strong>지도에서 둘러보기</strong><p>지도를 확대하고 이동하며 가까운 운동 공간을 확인하세요.</p></div>
            <div class="step"><span>FIND</span><strong>지역과 종목으로 찾기</strong><p>원하는 자치구와 종목을 선택하면 시설 목록이 나타납니다.</p></div>
            <div class="step"><span>VISIT</span><strong>상세정보와 예약 확인</strong><p>운영시간과 이용료를 확인하고 공식 예약 페이지로 이동하세요.</p></div></div>""",
            unsafe_allow_html=True,
        )

    def overview(self):
        st.markdown(
            """<div class="section-heading"><div class="eyebrow">SEOUL SPORTS INSIGHT</div>
            <h1>서울시 공공체육시설 현황</h1><p>서울의 운동 공간을 더 깊이 알아보는 곳</p></div>
            <section class="coming-soon"><div class="eyebrow">COMING SOON</div><h2>새로운 정보를 준비하고 있습니다</h2>
            <p>공공체육시설 현황은 다음 단계에서 제공할 예정입니다.<br>지금은 체육시설 찾기에서 원하는 운동 공간을 만나보세요.</p></section>""",
            unsafe_allow_html=True,
        )
        st.button(
            "체육시설 찾기로 이동", on_click=navigate, args=(FINDER,), type="primary"
        )

    def footer(self):
        st.markdown(
            """<footer class="site-footer"><div><strong>서울체육맵</strong><br>서울의 운동 공간을 더 가깝게</div>
            <div>데이터 제공 · 서울 열린데이터광장 / 국민체육진흥공단<br>운영 및 예약 정보는 해당 시설과 공식 예약 페이지에서 최종 확인해 주세요.</div></footer>""",
            unsafe_allow_html=True,
        )
