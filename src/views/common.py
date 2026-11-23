"""화면에서 공유하는 값 표시와 API 상태 안내."""

import math
from typing import Any

MISSING = "정보 없음"


def get_ui(ui: Any) -> Any:
    if ui is not None:
        return ui
    import streamlit

    return streamlit


def display_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return MISSING
    text = str(value).strip()
    return text if text else MISSING


def show_api_status(result, *, ui=None):
    ui = get_ui(ui)
    label = result.source
    if result.state == "missing_key":
        ui.warning(f"{label} · 키 미설정: {result.message}")
    elif result.state == "error":
        ui.error(f"{label} · API 오류: {result.message}")
    elif result.state == "partial":
        ui.warning(f"{label} · 일부 결과: {result.message}")
    else:
        ui.caption(f"{label} · 정상 응답")
