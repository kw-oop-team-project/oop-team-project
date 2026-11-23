"""API 입력값의 텍스트·자치구·종목·링크와 좌표를 정규화한다."""

import math
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from .config import DISTRICTS


def clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"none", "nan", "null", "-"} else text


def normalized(value):
    return re.sub(
        r"[^\w가-힣]", "", unicodedata.normalize("NFKC", clean(value)).casefold()
    )


def district_name(value, address=""):
    text = clean(value)
    if text + "구" in DISTRICTS:
        return text + "구"
    if text in DISTRICTS:
        return text
    for district in DISTRICTS:
        if re.search(rf"(?:^|\s){district}(?:\s|$)", text + " " + address):
            return district
    return ""


def sport_key(value):
    text = normalized(value)
    aliases = {
        "수영": ("수영",),
        "축구": ("축구",),
        "테니스": ("테니스",),
        "배드민턴": ("배드민턴",),
        "농구": ("농구",),
        "야구": ("야구",),
        "탁구": ("탁구",),
        "족구": ("족구",),
        "풋살": ("풋살",),
        "골프": ("골프",),
        "빙상": ("빙상", "스케이트"),
        "체력단련": ("체력단련", "헬스", "피트니스"),
    }
    found = sorted(
        key for key, words in aliases.items() if any(w in text for w in words)
    )
    return "/".join(found) if found else text


def safe_url(value, official_reservation=False):
    value = clean(value)
    if not value:
        return ""
    if value.startswith("www."):
        value = "https://" + value
    try:
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
        ):
            return ""
        if official_reservation:
            if parts.hostname.casefold() != "yeyak.seoul.go.kr":
                return ""
            return urlunsplit(("https", parts.netloc, parts.path, parts.query, ""))
        return value
    except ValueError:
        return ""


def coordinate(value, low, high):
    try:
        number = float(value)
        return number if math.isfinite(number) and low <= number <= high else None
    except (TypeError, ValueError):
        return None
