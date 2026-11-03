"""팀원 클래스/Streamlit 설치 없이 상세 화면의 관찰 가능한 동작을 검증한다."""

from __future__ import annotations

import copy
import unittest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

from src.views.detail_view import show_detail, show_facility_list


_DEFAULT_SELECTION = object()


@dataclass
class FakeFacility:
    facility_id: str
    name: Any = "테스트 수영장"
    district: Any = "노원구"
    facility_type: Any = "수영장"
    detail_available: bool = True
    info: dict = field(default_factory=dict)
    info_calls: int = 0

    def has_detail(self):
        return self.detail_available

    def get_info(self):
        self.info_calls += 1
        return self.info


class FakeUI:
    """렌더링 내용과 선택 위젯의 입출력을 기록하는 최소 UI 대역."""

    def __init__(self, selection=_DEFAULT_SELECTION):
        self.selection = selection
        self.headings = []
        self.messages = []
        self.captions = []
        self.tables = []
        self.selectboxes = []

    def subheader(self, text):
        self.headings.append(text)

    def info(self, text):
        self.messages.append(text)

    def caption(self, text):
        self.captions.append(text)

    def table(self, rows):
        self.tables.append(copy.deepcopy(rows))

    def selectbox(self, label, *, options, index, format_func, key, placeholder):
        self.selectboxes.append({
            "label": label,
            "options": list(options),
            "index": index,
            "labels": [format_func(option) for option in options],
            "key": key,
            "placeholder": placeholder,
        })
        if self.selection is _DEFAULT_SELECTION:
            return options[index] if index is not None else None
        return self.selection


class FacilityListTests(unittest.TestCase):
    def test_initial_list_has_no_automatic_selection(self):
        ui = FakeUI()
        result = show_facility_list([FakeFacility("one"), FakeFacility("two")], ui=ui)
        self.assertIsNone(result)
        self.assertEqual(len(ui.tables[0]), 2)
        self.assertEqual(ui.selectboxes[0]["options"], ["one", "two"])
        self.assertIsNone(ui.selectboxes[0]["index"])

    def test_user_selection_returns_id_instead_of_name(self):
        ui = FakeUI(selection="two")
        self.assertEqual(
            show_facility_list([FakeFacility("one"), FakeFacility("two")], ui=ui),
            "two",
        )

    def test_current_valid_selection_is_restored(self):
        ui = FakeUI()
        result = show_facility_list(
            [FakeFacility("one"), FakeFacility("two")], "two", ui=ui
        )
        self.assertEqual(result, "two")
        self.assertEqual(ui.selectboxes[0]["index"], 1)

    def test_empty_list_clears_selection_and_does_not_create_widget(self):
        ui = FakeUI()
        self.assertIsNone(show_facility_list([], "removed", ui=ui))
        self.assertTrue(ui.messages)
        self.assertFalse(ui.selectboxes)
        self.assertFalse(ui.tables)

    def test_duplicate_names_are_distinguishable_even_in_same_district(self):
        ui = FakeUI(selection="two")
        facilities = [FakeFacility("one"), FakeFacility("two")]
        self.assertEqual(show_facility_list(facilities, ui=ui), "two")
        labels = ui.selectboxes[0]["labels"]
        self.assertNotEqual(labels[0], labels[1])
        self.assertIn("one", labels[0])
        self.assertIn("two", labels[1])

    def test_removed_selection_does_not_select_first_facility(self):
        ui = FakeUI()
        self.assertIsNone(show_facility_list([FakeFacility("new")], "old", ui=ui))
        self.assertIsNone(ui.selectboxes[0]["index"])

    def test_stale_widget_return_is_rejected(self):
        ui = FakeUI(selection="removed")
        self.assertIsNone(show_facility_list([FakeFacility("current")], ui=ui))

    def test_widget_identity_changes_for_list_but_not_for_selection(self):
        original, changed_list, cleared = FakeUI(), FakeUI(), FakeUI()
        show_facility_list([FakeFacility("one")], "one", ui=original)
        show_facility_list([FakeFacility("two")], ui=changed_list)
        show_facility_list([FakeFacility("one")], None, ui=cleared)
        self.assertNotEqual(original.selectboxes[0]["key"], changed_list.selectboxes[0]["key"])
        self.assertEqual(original.selectboxes[0]["key"], cleared.selectboxes[0]["key"])

    def test_widget_state_supports_consecutive_choices_and_external_clear(self):
        class StatefulUI(FakeUI):
            def __init__(self):
                super().__init__()
                self.session_state = {}

            def selectbox(self, *args, **kwargs):
                initial = super().selectbox(*args, **kwargs)
                key = kwargs["key"]
                return self.session_state.setdefault(key, initial)

        ui = StatefulUI()
        facilities = [FakeFacility("one"), FakeFacility("two")]
        self.assertIsNone(show_facility_list(facilities, ui=ui))
        key = ui.selectboxes[-1]["key"]
        ui.session_state[key] = "one"
        self.assertEqual(show_facility_list(facilities, None, ui=ui), "one")
        ui.session_state[key] = "two"
        self.assertEqual(show_facility_list(facilities, "one", ui=ui), "two")
        self.assertIsNone(show_facility_list(facilities, None, ui=ui))

    def test_key_prefix_separates_two_detail_panels(self):
        first, second = FakeUI(), FakeUI()
        facilities = [FakeFacility("one")]
        show_facility_list(facilities, key_prefix="left", ui=first)
        show_facility_list(facilities, key_prefix="right", ui=second)
        self.assertNotEqual(first.selectboxes[0]["key"], second.selectboxes[0]["key"])

    def test_detail_unavailable_facilities_are_excluded_without_reading_info(self):
        excluded = FakeFacility("simple", facility_type="간이운동장", detail_available=False)
        ui = FakeUI()
        show_facility_list([excluded, FakeFacility("normal")], "simple", ui=ui)
        self.assertEqual(ui.selectboxes[0]["options"], ["normal"])
        self.assertIsNone(ui.selectboxes[0]["index"])
        self.assertTrue(ui.captions)
        self.assertEqual(excluded.info_calls, 0)

    def test_all_facilities_excluded_shows_explanation(self):
        ui = FakeUI()
        self.assertIsNone(show_facility_list(
            [FakeFacility("simple", detail_available=False)], ui=ui
        ))
        self.assertTrue(ui.messages)
        self.assertTrue(ui.captions)
        self.assertFalse(ui.selectboxes)

    def test_missing_listing_information_uses_placeholder(self):
        ui = FakeUI()
        show_facility_list([FakeFacility("one", name=None, district=" ", facility_type="")], ui=ui)
        self.assertEqual(set(ui.tables[0][0].values()), {"정보 없음"})

    def test_missing_or_invalid_id_is_contract_error(self):
        for invalid_id in (None, "", "  ", 1):
            with self.subTest(facility_id=invalid_id), self.assertRaises(ValueError):
                show_facility_list([FakeFacility(invalid_id)], ui=FakeUI())

    def test_duplicate_id_is_contract_error(self):
        with self.assertRaises(ValueError):
            show_facility_list([FakeFacility("same"), FakeFacility("same")], ui=FakeUI())

    def test_generator_input_is_consumed_once_and_objects_are_unchanged(self):
        facilities = [FakeFacility("one"), FakeFacility("two")]
        before = copy.deepcopy(facilities)
        show_facility_list((facility for facility in facilities), ui=FakeUI())
        self.assertEqual(facilities, before)


class FacilityDetailTests(unittest.TestCase):
    def test_no_selection_shows_instruction_without_detail_table(self):
        ui = FakeUI()
        show_detail(None, ui=ui)
        self.assertTrue(ui.messages)
        self.assertFalse(ui.tables)

    def test_detail_contains_identity_ownership_management_and_areas(self):
        ui = FakeUI()
        facility = FakeFacility("one", info={
            "owner": "서울시", "manager": "시설관리공단",
            "site_area": 1000, "building_area": 250, "total_floor_area": 500,
        })
        show_detail(facility, ui=ui)
        details = {row["항목"]: row["내용"] for row in ui.tables[0]}
        self.assertEqual(details["시설명"], "테스트 수영장")
        self.assertEqual(details["자치구"], "노원구")
        self.assertEqual(details["시설 종류"], "수영장")
        self.assertEqual(details["소유기관"], "서울시")
        self.assertEqual(details["관리주체"], "시설관리공단")
        self.assertEqual(details["부지면적"], "1000")
        self.assertEqual(details["건축면적"], "250")
        self.assertEqual(details["연면적"], "500")

    def test_missing_values_and_zero_are_distinguished_without_mutating_info(self):
        info = {"owner": None, "manager": "  ", "site_area": 0,
                "building_area": float("nan"), "total_floor_area": ""}
        facility = FakeFacility("one", info=info)
        ui = FakeUI()
        show_detail(facility, ui=ui)
        details = {row["항목"]: row["내용"] for row in ui.tables[0]}
        self.assertEqual(details["부지면적"], "0")
        for label in ("소유기관", "관리주체", "건축면적", "연면적"):
            self.assertEqual(details[label], "정보 없음")
        self.assertIs(facility.info, info)
        self.assertEqual(info["manager"], "  ")
        self.assertEqual(info["site_area"], 0)
        self.assertEqual(facility.info_calls, 1)

    def test_unavailable_detail_is_not_read(self):
        facility, ui = FakeFacility("simple", detail_available=False), FakeUI()
        show_detail(facility, ui=ui)
        self.assertEqual(facility.info_calls, 0)
        self.assertFalse(ui.tables)
        self.assertTrue(ui.messages)

    def test_invalid_info_return_is_contract_error(self):
        with self.assertRaises(TypeError):
            show_detail(FakeFacility("one", info=None), ui=FakeUI())

    def test_selected_duplicate_name_resolves_to_correct_details(self):
        facilities = [FakeFacility("one", info={"manager": "첫 번째 관리자"}),
                      FakeFacility("two", info={"manager": "두 번째 관리자"})]
        selected_id = show_facility_list(facilities, ui=FakeUI(selection="two"))
        selected = next(facility for facility in facilities if facility.facility_id == selected_id)
        ui = FakeUI()
        show_detail(selected, ui=ui)
        self.assertIn({"항목": "관리주체", "내용": "두 번째 관리자"}, ui.tables[0])
        self.assertEqual(facilities[0].info_calls, 0)

    def test_cleared_list_does_not_render_previous_details(self):
        selected_id = show_facility_list([], "old", ui=FakeUI())
        ui = FakeUI()
        show_detail(None if selected_id is None else FakeFacility(selected_id), ui=ui)
        self.assertFalse(ui.tables)

    def test_default_ui_uses_streamlit_only_when_rendering(self):
        ui = FakeUI()
        with patch.dict("sys.modules", {"streamlit": ui}):
            self.assertIsNone(show_facility_list([]))
            show_detail(None)
        self.assertEqual(len(ui.messages), 2)


if __name__ == "__main__":
    unittest.main()
