"""현황 집계·출처별 캐시·실제 앱의 통계 전용 동작을 검증한다."""

from datetime import datetime
import json
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from api_fixtures import ApiHTTP, NATIONAL_ROWS
from src.api_clients import NATIONAL, SEOUL, SourceResult
from src.config import DISTRICTS, FACILITY_CACHE_TTL
from src.facility_analyzer import ALL_TYPES, FacilityAnalyzer, UNKNOWN_TYPE
from src.overview_data import KST, OverviewService
from src.sports_facility import SportsFacility
from src.views.overview_view import count_table, district_boundaries, district_map_spec

ROOT = Path(__file__).resolve().parents[1]


def facility(fid, district="노원구", kind="수영장"):
    return SportsFacility("같은 시설명", district, kind, facility_id=fid)


class FacilityAnalyzerTests(unittest.TestCase):
    def test_totals_zeros_ties_and_exclusive_type_shares(self):
        analyzer = FacilityAnalyzer(
            [
                facility("a"),
                facility("b", "강남구"),
                facility("c", kind="간이운동장"),
                facility("d", "강남구", "간이운동장"),
            ]
        )
        counts = analyzer.get_count_by_district()
        self.assertEqual(set(counts), set(DISTRICTS))
        self.assertEqual(counts["종로구"], 0)
        self.assertEqual(analyzer.get_total_count(), sum(counts.values()))
        self.assertEqual(analyzer.get_top_district(), (["강남구", "노원구"], 2))
        self.assertEqual(analyzer.get_district_coverage(), 2)
        self.assertEqual(analyzer.get_total_count(include_simple=False), 2)
        self.assertEqual(analyzer.get_total_count("간이운동장", False), 0)
        shares = count_table(analyzer.get_count_by_type(), "시설 종류")
        self.assertAlmostEqual(shares["비중(%)"].sum(), 100)

    def test_only_same_ids_removed_and_input_unchanged(self):
        first, second = facility("a"), facility("b")
        original = [first, second, first, facility("outside", "서울")]
        analyzer = FacilityAnalyzer(original)
        self.assertEqual(analyzer.get_total_count(), 2)
        self.assertEqual(analyzer.duplicate_ids, 1)
        self.assertEqual(analyzer.excluded_districts, 1)
        self.assertEqual(len(original), 4)
        self.assertEqual(first.name, "같은 시설명")

    def test_provider_types_are_not_merged_into_sports(self):
        analyzer = FacilityAnalyzer(
            [
                facility("a", kind="수영"),
                facility("b", kind="수영장"),
                facility("c", kind=""),
                facility("d", kind="생활체육관"),
            ]
        )
        self.assertEqual(analyzer.get_total_count("수영"), 1)
        self.assertIn(UNKNOWN_TYPE, analyzer.get_types())
        self.assertEqual(sum(analyzer.get_count_by_type().values()), 4)

    def test_empty_totals_have_no_winner_or_division_error(self):
        analyzer = FacilityAnalyzer([])
        self.assertEqual(analyzer.get_top_district(), ([], 0))
        self.assertEqual(analyzer.get_district_coverage(), 0)
        self.assertEqual(analyzer.get_total_count("없는 종류"), 0)
        table = count_table(analyzer.get_count_by_district(), "자치구")
        self.assertEqual(len(table), 25)
        self.assertEqual(table["비중(%)"].sum(), 0)

    def test_local_map_contains_all_district_counts_without_facility_details(self):
        before = json.dumps(district_boundaries(), ensure_ascii=False)
        counts = FacilityAnalyzer([facility("private-id")]).get_count_by_district()
        spec = district_map_spec(counts)
        values = spec["data"]["values"]
        mapped = {f["properties"]["district"]: f["properties"]["count"] for f in values}
        self.assertEqual(mapped, counts)
        self.assertNotIn("같은 시설명", json.dumps(spec, ensure_ascii=False))
        self.assertNotIn("private-id", json.dumps(spec))
        self.assertEqual(json.dumps(district_boundaries(), ensure_ascii=False), before)

    def test_district_type_analysis(self):
        analyzer = FacilityAnalyzer([
            facility("a", "노원구", "수영장"),
            facility("b", "노원구", "수영장"),
            facility("c", "노원구", "축구장"),
            facility("d", "강남구", "체육관"),
            facility("e", "노원구", "간이운동장"),
        ])

        counts = analyzer.get_district_type_counts()

        self.assertEqual(counts["노원구"]["수영장"], 2)
        self.assertEqual(counts["노원구"]["축구장"], 1)
        self.assertEqual(counts["종로구"], {})

        diversity = analyzer.get_district_diversity()

        self.assertEqual(diversity["노원구"], 3)
        self.assertEqual(diversity["강남구"], 1)

        filtered = analyzer.get_district_type_counts(
            include_simple=False
        )

        self.assertNotIn("간이운동장", filtered["노원구"])

        top = analyzer.get_top_type_counts(
            counts["노원구"], top_n=1
        )

        self.assertEqual(top["수영장"], 2)
        self.assertEqual(top["기타(나머지)"], 2)

    def test_summary_matches_existing_methods(self):
        analyzer = FacilityAnalyzer([
            facility("a", "노원구", "수영장"),
            facility("b", "노원구", "축구장"),
            facility("c", "강남구", "수영장"),
            facility("d", "노원구", "간이운동장"),
        ])

        for facility_type in [ALL_TYPES, "수영장", "없는 종류"]:
            for include_simple in [True, False]:
                summary = analyzer.get_summary(
                    facility_type, include_simple
                )

                self.assertEqual(
                    summary["district_counts"],
                    analyzer.get_count_by_district(facility_type, include_simple)
                )

                self.assertEqual(
                    summary["total"],
                    analyzer.get_total_count(facility_type, include_simple)
                )

                self.assertEqual(
                    (summary["leaders"], summary["maximum"]),
                    analyzer.get_top_district(facility_type, include_simple)
                )

                self.assertEqual(
                    summary["coverage"],
                    analyzer.get_district_coverage(facility_type, include_simple)
                )

                self.assertEqual(
                    summary["type_counts"],
                    analyzer.get_count_by_type(facility_type, include_simple)
                )


class OverviewServiceTests(unittest.TestCase):
    def test_cache_refresh_expiry_and_sources_are_independent(self):
        apis = {source: Mock() for source in (NATIONAL, SEOUL)}
        for source, api in apis.items():
            api.fetch.return_value = SourceResult(source, [facility(source)])
        clock = [0]
        times = iter(datetime(2026, 11, 24, hour, tzinfo=KST) for hour in range(4))
        service = OverviewService(apis, clock=lambda: clock[0], now=lambda: next(times))
        first = service.load(NATIONAL)
        first.result.items.clear()
        cached = service.load(NATIONAL)
        self.assertEqual(len(cached.result.items), 1)
        self.assertEqual(first.fetched_at, cached.fetched_at)
        apis[NATIONAL].fetch.assert_called_once()
        apis[SEOUL].fetch.assert_not_called()
        service.load(SEOUL)
        service.load(NATIONAL, refresh=True)
        self.assertEqual(apis[NATIONAL].fetch.call_count, 2)
        self.assertEqual(apis[SEOUL].fetch.call_count, 1)
        clock[0] = FACILITY_CACHE_TTL + 1
        service.load(NATIONAL)
        self.assertEqual(apis[NATIONAL].fetch.call_count, 3)

    def test_partial_and_errors_are_retried_instead_of_cached(self):
        api = Mock()
        api.fetch.side_effect = [
            SourceResult(NATIONAL, [facility("a")], "partial"),
            SourceResult(NATIONAL, state="error"),
            SourceResult(NATIONAL, [facility("a")]),
        ]
        service = OverviewService({NATIONAL: api})
        self.assertEqual(service.load(NATIONAL).result.state, "partial")
        self.assertEqual(service.load(NATIONAL).result.state, "error")
        self.assertEqual(service.load(NATIONAL).result.state, "ok")
        self.assertEqual(api.fetch.call_count, 3)


class OverviewAppTests(unittest.TestCase):
    def setUp(self):
        st.cache_resource.clear()
        env = patch.dict(
            os.environ,
            {
                "SEOUL_OPEN_API_KEY": "test-seoul",
                "DATA_GO_KR_SERVICE_KEY": "test-national",
            },
        )
        env.start()
        self.addCleanup(env.stop)

    def overview(self):
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=25)
        app.secrets = {"test_mode": True}
        app.run()
        app.radio(key="main_navigation").set_value("체육시설 현황").run()
        self.assertEqual(len(app.exception), 0, str(app.exception))
        return app

    def test_source_switch_and_statistics_only_no_reservation_or_search(self):
        http = ApiHTTP()
        with patch("requests.Session.get", side_effect=http):
            app = self.overview()
            self.assertEqual(app.metric[0].value, "2건")
            self.assertEqual({call[0] for call in http.calls}, {"national"})
            self.assertEqual(len(app.text_input), 0)
            self.assertFalse(
                any(b.key and b.key.startswith("facility_card_") for b in app.button)
            )
            self.assertFalse(any("찾기로 이동" in b.label for b in app.button))
            self.assertEqual(len(app.dataframe[0].value), 25)
            self.assertEqual(app.dataframe[0].value["등록 시설 수(건)"].sum(), 2)
            app.selectbox(key="overview_source").set_value(SEOUL).run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.metric[0].value, "2건")
            self.assertIn("공동 최다", "\n".join(c.value for c in app.caption))
            app.selectbox(key="overview_type").set_value("테니스장").run()
            self.assertEqual(app.metric[0].value, "1건")
            self.assertEqual(app.dataframe[1].value["등록 시설 수(건)"].sum(), 1)
            self.assertFalse(any(call[0] == "reservation" for call in http.calls))

    def test_simple_filter_and_source_change_reset_invalid_type(self):
        rows = [
            *NATIONAL_ROWS,
            dict(NATIONAL_ROWS[0], faci_cd="simple", ftype_nm="간이운동장"),
        ]
        with (
            patch("api_fixtures.NATIONAL_ROWS", rows),
            patch("requests.Session.get", side_effect=ApiHTTP()),
        ):
            app = self.overview()
            self.assertEqual(app.metric[0].value, "3건")
            app.selectbox(key="overview_type").set_value("간이운동장").run()
            self.assertEqual(app.metric[0].value, "1건")
            app.checkbox(key="overview_simple").uncheck().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.selectbox(key="overview_type").value, ALL_TYPES)
            self.assertEqual(app.metric[0].value, "2건")

    def test_failed_source_does_not_look_like_zero_or_silently_switch(self):
        with patch("requests.Session.get", side_effect=ApiHTTP(fail="national")):
            app = self.overview()
            self.assertTrue(app.error)
            self.assertEqual(len(app.metric), 0)
            self.assertEqual(app.selectbox(key="overview_source").value, NATIONAL)
            app.selectbox(key="overview_source").set_value(SEOUL).run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.metric[0].value, "2건")

    def test_missing_keys_make_no_requests_and_healthy_empty_shows_zeros(self):
        with (
            patch.dict(
                os.environ, {"SEOUL_OPEN_API_KEY": "", "DATA_GO_KR_SERVICE_KEY": ""}
            ),
            patch("requests.Session.get") as request,
        ):
            app = self.overview()
            self.assertTrue(any("키 미설정" in w.value for w in app.warning))
            self.assertEqual(len(app.metric), 0)
            request.assert_not_called()
        st.cache_resource.clear()
        with patch("requests.Session.get", side_effect=ApiHTTP(empty=True)):
            app = self.overview()
            self.assertEqual(app.metric[0].value, "0건")
            self.assertEqual(app.metric[1].value, "해당 없음")
            self.assertEqual(app.metric[2].value, "0 / 25")
            self.assertTrue(any("0건" in item.value for item in app.info))

    def test_partial_response_labels_metrics_and_map_not_complete(self):
        with patch("src.overview_data.OverviewService.load") as load:
            from src.overview_data import OverviewSnapshot

            load.return_value = OverviewSnapshot(
                SourceResult(NATIONAL, [facility("a")], "partial", "일부 페이지 오류"),
                datetime.now(KST),
            )
            app = self.overview()
            self.assertEqual(app.metric[0].label, "수신 자료 중 등록 시설 수")
            self.assertTrue(any("전체 현황이 아니며" in w.value for w in app.warning))

    def test_overview_filters_do_not_change_finder_state_and_survive_navigation(self):
        with patch("requests.Session.get", side_effect=ApiHTTP()):
            app = self.overview()
            app.selectbox(key="overview_source").set_value(SEOUL).run()
            app.selectbox(key="overview_type").set_value("테니스장").run()
            app.radio(key="main_navigation").set_value("체육시설 찾기").run()
            self.assertEqual(app.selectbox(key="search_sport").value, "전체 종목")
            app.radio(key="main_navigation").set_value("체육시설 현황").run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.selectbox(key="overview_source").value, SEOUL)
            self.assertEqual(app.selectbox(key="overview_type").value, "테니스장")


if __name__ == "__main__":
    unittest.main()
