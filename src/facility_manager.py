"""API 시설을 관리하고 검색·중복 제거·예약 연결을 담당한다."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re

from .api_clients import FacilityApi, NATIONAL, RESERVATIONS, SEOUL, SourceResult
from .http_client import JsonTransport
from .normalization import clean, district_name, normalized, safe_url, sport_key


def address_key(address):
    address = clean(address).replace("서울특별시", "서울").replace("서울시", "서울")
    # 건물번호의 하이픈은 보존한다. 도로명/지번 주소의 추측 변환은 하지 않는다.
    return re.sub(r"[^\w가-힣-]", "", address.casefold())


def identity(facility):
    values = (
        facility.district,
        normalized(facility.name),
        address_key(facility.address),
        sport_key(facility.facility_type),
    )
    return values if all(values) else None


def same_facility(first, second):
    if identity(first) is None or identity(first) != identity(second):
        return False
    # 같은 건물의 다른 층/코트 등은 별도 시설로 유지한다.
    return not (
        first.address_detail
        and second.address_detail
        and normalized(first.address_detail) != normalized(second.address_detail)
    )


def merge_facilities(facilities):
    result = []
    seen_ids = set()
    by_identity = {}
    for original in facilities:
        if original.facility_id in seen_ids:
            continue
        seen_ids.add(original.facility_id)
        key = identity(original)
        candidates = [
            f
            for f in by_identity.get(key, [])
            if same_facility(f, original)
            and not set(f.sources).intersection(original.sources)
        ]
        if len(candidates) != 1:
            independent = deepcopy(original)
            result.append(independent)
            if key is not None:
                by_identity.setdefault(key, []).append(independent)
            continue
        target = candidates[0]
        # 서울시 상세정보를 우선하고, 누락된 값만 전국 API로 보완한다.
        for attr in (
            "owner",
            "manager",
            "area",
            "size",
            "total_floor_area",
            "address_detail",
            "hours",
            "phone",
            "fee",
            "homepage",
        ):
            if not getattr(target, attr):
                setattr(target, attr, getattr(original, attr))
        if target.latitude is None or target.longitude is None:
            target.latitude, target.longitude = original.latitude, original.longitude
        target.sources = tuple(dict.fromkeys(target.sources + original.sources))
        target.source_details.update(deepcopy(original.source_details))
    return result


@dataclass
class SearchResult:
    facilities: list
    statuses: list[SourceResult]


@dataclass
class Reservation:
    reservation_id: str
    title: str
    place: str
    district: str
    sport: str
    status: str
    receipt_start: str
    receipt_end: str
    use_start: str
    use_end: str
    fee: str
    phone: str
    url: str

    @classmethod
    def from_row(cls, row):
        return cls(
            clean(row.get("SVCID")),
            clean(row.get("SVCNM")),
            clean(row.get("PLACENM")),
            district_name(row.get("AREANM")),
            clean(row.get("MINCLASSNM")),
            clean(row.get("SVCSTATNM")),
            clean(row.get("RCPTBGNDT")),
            clean(row.get("RCPTENDDT")),
            clean(row.get("SVCOPNBGNDT")),
            clean(row.get("SVCOPNENDDT")),
            clean(row.get("PAYATNM")),
            clean(row.get("TELNO")),
            safe_url(row.get("SVCURL"), official_reservation=True),
        )


def reservation_score(facility, reservation):
    if facility.district != reservation.district:
        return 0
    sport, requested = sport_key(facility.facility_type), sport_key(reservation.sport)
    generic = sport in {
        "생활체육관",
        "종합체육시설",
        "종합체육관",
        "체육센터",
        "다목적체육관",
    }
    compatible = sport == requested or bool(
        set(sport.split("/")) & set(requested.split("/"))
    )
    if sport and requested and not compatible and not generic:
        return 0
    name, place, title = (
        normalized(facility.name),
        normalized(reservation.place),
        normalized(reservation.title),
    )
    if not name or not place:
        return 0
    # 세부 코트명이 있는 시설을 우선한다. 장소명만 같은 다종목 시설은 연결하지 않는다.
    title_match = re.search(
        re.escape(name) + (r"(?!\d)" if name[-1:].isdigit() else ""), title
    )
    if title_match and len(name) >= 4 and (name == place or place in name):
        return 3
    if name == place:
        return 2
    if len(place) >= 4 and place in name and sport and compatible:
        return 1
    return 0


class FacilityManager:
    def __init__(self, seoul_api, national_api, reservation_api):
        self.seoul_api = seoul_api
        self.national_api = national_api
        self.reservation_api = reservation_api

    @classmethod
    def from_settings(cls, settings):
        # 각 서비스의 타임아웃/오류/캐시를 분리한다.
        return cls(
            FacilityApi(SEOUL, settings.seoul_key, JsonTransport()),
            FacilityApi(NATIONAL, settings.national_key, JsonTransport()),
            FacilityApi(
                RESERVATIONS, settings.effective_reservation_key, JsonTransport()
            ),
        )

    def clear_cache(self):
        for api in (self.seoul_api, self.national_api, self.reservation_api):
            api.transport.clear()

    def load_data(self):
        statuses = [self.seoul_api.fetch(), self.national_api.fetch()]
        facilities = merge_facilities([f for result in statuses for f in result.items])
        return SearchResult(facilities, statuses)

    @staticmethod
    def search(facilities, district="", name="", sport=""):
        return [
            facility
            for facility in facilities
            if (not district or district == facility.district)
            and (not name or normalized(name) in normalized(facility.name))
            and (
                not sport
                or sport_key(sport) in sport_key(facility.facility_type)
                or normalized(sport) in normalized(facility.name)
            )
        ]

    def get_reservations(self, selected, all_facilities):
        result = self.reservation_api.fetch()
        matched = []
        seen = set()
        for row in result.items:
            reservation = Reservation.from_row(row)
            scores = [
                (reservation_score(f, reservation), f.facility_id)
                for f in all_facilities
            ]
            best = max((score for score, _ in scores), default=0)
            winners = {fid for score, fid in scores if score == best and score > 0}
            # 동명/동일 장소 등으로 후보가 여러 개면 어느 시설에도 자동 연결하지 않는다.
            if winners == {selected.facility_id}:
                key = reservation.reservation_id or (
                    reservation.title,
                    reservation.receipt_start,
                    reservation.use_start,
                )
                if key not in seen:
                    matched.append(reservation)
                    seen.add(key)
        return SourceResult(
            result.source, matched, result.state, result.message, result.rejected
        )
