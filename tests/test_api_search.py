from copy import deepcopy
from dataclasses import replace
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import requests

from api_fixtures import ApiHTTP, FakeResponse, NATIONAL_ROWS, SEOUL_ROWS
from src.api_clients import (
    FacilityApi,
    NATIONAL,
    SEOUL,
    national_facility,
    national_page,
    seoul_facility,
    seoul_page,
)
from src.http_client import ApiError, JsonTransport
from src.normalization import safe_url
from src.config import ApiSettings
from src.facility_manager import FacilityManager, merge_facilities


class ApiSearchTests(unittest.TestCase):
    def manager(self):
        return FacilityManager.from_settings(ApiSettings("test-seoul", "test-national"))

    def test_official_fields_and_public_seoul_filter(self):
        f = seoul_facility(SEOUL_ROWS[0])
        self.assertEqual((f.district, f.facility_type), ("노원구", "수영장"))
        self.assertIn("06:00", f.hours)
        self.assertEqual(f.fee, "성인 5,000원")
        self.assertEqual(f.phone, "02-000-0000")
        self.assertEqual(f.size, "성인풀 5레인")
        self.assertIsNone(seoul_facility(SEOUL_ROWS[2]))
        for row in NATIONAL_ROWS[2:]:
            self.assertIsNone(national_facility(row))

    def test_pagination_fetches_all_sources_and_keeps_supplementary(self):
        http = ApiHTTP()
        manager = self.manager()
        for api in (manager.seoul_api, manager.national_api, manager.reservation_api):
            api.page_size = 2
        with patch("requests.Session.get", side_effect=http):
            result = manager.load_data()
        self.assertEqual(len(http.calls), 4)
        self.assertEqual(len(result.facilities), 3)
        self.assertTrue(all(s.state == "ok" for s in result.statuses))
        merged = next(f for f in result.facilities if f.district == "노원구")
        self.assertEqual(merged.sources, (SEOUL, NATIONAL))
        self.assertEqual(merged.latitude, 37.65)
        self.assertEqual(merged.fee, "성인 5,000원")
        self.assertTrue(any(f.name == "가상 보완수영장" for f in result.facilities))
        national_call = next(c for c in http.calls if c[0] == "national")
        self.assertEqual(national_call[2]["cp_nm"], "서울특별시")
        self.assertEqual(national_call[2]["faci_gb_nm"], "공공")

    def test_encoded_key_is_not_double_encoded(self):
        http = ApiHTTP()
        api = FacilityApi(NATIONAL, "test%2Bkey%2Fvalue%3D")
        with patch("requests.Session.get", side_effect=http):
            api.fetch()
        self.assertEqual(http.calls[0][2]["serviceKey"], "test+key/value=")

    def test_conservative_duplicate_policy_and_input_not_mutated(self):
        first = seoul_facility(SEOUL_ROWS[0])
        second = national_facility(NATIONAL_ROWS[0])
        before = deepcopy(first)
        self.assertEqual(len(merge_facilities([first, second])), 1)
        self.assertEqual(first, before)
        variants = [
            replace(second, address=""),
            replace(second, district="강남구"),
            replace(second, address=second.address + "-1"),
            replace(second, facility_type="테니스장"),
            replace(second, name=second.name + "별관"),
            replace(second, address_detail="지상 2층"),
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(len(merge_facilities([first, variant])), 2)
        # 두 서울 시설이 모두 후보면 전국 시설을 어느 쪽에도 합치지 않는다.
        other = replace(first, facility_id="seoul:other")
        self.assertEqual(len(merge_facilities([first, other, second])), 3)

    def test_search_combines_all_three_conditions(self):
        with patch("requests.Session.get", side_effect=ApiHTTP()):
            facilities = self.manager().load_data().facilities
        self.assertEqual(
            len(FacilityManager.search(facilities, "노원구", "가상구민", "수영")), 1
        )
        self.assertEqual(
            len(FacilityManager.search(facilities, "강남구", "보완", "수영장")), 1
        )
        self.assertFalse(FacilityManager.search(facilities, "노원구", "", "테니스"))
        self.assertFalse(FacilityManager.search(facilities, name="존재하지않음"))

    def test_missing_key_performs_no_request(self):
        with patch("requests.Session.get") as request:
            result = FacilityManager.from_settings(ApiSettings()).load_data()
        request.assert_not_called()
        self.assertEqual(
            [s.state for s in result.statuses], ["missing_key", "missing_key"]
        )

    def test_one_source_failure_preserves_other_source(self):
        for failed in ("seoul", "national"):
            with (
                self.subTest(failed=failed),
                patch("requests.Session.get", side_effect=ApiHTTP(fail=failed)),
            ):
                result = self.manager().load_data()
            self.assertTrue(result.facilities)
            self.assertEqual(sorted(s.state for s in result.statuses), ["error", "ok"])

    def test_partial_pagination_and_repeat_page_are_explicit(self):
        http = ApiHTTP()

        def fail_second(url, **kwargs):
            if url.endswith("/3/4/"):
                raise requests.Timeout("private key should never appear")
            return http(url, **kwargs)

        api = FacilityApi(SEOUL, "test-seoul", page_size=2)
        with patch("requests.Session.get", side_effect=fail_second):
            result = api.fetch()
        self.assertEqual(result.state, "partial")
        self.assertEqual(len(result.items), 2)
        repeated = {
            "facilities": {
                "RESULT": {"CODE": "INFO-000"},
                "list_total_count": 10,
                "row": [SEOUL_ROWS[0]],
            }
        }
        with patch("requests.Session.get", return_value=FakeResponse(repeated)):
            result = FacilityApi(SEOUL, "test").fetch()
        self.assertEqual(result.state, "partial")
        self.assertIn("반복", result.message)

    def test_zero_response_and_malformed_and_auth_errors(self):
        self.assertEqual(
            seoul_page({"RESULT": {"CODE": "INFO-200"}}, "facilities").rows, []
        )
        self.assertEqual(
            national_page(
                {
                    "header": {"resultCode": "00"},
                    "body": {"totalCount": "0", "items": ""},
                }
            ).rows,
            [],
        )
        self.assertEqual(
            len(
                national_page(
                    {
                        "header": {"resultCode": "00"},
                        "body": {
                            "totalCount": "1",
                            "items": {"item": NATIONAL_ROWS[0]},
                        },
                    }
                ).rows
            ),
            1,
        )
        with self.assertRaises(ApiError):
            seoul_page(
                {"RESULT": {"CODE": "INFO-100", "MESSAGE": "do not echo key"}},
                "facilities",
            )
        with self.assertRaises(ApiError):
            national_page(
                {"header": {"resultCode": "30", "resultMsg": "do not echo key"}}
            )
        for payload in (
            {"facilities": None},
            {"facilities": {"RESULT": None}},
            {"response": {"header": []}},
        ):
            with patch("requests.Session.get", return_value=FakeResponse(payload)):
                result = FacilityApi(SEOUL, "test").fetch()
            self.assertEqual(result.state, "error")

    def test_memory_cache_ttl_timeout_and_safe_error(self):
        now = [0]
        transport = JsonTransport(clock=lambda: now[0])
        http = ApiHTTP()
        url = "http://openapi.seoul.go.kr:8088/test-key/json/facilities/1/5/"
        with patch("requests.Session.get", side_effect=http):
            first = transport.get(url, ttl=60)
            first["facilities"]["row"].clear()
            self.assertTrue(transport.get(url, ttl=60)["facilities"]["row"])
            self.assertEqual(len(http.calls), 1)
            now[0] = 61
            transport.get(url, ttl=60)
            self.assertEqual(len(http.calls), 2)
        self.assertEqual(http.calls[0][3], (3.05, 12))
        transport.clear()
        with patch("requests.Session.get", side_effect=requests.Timeout(url)):
            with self.assertRaises(ApiError) as caught:
                transport.get(url)
        self.assertNotIn("test-key", str(caught.exception))
        response = FakeResponse({})
        response.json = lambda: (_ for _ in ()).throw(ValueError("secret XML body"))
        with patch("requests.Session.get", return_value=response):
            with self.assertRaises(ApiError) as caught:
                transport.get(url)
        self.assertNotIn("secret", str(caught.exception))

    def test_reservations_multiple_schedules_and_ambiguity(self):
        manager = self.manager()
        http = ApiHTTP()
        manager.reservation_api.page_size = 2
        with patch("requests.Session.get", side_effect=http):
            catalog = manager.load_data()
            selected = next(f for f in catalog.facilities if f.district == "노원구")
            result = manager.get_reservations(selected, catalog.facilities)
            self.assertEqual([r.reservation_id for r in result.items], ["r1", "r2"])
            self.assertEqual([r.status for r in result.items], ["접수중", "예약마감"])
            self.assertEqual(result.items[0].receipt_end, "2026-11-30 18:00")
            ambiguous = replace(
                selected, facility_id="different-id", address="서울시 노원구 다른로 20"
            )
            self.assertFalse(
                manager.get_reservations(
                    selected, catalog.facilities + [ambiguous]
                ).items
            )
            http.fail = "reservation"
            manager.reservation_api.transport.clear()
            self.assertEqual(
                manager.get_reservations(selected, catalog.facilities).state, "error"
            )

    def test_official_reservation_link_validation(self):
        for bad in (
            "javascript:alert(1)",
            "https://yeyak.seoul.go.kr.attacker.org/",
            "https://user@yeyak.seoul.go.kr/",
        ):
            self.assertEqual(safe_url(bad, official_reservation=True), "")
        self.assertEqual(
            safe_url("http://yeyak.seoul.go.kr/test", True),
            "https://yeyak.seoul.go.kr/test",
        )

    def test_settings_environment_priority_and_safe_repr(self):
        with patch.dict(os.environ, {"SEOUL_OPEN_API_KEY": "test-env"}, clear=True):
            settings = ApiSettings.from_environment(
                {
                    "SEOUL_OPEN_API_KEY": "test-secrets",
                    "DATA_GO_KR_SERVICE_KEY": "national-secret",
                }
            )
        self.assertEqual(settings.seoul_key, "test-env")
        self.assertEqual(settings.national_key, "national-secret")
        self.assertNotIn("secret", repr(settings))

    def test_missing_source_ids_still_keep_both_provenances(self):
        seoul_row, national_row = deepcopy(SEOUL_ROWS[0]), deepcopy(NATIONAL_ROWS[0])
        seoul_row.pop("FT_IDX")
        national_row.pop("faci_cd")
        national_row["faci_nm"] = seoul_row["FT_TITLE"]
        national_row["faci_road_addr"] = seoul_row["FT_ADDR"]
        result = merge_facilities(
            [seoul_facility(seoul_row), national_facility(national_row)]
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].sources, (SEOUL, NATIONAL))

    def test_separate_reservation_key_is_used_only_for_reservations(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = ApiSettings.from_environment(
                {
                    "SEOUL_OPEN_API_KEY": "test-facility",
                    "DATA_GO_KR_SERVICE_KEY": "test-national",
                    "SEOUL_RESERVATION_API_KEY": "test-reservation",
                }
            )
        manager = FacilityManager.from_settings(settings)
        http = ApiHTTP()
        with patch("requests.Session.get", side_effect=http):
            manager.load_data()
            manager.reservation_api.fetch()
        self.assertTrue(
            any("/test-facility/" in c[1] for c in http.calls if c[0] == "seoul")
        )
        self.assertTrue(
            any(
                "/test-reservation/" in c[1]
                for c in http.calls
                if c[0] == "reservation"
            )
        )
        self.assertNotIn("test-reservation", repr(settings))

    def test_blank_reservation_key_reuses_seoul_key(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = ApiSettings.from_environment(
                {"SEOUL_OPEN_API_KEY": "test-shared", "SEOUL_RESERVATION_API_KEY": ""}
            )
        self.assertEqual(settings.effective_reservation_key, "test-shared")

    def test_error_payload_is_not_cached_and_page_limit_is_explicit(self):
        transport = JsonTransport()
        with patch(
            "requests.Session.get",
            return_value=FakeResponse({"RESULT": {"CODE": "INFO-100"}}),
        ) as request:
            for _ in range(2):
                transport.get("http://example.invalid/test")
            self.assertEqual(request.call_count, 2)
        with patch("requests.Session.get", side_effect=ApiHTTP()):
            result = FacilityApi(SEOUL, "test", page_size=1, max_pages=1).fetch()
        self.assertEqual(result.state, "partial")
        self.assertIn("한도", result.message)

    def test_project_has_no_csv_outside_external_packages(self):
        root = Path(__file__).resolve().parents[1]
        managed_csv = []
        for current, directories, files in os.walk(root):
            directories[:] = [
                name
                for name in directories
                if name
                not in {
                    ".git",
                    ".runtime",
                    "site-packages",
                    "node_modules",
                    "__pycache__",
                }
                and not (Path(current) / name / "pyvenv.cfg").exists()
            ]
            managed_csv.extend(
                str(Path(current) / name)
                for name in files
                if name.lower().endswith(".csv")
            )
        self.assertEqual(managed_csv, [])


if __name__ == "__main__":
    unittest.main()
