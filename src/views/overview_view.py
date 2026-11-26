"""통계 전용 현황 화면. 시설 목록·검색 연결·예약 호출을 제공하지 않는다."""

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from ..api_clients import NATIONAL, SEOUL
from ..config import DISTRICTS
from ..facility_analyzer import ALL_TYPES, FacilityAnalyzer
from .common import show_api_status

from .facility_chart import FacilityChart

BOUNDARY_PATH = (
    Path(__file__).resolve().parents[2] / "assets" / "seoul-districts-2015.geojson"
)


@lru_cache(maxsize=1)
def district_boundaries():
    geo = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    names = [f["properties"]["SIG_KOR_NM"] for f in geo["features"]]
    if len(names) != 25 or set(names) != set(DISTRICTS):
        raise ValueError("서울 25개 자치구 경계가 일치하지 않습니다.")
    return geo


def district_map_spec(counts, pie_images=None, pie_counts=None, diversity=None):
    """지역 집계만 브라우저에 전달한다."""
    features = deepcopy(district_boundaries()["features"])

    for feature in features:
        name = feature["properties"]["SIG_KOR_NM"]

        properties = {
            "district": name,
            "count": counts[name]
        }

        if pie_counts:
            properties["title"] = (
                f"자치구: {name}\n"
                f"등록자료(건): {counts[name]:,}"
            )

            if diversity is not None:
                properties["title"] += (
                    f"\n시설 종류 수(종): {diversity[name]}"
                )

            properties["image"] = pie_images.get(name) or ""

            for i in range(FacilityChart.TOP_N + 1):
                properties[f"legend_{i}"] = ""

            total = counts[name]

            for i, (kind, count) in enumerate(pie_counts[name].items()):
                ratio = count / total * 100

                properties[f"legend_{i}"] = (
                    f"{kind}  {count:,}건 ({ratio:.1f}%)"
                )

        feature["properties"] = properties
            
    return {
        "data": {"values": features},
        "projection": {"type": "mercator"},
        "mark": {"type": "geoshape", "stroke": "white", "strokeWidth": 1.4},
        "encoding": {
            "color": {
                "condition": {
                    "test": "datum.properties.count === 0",
                    "value": "#edf1f6",
                },
                "field": "properties.count",
                "type": "quantitative",
                "scale": {
                    "scheme": "blues",
                    "domain": [0, max(1, max(counts.values(), default=0))],
                },
                "legend": {"title": "등록자료(건)", "orient": "bottom", "format": "d"},
            },
            "tooltip": (
                [
                    {
                        "field": "properties.title",
                        "type": "nominal",
                        "title": "title",
                    },
                    {
                        "field": "properties.image",
                        "type": "nominal",
                        "title": "image",
                    },
                ] + [
                    {
                        "field": f"properties.legend_{i}",
                        "type": "nominal",
                        "title": f"범례{i + 1}",
                    }
                    for i in range(FacilityChart.TOP_N + 1)
                ]
                if pie_counts else [
                    {
                        "field": "properties.district",
                        "type": "nominal",
                        "title": "자치구",
                    },
                    {
                        "field": "properties.count",
                        "type": "quantitative",
                        "title": "등록자료(건)",
                        "format": ",d",
                    },
                ]
            ),
        },
        "height": 500,
        "config": {"view": {"stroke": None}},
    }


def count_table(counts, label):
    total = sum(counts.values())
    return pd.DataFrame(
        [
            {
                label: name,
                "등록 시설 수(건)": count,
                "비중(%)": 100 * count / total if total else 0.0,
            }
            for name, count in counts.items()
        ],
        columns=[label, "등록 시설 수(건)", "비중(%)"],
    )


def bar_spec(label, height):
    return {
        "mark": {"type": "bar", "color": "#1764e8", "cornerRadiusEnd": 4},
        "encoding": {
            "y": {
                "field": label,
                "type": "nominal",
                "sort": "-x",
                "title": None,
                "axis": {
                    "labelLimit": 220,
                    "labelOverlap": False,
                    "labelFontSize": 11,
                    "labelFlush": False,
                    "labelBaseline": "middle",
                },
            },
            "x": {
                "field": "등록 시설 수(건)",
                "type": "quantitative",
                "title": "등록자료(건)",
                "axis": {"tickMinStep": 1},
            },
            "tooltip": [
                {"field": label, "type": "nominal"},
                {"field": "등록 시설 수(건)", "type": "quantitative", "format": ",d"},
                {"field": "비중(%)", "type": "quantitative", "format": ".1f"},
            ],
        },
        "height": height,
        "config": {"view": {"stroke": None}},
    }

def pie_tooltip_style():
    selector = "#vg-tooltip-element:has(> h2)"

    styles = f"""
    {selector} h2 {{
        white-space: pre-line;
        border-bottom: 1px solid #d1d5db;
        padding-bottom: 8px;
        margin-bottom: 8px;
        text-align: left;
    }}

    {selector} img {{
        display: block;
        margin: 8px auto;
        width: 150px;
    }}

    {selector} td.key {{
        font-size: 0;
    }}

    {selector} tr:has(td.value:empty) {{
        display: none;
    }}

    {selector} td.key::before {{
        content: "";
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 2px;
        margin-right: 5px;
    }}
    """

    for i, color in enumerate(FacilityChart.COLORS, start=1):
        styles += f"""
        {selector} tr:nth-child({i}) td.key::before {{
            background-color: {color};
        }}
        """

    return f"<style>{styles}</style>"

class OverviewView:
    def render(self, service):
        st.html(pie_tooltip_style())
        st.html(
            """<style>
        .overview-intro { padding:28px 0 18px; }
        .overview-intro h1 { font-size:38px; margin:0 0 12px; }
        .overview-intro p { color:#64748b; line-height:1.8; }
        .st-key-overview_metrics [data-testid="stMetric"] { background:#f3f7ff; border:1px solid #e0e9f6; border-radius:14px; padding:20px; height:100%; }
        .st-key-overview_metrics [data-testid="stMetricValue"] { color:#102b49; font-size:clamp(22px,3vw,34px); }
        @media(max-width:850px) { .overview-intro h1 { font-size:30px; } }
        </style><div class="overview-intro"><div class="eyebrow">SEOUL SPORTS INSIGHT</div>
        <h1>서울시 공공체육시설 현황</h1><p>서울의 운동 공간은 어떻게 분포되어 있을까요?<br>
        제공기관의 등록자료를 기준으로 자치구별 분포와 시설 종류를 비교합니다.</p></div>""",
        )

        saved = st.session_state.get("overview_filters", (NATIONAL, ALL_TYPES, True))
        for key, value in zip(
            ("overview_source", "overview_type", "overview_simple"), saved
        ):
            st.session_state.setdefault(key, value)
        with st.container(border=True, key="overview_filters_panel"):
            source_col, type_col, simple_col = st.columns([1.4, 1.4, 1])
            source = source_col.selectbox(
                "통계 출처", [NATIONAL, SEOUL], key="overview_source"
            )
            include_simple = simple_col.checkbox(
                "간이운동장 포함", key="overview_simple"
            )
            refresh = st.button("통계 새로고침", key="overview_refresh")
            with st.spinner("선택한 출처의 등록자료를 집계하고 있습니다…"):
                snapshot = service.load(source, refresh=refresh)
            result = snapshot.result
            analyzer = FacilityAnalyzer(result.items)
            types = [ALL_TYPES, *analyzer.get_types(include_simple)]
            if st.session_state.overview_type not in types:
                st.session_state.overview_type = ALL_TYPES
            facility_type = type_col.selectbox("시설 종류", types, key="overview_type")
            st.session_state.overview_filters = (source, facility_type, include_simple)

        show_api_status(result)
        timestamp = snapshot.fetched_at.strftime("%Y-%m-%d %H:%M:%S KST")
        st.caption(
            f"선택 출처: {source} · {'조회 완료' if result.state == 'ok' else '조회 시도'}: {timestamp} · 정상 응답은 최대 5분간 재사용합니다."
        )
        if result.state not in {"ok", "partial"}:
            st.info(
                "선택한 출처의 통계를 불러올 수 없습니다. 인증 설정을 확인하거나 통계 출처를 변경해 주세요."
            )
            return
        partial = result.state == "partial"
        if partial:
            st.warning(
                "일부 페이지의 수신 자료만 집계했습니다. 아래 수치·순위는 전체 현황이 아니며, 0건인 지역도 실제 시설이 없다는 뜻은 아닙니다."
            )

        summary = analyzer.get_summary(facility_type, include_simple)

        counts = summary["district_counts"]
        total = summary["total"]
        leaders = summary["leaders"]
        maximum = summary["maximum"]
        leader_label = (
            " · ".join(leaders)
            if len(leaders) <= 2
            else f"{len(leaders)}개 자치구 공동"
        )
        with st.container(key="overview_metrics"):
            total_col, top_col, coverage_col = st.columns(3)
            total_col.metric(
                "수신 자료 중 등록 시설 수" if partial else "등록 시설 수",
                f"{total:,}건",
            )
            top_col.metric(
                "수신 자료 중 최다 자치구" if partial else "최다 등록 자치구",
                leader_label or "해당 없음",
                help="같은 건수이면 공동 최다로 표시합니다.",
            )
            coverage_col.metric(
                "수신 자료가 있는 자치구" if partial else "시설 보유 자치구",
                f"{summary['coverage']} / 25",
            )
        if leaders:
            title = "공동 최다" if len(leaders) > 1 else "최다 등록"
            st.caption(
                f"{'수신 자료 중 ' if partial else ''}{title}: {' · '.join(leaders)} · 각 {maximum:,}건"
            )
        st.caption(
            f"집계 조건: {facility_type} · 간이운동장 {'포함' if include_simple else '제외'} · 제공기관별 시설 ID 기준 등록자료이며 실제 건물·코트 수와 다를 수 있습니다."
        )
        if not total:
            st.info(
                "수신 자료 중 선택한 조건에 해당하는 등록 시설이 0건입니다."
                if partial
                else "선택한 조건에 해당하는 등록 시설이 0건입니다."
            )
        
        pie_images = {}
        pie_counts = {}
        diversity = {}

        if facility_type == ALL_TYPES:
            district_type_counts = summary["district_type_counts"]
            diversity = summary["diversity"]

            chart = FacilityChart()

            for district, type_counts in district_type_counts.items():
                top_counts = analyzer.get_top_type_counts(
                    type_counts, top_n=FacilityChart.TOP_N
                )

                pie_counts[district] = top_counts
                pie_images[district] = chart.create_pie_chart(top_counts)

        district_data = count_table(counts, "자치구")
        with st.container(border=True):
            st.subheader("자치구별 분포")
            map_col, graph_col = st.columns([1.1, 1])
            with map_col:
                try:
                    st.vega_lite_chart(
                        spec=district_map_spec(counts, pie_images, pie_counts, diversity),
                        width="stretch",
                        key="overview_map",
                    )
                except (OSError, ValueError, KeyError):
                    st.warning(
                        "경계 지도를 표시할 수 없습니다. 자치구별 그래프와 집계표에서 수치를 확인해 주세요."
                    )

            with graph_col:
                district_chart_data = district_data.copy()
                district_chart_spec = bar_spec("자치구", 500)

                if facility_type == ALL_TYPES:

                    district_chart_data["시설 종류 수"] = (
                        district_chart_data["자치구"].map(diversity)
                    )

                    district_chart_spec["encoding"]["tooltip"].append(
                        {
                            "field": "시설 종류 수",
                            "title": "시설 종류 수(종)",
                            "type": "quantitative",
                            "format": "d",
                        }
                    )

                st.vega_lite_chart(
                    district_chart_data,
                    spec=district_chart_spec,
                    width="stretch",
                    key="overview_district_chart",
                )

            st.caption(
                "색이 진할수록 등록자료가 많습니다. 회색 지역은 이번 집계에서 0건인 지역입니다."
            )
            st.caption(
                "지역 위에 마우스를 올리면 자치구명과 등록 건수가 표시됩니다.  \n"
                "전체 종류 선택 시 시설 종류 수와 종류별 구성 비율을 원형 그래프로 확인할 수 있습니다.  \n"
                f"원형 그래프는 상위 {FacilityChart.TOP_N}개 시설 종류를 표시하며, 나머지는 기타로 합산합니다."
            )
            st.caption(
                "지도 경계: JUSO 2015 / southkorea-seoul-maps (Apache 2.0). "
                "시설 데이터의 기준 연도를 뜻하지 않습니다."
            )

        type_counts = summary["type_counts"]
        type_data = count_table(type_counts, "시설 종류")
        with st.container(border=True):
            st.subheader("시설 종류별 구성")
            st.caption(
                "제공기관의 시설 분류를 그대로 사용합니다. 위에서 선택한 조건과 동일한 자료를 집계하며, 종류 하나를 선택하면 해당 종류만 표시합니다."
            )
            if total:
                st.vega_lite_chart(
                    type_data,
                    spec=bar_spec("시설 종류", max(150, 25 * len(type_counts))),
                    width="stretch",
                    key="overview_type_chart",
                )
            else:
                st.caption("표시할 종류별 구성 자료가 없습니다.")

        with st.container(border=True):
            st.subheader("집계표")
            st.caption(
                "비중은 선택 조건의 등록자료 합계를 분모로 계산합니다. 좌표가 없는 등록자료도 포함합니다."
            )
            districts_tab, types_tab = st.tabs(["자치구별", "시설 종류별"])
            for tab, data in ((districts_tab, district_data), (types_tab, type_data)):
                with tab:
                    st.dataframe(
                        data,
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "비중(%)": st.column_config.NumberColumn(format="%.1f")
                        },
                    )

        with st.expander("통계 기준과 데이터 출처"):
            st.write(
                "두 기관의 자료를 합산하지 않습니다. 이름·주소가 비슷해도 서로 다른 등록 ID이면 별도 항목으로 집계하며, 동일 ID의 반복 응답만 제외합니다."
            )
            st.write(
                "간이운동장은 기본 포함입니다. 제공기관의 분류명으로 포함 여부를 판단하며, 수영장·생활체육관·기타시설 등을 임의로 같은 종류로 합치지 않습니다."
            )
            st.write(
                "조회 시각은 API 응답을 확인한 시각이며 제공기관의 원본 갱신일이 아닙니다. 시설 수는 이용률·수용능력·접근성의 순위를 뜻하지 않습니다."
            )
            st.caption(
                f"수신 항목 {len(result.items):,}건 · 동일 ID 반복 제외 {analyzer.duplicate_ids:,}건 · 자치구 확인 불가 제외 {analyzer.excluded_districts:,}건"
            )
            url = (
                "https://www.data.go.kr/data/15113986/openapi.do"
                if source == NATIONAL
                else "https://data.seoul.go.kr/dataList/OA-21779/A/1/datasetView.do"
            )
            st.link_button("선택한 통계 출처의 API 안내", url)
            st.link_button("지도 경계 출처", "https://github.com/southkorea/seoul-maps")
