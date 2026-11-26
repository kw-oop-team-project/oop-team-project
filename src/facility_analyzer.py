"""선택한 출처의 등록자료만 집계한다. 화면·HTTP·검색 상태와 독립적이다.

기존 팀원의 네 가지 집계 인터페이스를 API 객체에 맞춰 확장했다.
서로 다른 ID는 이름이나 주소가 같아도 별도 등록 항목으로 센다.
"""

from collections import Counter

from .config import DISTRICTS
from .normalization import clean, normalized

ALL_TYPES = "전체 종류"
UNKNOWN_TYPE = "종류 정보 없음"


def facility_kind(facility):
    # 종목 검색용 sport_key로 서로 다른 시설 분류를 합치지 않는다.
    return clean(facility.facility_type) or UNKNOWN_TYPE


def is_simple_facility(facility):
    return normalized(facility.facility_type).startswith("간이운동장")


class FacilityAnalyzer:
    def __init__(self, facilities, districts=DISTRICTS):
        self.districts = tuple(districts)
        seen = set()
        self.facilities = []
        self.duplicate_ids = 0
        self.excluded_districts = 0
        for facility in facilities:
            if facility.district not in self.districts:
                self.excluded_districts += 1
                continue
            if facility.facility_id in seen:
                self.duplicate_ids += 1
                continue
            seen.add(facility.facility_id)
            self.facilities.append(facility)

    def select(self, facility_type=ALL_TYPES, include_simple=True):
        return [
            facility
            for facility in self.facilities
            if (include_simple or not is_simple_facility(facility))
            and (facility_type == ALL_TYPES or facility_kind(facility) == facility_type)
        ]

    def get_types(self, include_simple=True):
        return sorted(
            {facility_kind(f) for f in self.select(include_simple=include_simple)}
        )

    def get_count_by_district(self, facility_type=ALL_TYPES, include_simple=True):
        counts = dict.fromkeys(self.districts, 0)
        for facility in self.select(facility_type, include_simple):
            counts[facility.district] += 1
        return counts

    def get_total_count(self, facility_type=ALL_TYPES, include_simple=True):
        return sum(self.get_count_by_district(facility_type, include_simple).values())

    def get_top_district(self, facility_type=ALL_TYPES, include_simple=True):
        counts = self.get_count_by_district(facility_type, include_simple)
        maximum = max(counts.values(), default=0)
        if not maximum:
            return [], 0
        return [name for name, count in counts.items() if count == maximum], maximum

    def get_district_coverage(self, facility_type=ALL_TYPES, include_simple=True):
        return sum(
            count > 0
            for count in self.get_count_by_district(
                facility_type, include_simple
            ).values()
        )

    def get_count_by_type(self, facility_type=ALL_TYPES, include_simple=True):
        counts = Counter(
            facility_kind(f) for f in self.select(facility_type, include_simple)
        )
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def get_district_type_counts(self, include_simple=True):
        counts = {district: {} for district in self.districts}

        for facility in self.select(include_simple=include_simple):
            district = facility.district
            kind = facility_kind(facility)

            if kind not in counts[district]:
                counts[district][kind] = 0

            counts[district][kind] += 1

        return counts

    def get_district_diversity(self, include_simple=True):
        counts = self.get_district_type_counts(include_simple)

        return {
            district: len(types)
            for district, types in counts.items()
        }

    def get_top_type_counts(self, counts, top_n=5):
        ranked = sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0])
        )

        result = dict(ranked[:top_n])
        other = sum(count for _, count in ranked[top_n:])

        if other > 0:
            label = "기타(나머지)"
            while label in counts:
                label += "*"
            result[label] = other

        return result