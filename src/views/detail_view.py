"""시설 목록과 상세정보를 표시하는 독립 화면 모듈.

임시 연동 계약:
* 호출자는 Manager에서 조회한 시설 객체를 전달한다. 이 모듈은 데이터를 읽거나
  시설 종류/자치구를 필터링하지 않는다.
* facility_id는 비어 있지 않은 고유 문자열이다. name, district,
  facility_type은 목록 표시용 속성이다.
* has_detail()은 상세 탐색 가능 여부를, get_info()는 상세정보 매핑을 반환한다.
  상세정보 키 변환은 _DETAIL_FIELDS와 _detail_rows에 모아 두었다.
* 선택 상태의 소유자는 호출자(Dashboard)다. 목록 함수의 반환 ID로 현재 목록의
  객체를 찾아 상세 함수에 전달한다. 선택 해제는 None으로 전달한다.

Streamlit은 화면 호출 시에만 가져온다. ui 인자로 같은 메서드를 가진 대역을
전달하면 Streamlit을 설치하지 않고 화면 동작을 테스트할 수 있다.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any, Protocol


class FacilityLike(Protocol):
    """SportsFacility의 구체 클래스에 의존하지 않는 화면 입력 계약."""

    facility_id: str
    name: str
    district: str
    facility_type: str

    def has_detail(self) -> bool: ...

    def get_info(self) -> Mapping[str, Any]: ...


_MISSING = "정보 없음"
_DETAIL_FIELDS = (
    ("name", "시설명"),
    ("district", "자치구"),
    ("facility_type", "시설 종류"),
    ("owner", "소유기관"),
    ("manager", "관리주체"),
    ("site_area", "부지면적"),
    ("building_area", "건축면적"),
    ("total_floor_area", "연면적"),
)


def _get_ui(ui: Any) -> Any:
    if ui is not None:
        return ui
    import streamlit

    return streamlit


def _display_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return _MISSING
    text = str(value).strip()
    return text if text else _MISSING


def _facility_id(facility: FacilityLike) -> str:
    value = getattr(facility, "facility_id", None)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("facility_id는 비어 있지 않은 고유 문자열이어야 합니다.")
    return value


def _list_row(facility: FacilityLike) -> dict[str, str]:
    """팀원 클래스의 목록 속성명 변경은 이 어댑터에 반영한다."""
    return {
        "시설명": _display_value(getattr(facility, "name", None)),
        "자치구": _display_value(getattr(facility, "district", None)),
        "시설 종류": _display_value(getattr(facility, "facility_type", None)),
    }


def _detail_rows(facility: FacilityLike) -> list[dict[str, str]]:
    info = facility.get_info()
    if not isinstance(info, Mapping):
        raise TypeError("get_info()는 상세정보 매핑을 반환해야 합니다.")
    rows = []
    for key, label in _DETAIL_FIELDS:
        # 목록 속성과 상세정보의 동일 필드는 상세정보에 키가 없을 때만 보완한다.
        value = info.get(key, getattr(facility, key, None))
        rows.append({"항목": label, "내용": _display_value(value)})
    return rows


def show_facility_list(
    facilities: Iterable[FacilityLike],
    selected_facility_id: str | None = None,
    *,
    key_prefix: str = "detail",
    ui: Any = None,
) -> str | None:
    """목록을 표시하고 선택한 시설 ID를 반환한다. 미선택/빈 결과는 None.

    has_detail()이 False인 시설은 목록에서 제외한다. ID의 누락/중복은
    호출자 계약 오류로 ValueError를 발생시킨다. 입력 객체는 변경하지 않는다.
    key_prefix는 한 페이지에서 상세 목록을 여러 개 표시할 때 다르게 지정한다.
    """
    by_id = {}
    for facility in facilities:
        facility_id = _facility_id(facility)
        if facility_id in by_id:
            raise ValueError(f"중복된 facility_id입니다: {facility_id}")
        by_id[facility_id] = facility

    eligible = {
        facility_id: facility
        for facility_id, facility in by_id.items()
        if facility.has_detail()
    }
    ui = _get_ui(ui)
    widget_state = getattr(ui, "session_state", None)
    last_result_key = f"{key_prefix}_last_returned_facility_id"
    ui.subheader("시설 목록")
    excluded_count = len(by_id) - len(eligible)
    if excluded_count:
        ui.caption(f"상세정보가 없는 시설 {excluded_count}개는 상세 탐색에서 제외됩니다.")
    if not eligible:
        if widget_state is not None:
            widget_state[last_result_key] = None
        message = (
            "상세 탐색 가능한 시설이 없습니다."
            if by_id
            else "선택한 조건에 해당하는 시설이 없습니다."
        )
        ui.info(message)
        return None

    rows = {facility_id: _list_row(facility) for facility_id, facility in eligible.items()}
    ui.table(list(rows.values()))
    name_counts = Counter(row["시설명"] for row in rows.values())
    labels = {}
    for facility_id, row in rows.items():
        label = " · ".join(row.values())
        if name_counts[row["시설명"]] > 1:
            label += f" [{facility_id}]"
        labels[facility_id] = label

    options = list(eligible)
    current_id = selected_facility_id if selected_facility_id in eligible else None
    # 사용자 선택으로 키가 바뀌면 다음 재실행에서 클릭 결과를 잃는다.
    # 키는 목록 기준으로 유지하고, 호출자가 별도로 선택을 변경했을 때만
    # 위젯 상태를 동기화한다. 업무 상태의 소유자는 계속 Dashboard다.
    identity = json.dumps(options, ensure_ascii=False)
    fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    widget_key = f"{key_prefix}_facility_{fingerprint}"
    index = options.index(current_id) if current_id is not None else None
    if widget_state is not None and widget_key in widget_state:
        if widget_state.get(last_result_key) != current_id:
            widget_state[widget_key] = current_id
        # 기존 위젯 값은 Session State에서 복원한다. 기본값을 중복 지정하지 않는다.
        index = None
    selected = ui.selectbox(
        "시설 선택",
        options=options,
        index=index,
        format_func=labels.__getitem__,
        key=widget_key,
        placeholder="상세정보를 확인할 시설을 선택하세요.",
    )
    result = selected if selected in eligible else None
    if widget_state is not None:
        widget_state[last_result_key] = result
    return result


def show_detail(facility: FacilityLike | None, *, ui: Any = None) -> None:
    """선택 시설의 상세정보를 표시한다. 객체 조회와 선택 상태는 호출자가 관리한다."""
    ui = _get_ui(ui)
    ui.subheader("시설 상세정보")
    if facility is None:
        ui.info("목록에서 시설을 선택하면 상세정보를 확인할 수 있습니다.")
        return
    if not facility.has_detail():
        ui.info("이 시설은 상세 탐색 대상에서 제외됩니다.")
        return
    ui.table(_detail_rows(facility))
