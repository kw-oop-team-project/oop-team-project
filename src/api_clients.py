"""공식 API의 페이지를 읽고 공공시설 응답을 도메인 객체로 변환한다."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from urllib.parse import quote, unquote

from .config import (
    API_MAX_PAGES,
    API_PAGE_SIZE,
    FACILITY_CACHE_TTL,
    RESERVATION_CACHE_TTL,
)
from .http_client import ApiError, JsonTransport
from .normalization import clean, coordinate, district_name, normalized, safe_url
from .sports_facility import SportsFacility

SEOUL = "서울시 공공체육시설"
NATIONAL = "국민체육진흥공단"
RESERVATIONS = "서울시 공공서비스예약"
SEOUL_BASE = "http://openapi.seoul.go.kr:8088"
NATIONAL_URL = "https://apis.data.go.kr/B551014/SRVC_API_SFMS_FACI/TODZ_API_SFMS_FACI"


@dataclass
class Page:
    rows: list[dict]
    total: int


@dataclass
class SourceResult:
    source: str
    items: list = field(default_factory=list)
    state: str = "ok"
    message: str = ""
    rejected: int = 0


def total_count(value):
    try:
        number = int(value)
        if number < 0:
            raise ValueError
        return number
    except (TypeError, ValueError):
        raise ApiError("API의 전체 건수 형식이 올바르지 않습니다.") from None


def seoul_page(payload, service):
    root = payload.get(service, payload)
    if not isinstance(root, dict):
        raise ApiError("서울시 API 응답 형식이 올바르지 않습니다.")
    code = root.get("RESULT", {}).get("CODE")
    if code == "INFO-200":
        return Page([], 0)
    if code != "INFO-000":
        if code == "INFO-100":
            raise ApiError(
                "서울시 인증키가 유효하지 않거나 해당 서비스가 승인되지 않았습니다."
            )
        raise ApiError(
            "서울시 API가 오류를 반환했습니다. 서비스 이용 상태를 확인해 주세요."
        )
    rows = root.get("row", [])
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ApiError("서울시 API의 시설 목록 형식이 올바르지 않습니다.")
    return Page(rows, total_count(root.get("list_total_count")))


def national_page(payload):
    root = payload.get("response", payload)
    if not isinstance(root, dict):
        raise ApiError("전국체육시설 API 응답 형식이 올바르지 않습니다.")
    code = str(root.get("header", {}).get("resultCode", ""))
    if code not in {"00", "0"}:
        if code in {"03", "3"}:
            return Page([], 0)
        raise ApiError(
            "전국체육시설 API 오류입니다. 인증키와 서비스 이용 승인을 확인해 주세요."
        )
    body = root.get("body", {})
    if not isinstance(body, dict):
        raise ApiError("전국체육시설 API의 본문 형식이 올바르지 않습니다.")
    items = body.get("items") or {}
    rows = items.get("item", []) if isinstance(items, dict) else items
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ApiError("전국체육시설 API의 시설 목록 형식이 올바르지 않습니다.")
    return Page(rows, total_count(body.get("totalCount")))


def seoul_facility(row):
    # BK_CD_NAME은 공공/학교/민간 구분, FT_KIND_NAME은 종목/시설 유형이다.
    if clean(row.get("BK_CD_NAME")) != "공공체육시설":
        return None
    address = clean(row.get("FT_ADDR"))
    district = district_name(row.get("AR_CD_NAME"), address)
    name = clean(row.get("FT_TITLE"))
    if not district or not name or (address and not address.startswith("서울")):
        return None
    hours = "\n".join(
        f"{label}: {clean(row.get(key))}"
        for label, key in (
            ("평일", "FT_WD_TIME"),
            ("주말", "FT_WE_TIME"),
            ("안내", "FT_INFO_TIME"),
        )
        if clean(row.get(key))
    )
    facility = SportsFacility(
        name,
        district,
        clean(row.get("FT_KIND_NAME")),
        manager=clean(row.get("FT_ORG")),
        size=clean(row.get("FT_SIZE")),
        address=address,
        address_detail=clean(row.get("FT_ADDR_DETAIL")),
        hours=hours,
        phone=clean(row.get("FT_PHONE")),
        fee=clean(row.get("FT_MONEY")),
        homepage=safe_url(row.get("FT_HOMEPAGE")),
        sources=(SEOUL,),
    )
    if clean(row.get("FT_IDX")):
        facility.facility_id = "seoul:" + clean(row["FT_IDX"])
    else:
        facility.facility_id = "seoul:" + facility.facility_id
    facility.source_details = {SEOUL: facility.get_info()}
    return facility


def national_facility(row):
    if normalized(row.get("faci_gb_nm")) not in {"공공", "공공시설", "공공체육시설"}:
        return None
    region = clean(row.get("cp_nm")) or clean(row.get("addr_ctpv_nm"))
    address = clean(row.get("faci_road_addr")) or clean(row.get("faci_addr"))
    if region and region not in {"서울", "서울시", "서울특별시"}:
        return None
    if not region and not address.startswith("서울"):
        return None
    district = district_name(row.get("cpb_nm") or row.get("addr_cpb_nm"), address)
    name = clean(row.get("faci_nm"))
    if not district or not name:
        return None
    facility = SportsFacility(
        name,
        district,
        clean(row.get("ftype_nm")) or clean(row.get("fcob_nm")),
        owner=clean(row.get("fmng_type_gb_nm")),
        manager=clean(row.get("fmng_dept_nm")),
        total_floor_area=clean(row.get("faci_gfa")),
        address=address,
        address_detail=clean(
            row.get("faci_road_daddr")
            if row.get("faci_road_addr")
            else row.get("faci_daddr")
        ),
        phone=clean(row.get("faci_tel_no")),
        homepage=safe_url(row.get("faci_homepage")),
        latitude=coordinate(row.get("faci_lat"), 37, 38),
        longitude=coordinate(row.get("faci_lot"), 126, 128),
        sources=(NATIONAL,),
    )
    if clean(row.get("faci_cd")):
        facility.facility_id = "national:" + clean(row["faci_cd"])
    else:
        facility.facility_id = "national:" + facility.facility_id
    facility.source_details = {NATIONAL: facility.get_info()}
    return facility


class FacilityApi:
    def __init__(
        self,
        source,
        key,
        transport=None,
        page_size=API_PAGE_SIZE,
        max_pages=API_MAX_PAGES,
    ):
        self.source = source
        self._key = key
        self.transport = transport or JsonTransport()
        self.page_size = min(1000, max(1, page_size))
        self.max_pages = max_pages

    def page(self, page_number):
        if self.source in {SEOUL, RESERVATIONS}:
            service = (
                "facilities" if self.source == SEOUL else "ListPublicReservationSport"
            )
            start = (page_number - 1) * self.page_size + 1
            end = page_number * self.page_size
            url = f"{SEOUL_BASE}/{quote(self._key, safe='')}/json/{service}/{start}/{end}/"
            ttl = (
                RESERVATION_CACHE_TTL
                if self.source == RESERVATIONS
                else FACILITY_CACHE_TTL
            )
            return seoul_page(self.transport.get(url, ttl=ttl), service)
        params = {
            "serviceKey": unquote(self._key),
            "pageNo": page_number,
            "numOfRows": self.page_size,
            "resultType": "JSON",
            "cp_nm": "서울특별시",
            "faci_gb_nm": "공공",
        }
        return national_page(self.transport.get(NATIONAL_URL, params=params))

    def fetch(self):
        if not self._key:
            env_name = (
                "DATA_GO_KR_SERVICE_KEY"
                if self.source == NATIONAL
                else "SEOUL_OPEN_API_KEY"
            )
            if self.source == RESERVATIONS:
                env_name = "SEOUL_RESERVATION_API_KEY 또는 SEOUL_OPEN_API_KEY"
            return SourceResult(
                self.source,
                state="missing_key",
                message=f"{env_name}가 설정되지 않았습니다.",
            )
        result = SourceResult(self.source)
        seen_pages = set()
        consumed = 0
        try:
            for number in range(1, self.max_pages + 1):
                page = self.page(number)
                fingerprint = hashlib.sha256(
                    json.dumps(page.rows, sort_keys=True).encode()
                ).digest()
                if page.rows and fingerprint in seen_pages:
                    raise ApiError(
                        "API가 같은 페이지를 반복 반환하여 일부 결과만 표시합니다."
                    )
                seen_pages.add(fingerprint)
                for row in page.rows:
                    item = (
                        row
                        if self.source == RESERVATIONS
                        else (
                            seoul_facility(row)
                            if self.source == SEOUL
                            else national_facility(row)
                        )
                    )
                    if item is None:
                        result.rejected += 1
                    else:
                        result.items.append(item)
                consumed += len(page.rows)
                if consumed >= page.total:
                    return result
                if not page.rows:
                    raise ApiError(
                        "전체 건수보다 적은 데이터가 반환되어 일부 결과만 표시합니다."
                    )
            raise ApiError("조회 페이지 한도에 도달하여 일부 결과만 표시합니다.")
        except ApiError as error:
            result.state = "partial" if result.items else "error"
            result.message = str(error)
            return result
        except (AttributeError, TypeError, ValueError, KeyError):
            result.state = "partial" if result.items else "error"
            result.message = (
                "API 응답 구조가 명세와 다릅니다. 잠시 후 다시 조회해 주세요."
            )
            return result
