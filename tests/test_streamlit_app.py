"""Streamlit의 실제 실행/위젯 생명주기를 모의 HTTP 응답으로 검증한다."""

from pathlib import Path
import os
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from api_fixtures import ApiHTTP, FakeResponse, SEOUL_ROWS


ROOT = Path(__file__).resolve().parents[1]


def click_search(app):
    next(button for button in app.button if button.label == "시설 검색").click().run()
    return app


def select_facility(app, facility_id):
    app.button(key=f"facility_card_{facility_id}").click().run()
    return app


class StreamlitAppTests(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear()
        self.env = patch.dict(
            os.environ,
            {
                "SEOUL_OPEN_API_KEY": "test-seoul",
                "DATA_GO_KR_SERVICE_KEY": "test-national",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def app(self, finder=True):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=25)
        # 사용자가 입력하는 실제 로컬 인증 설정을 테스트에서 읽지 않는다.
        app.secrets = {"test_mode": True}
        app.run()
        if finder:
            app.radio(key="main_navigation").set_value("체육시설 찾기").run()
        return app

    def assert_healthy(self, app):
        self.assertEqual(len(app.exception), 0, str(app.exception))

    def test_search_detail_dedup_reservations_and_filter_reset_without_csv(self):
        self.assertFalse(list((ROOT / "data").glob("*.csv")))
        http = ApiHTTP()
        with patch("requests.Session.get", side_effect=http):
            app = click_search(self.app())
            self.assert_healthy(app)
            self.assertIn("검색 결과 3개", [x.value for x in app.subheader])
            select_facility(app, "seoul:1")
            self.assert_healthy(app)
            all_tables = "\n".join(table.value.to_string() for table in app.table)
            for value in (
                "06:00~22:00",
                "성인 5,000원",
                "접수중",
                "예약마감",
                "2026-11-30 18:00",
            ):
                self.assertIn(value, all_tables)
            self.assertTrue(any("가상 구민수영장" in x.value for x in app.markdown))
            links = [element.proto.url for element in app.get("link_button")]
            self.assertEqual(len([url for url in links if "rsv_svc_id=" in url]), 2)
            self.assertTrue(
                any(
                    "제공기관:" in x.value and "국민체육진흥공단" in x.value
                    for x in app.caption
                )
            )
            # 같은 시설의 재실행에서는 선택을 유지하고 새 검색에서는 초기화한다.
            app.run()
            self.assert_healthy(app)
            self.assertEqual(app.session_state["selected_facility_id"], "seoul:1")
            app.selectbox(key="search_district").select("강남구")
            app.text_input(key="search_name").input("보완")
            app.selectbox(key="search_sport").set_value("수영")
            click_search(app)
            self.assert_healthy(app)
            self.assertIn("검색 결과 1개", [x.value for x in app.subheader])
            self.assertIsNone(app.session_state["selected_facility_id"])
            select_facility(app, "national:n2")
            self.assert_healthy(app)
            self.assertTrue(
                any("연결되는 예약 일정이 없습니다" in x.value for x in app.info)
            )

    def test_missing_keys_and_unavailable_source_are_not_zero_results(self):
        with (
            patch.dict(
                os.environ, {"SEOUL_OPEN_API_KEY": "", "DATA_GO_KR_SERVICE_KEY": ""}
            ),
            patch("requests.Session.get") as request,
        ):
            app = self.app()
            self.assert_healthy(app)
            self.assertTrue(any("키 미설정" in x.value for x in app.warning))
            click_search(app)
            self.assert_healthy(app)
            self.assertTrue(any("가져오지 못했습니다" in x.value for x in app.info))
            request.assert_not_called()

    def test_zero_matches_are_distinct_from_api_errors(self):
        with patch("requests.Session.get", side_effect=ApiHTTP()):
            app = self.app()
            app.text_input(key="search_name").input("없는시설")
            click_search(app)
            self.assert_healthy(app)
            self.assertFalse(app.error)
            self.assertTrue(
                any("검색 조건과 일치하는 시설이 없습니다" in x.value for x in app.info)
            )

    def test_both_apis_healthy_but_empty(self):
        with patch("requests.Session.get", side_effect=ApiHTTP(empty=True)):
            app = click_search(self.app())
            self.assert_healthy(app)
            self.assertFalse(app.error)
            self.assertIn("검색 결과 0개", [x.value for x in app.subheader])

    def test_seoul_failure_still_allows_national_detail(self):
        with patch("requests.Session.get", side_effect=ApiHTTP(fail="seoul")):
            app = click_search(self.app())
            self.assert_healthy(app)
            self.assertTrue(any("API 오류" in x.value for x in app.error))
            select_facility(app, "national:n2")
            self.assert_healthy(app)
            self.assertTrue(
                any("02-000-1111" in table.value.to_string() for table in app.table)
            )

    def test_reservation_failure_does_not_hide_facility_details(self):
        with patch("requests.Session.get", side_effect=ApiHTTP(fail="reservation")):
            app = click_search(self.app())
            select_facility(app, "seoul:1")
            self.assert_healthy(app)
            self.assertTrue(
                any(
                    "서울시 공공서비스예약" in x.value and "API 오류" in x.value
                    for x in app.error
                )
            )
            self.assertTrue(
                any("성인 5,000원" in table.value.to_string() for table in app.table)
            )

    def test_large_result_list_pagination_and_address_only_facilities(self):
        rows = [
            dict(
                SEOUL_ROWS[0],
                FT_IDX=100 + i,
                FT_TITLE=f"가상 시설 {i}",
                FT_ADDR=f"서울특별시 노원구 가상로 {100 + i}",
            )
            for i in range(26)
        ]

        def http(url, **kwargs):
            if "/facilities/" in url:
                return FakeResponse(
                    {
                        "facilities": {
                            "RESULT": {"CODE": "INFO-000"},
                            "list_total_count": 26,
                            "row": rows,
                        }
                    }
                )
            return ApiHTTP(empty=True)(url, **kwargs)

        with patch("requests.Session.get", side_effect=http):
            app = click_search(self.app())
            self.assert_healthy(app)
            self.assertEqual(
                len(
                    [
                        b
                        for b in app.button
                        if b.key and b.key.startswith("facility_card_")
                    ]
                ),
                25,
            )
            self.assertTrue(any("위치 좌표가 없습니다" in x.value for x in app.info))
            next(w for w in app.selectbox if w.label == "목록 페이지").set_value(
                2
            ).run()
            select_facility(app, "seoul:125")
            self.assert_healthy(app)
            self.assertTrue(
                any("가상 시설 25" in value.value for value in app.markdown)
            )
            app.radio(key="main_navigation").set_value("체육시설 현황").run()
            app.radio(key="main_navigation").set_value("체육시설 찾기").run()
            self.assertEqual(app.selectbox(key="result_page").value, 2)
            self.assertEqual(app.session_state["selected_facility_id"], "seoul:125")

    def test_home_does_not_call_apis(self):
        with patch("requests.Session.get") as request:
            app = self.app(finder=False)
            self.assert_healthy(app)
            self.assertEqual(app.radio(key="main_navigation").value, "홈")
            self.assertTrue(any("더 즐거운 움직임" in x.value for x in app.markdown))
            request.assert_not_called()

    def test_home_finder_button_loads_map_before_search(self):
        with patch("requests.Session.get", side_effect=ApiHTTP()):
            app = self.app(finder=False)
            app.button(key="home_find_button").click().run()
            self.assert_healthy(app)
            self.assertEqual(app.radio(key="main_navigation").value, "체육시설 찾기")
            self.assertIn("검색 결과 3개", [x.value for x in app.subheader])
            self.assertTrue(app.get("deck_gl_json_chart"))
            self.assertTrue(
                any("서울시 공공체육시설 지도" == x.value for x in app.subheader)
            )

    def test_clear_selection_reset_filters_and_tab_persistence(self):
        with patch("requests.Session.get", side_effect=ApiHTTP()):
            app = self.app()
            select_facility(app, "seoul:1")
            app.button(key="clear_facility").click().run()
            self.assertIsNone(app.session_state["selected_facility_id"])
            app.selectbox(key="search_district").set_value("강남구")
            app.selectbox(key="search_sport").set_value("수영")
            click_search(app)
            self.assertIn("검색 결과 1개", [x.value for x in app.subheader])
            app.radio(key="main_navigation").set_value("체육시설 현황").run()
            app.radio(key="main_navigation").set_value("체육시설 찾기").run()
            self.assert_healthy(app)
            self.assertIn("검색 결과 1개", [x.value for x in app.subheader])
            self.assertEqual(app.selectbox(key="search_district").value, "강남구")
            self.assertEqual(app.selectbox(key="search_sport").value, "수영")
            app.button(key="reset_search").click().run()
            self.assertIn("검색 결과 3개", [x.value for x in app.subheader])

    def test_map_selection_accepts_only_displayed_facilities(self):
        from src.views.main_view import map_facility_id

        event = {"selection": {"objects": {"facilities": [{"facility_id": "one"}]}}}
        self.assertEqual(map_facility_id(event, {"one"}), "one")
        self.assertIsNone(map_facility_id(event, {"other"}))
        self.assertIsNone(map_facility_id({}, {"one"}))


if __name__ == "__main__":
    unittest.main()
