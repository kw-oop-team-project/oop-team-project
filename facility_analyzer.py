# ============================================================
# [클래스 간 데이터 전달 방식]
#
# 1. FacilityManager -> FacilityAnalyzer
#    - FacilityManager는 SportsFacility 객체 목록을 전달
#
#    - FacilityManager가 관리하는 시설 데이터를 전달받음
#        facilities : 시설 객체 목록 (list)
#        districts  : 서울시 25개 자치구 목록 (list)
#
#    - 각 시설 객체에는 다음 속성이 필요
#        facility_type : 시설 종류 (예: "수영장")
#        district      : 자치구 (예: "노원구")
#    - 시설 목록과 서울시 25개 자치구 목록을 생성자에 전달
#    - 시설 종류별 필터링은 FacilityAnalyzer 내부에서 수행
#
# 2. Dashboard -> FacilityAnalyzer
#    - 사용자가 선택한 시설 종류(facility_type)를 메서드에 전달
#    - 예: analyzer.get_count_by_district("수영장")
#
# 3. FacilityAnalyzer -> Dashboard
#    - get_total_count()        : 전체 시설 개수 (int)
#    - get_count_by_district()  : 자치구별 개수 (dict)
#    - get_top_district()       : 최다 보유 자치구 및 개수 (tuple)
#    - get_district_coverage()  : 시설 보유 자치구 수 (int)
#    - Dashboard는 반환된 결과를 지도와 통계에 표시
#
### FacilityManager의 실제 메서드와 속성명은 추후 통일
# ============================================================


# 서울시 공공체육시설 통계 분석 클래스
# 1. 서울 전체 선택 시설 개수 계산
# 2. 자치구별 선택 시설 개수 계산
# 3. 선택 시설이 가장 많은 자치구 계산
# 4. 선택 시설을 보유한 자치구 수 계산

class FacilityAnalyzer:
    def __init__(self, facilities, districts):
        self.facilities = facilities
        self.districts = districts

    # 시설 객체 또는 딕셔너리에서 값 가져오기
    def _get_value(self, facility, key):
        if isinstance(facility, dict):
            return facility[key]
        return getattr(facility, key)

    # 1. 서울 전체 선택 시설 개수
    # "수영장"을 선택하면 서울 전체 수영장 수 계산
    # 자치구별 시설 개수를 합산
    def get_total_count(self, facility_type):
        counts = self.get_count_by_district(facility_type)
        return sum(counts.values())

    # 2. 자치구별 선택 시설 개수
    # 모든 자치구를 0개로 초기화 (시설이 없는 자치구도 지도에 표시하기 위함)
    def get_count_by_district(self, facility_type):
        counts = {district: 0 for district in self.districts}

        for facility in self.facilities:
            if self._get_value(facility, "facility_type") == facility_type:
                district = self._get_value(facility, "district")
                if district in counts:
                    counts[district] += 1

        return counts

    # 3. 선택 시설이 가장 많은 자치구
    def get_top_district(self, facility_type):
        counts = self.get_count_by_district(facility_type)
        top_count = max(counts.values(), default=0)

        if top_count == 0:
            return [], 0

        # 최다 개수가 동일한 자치구가 여러 개면 모두 반환
        top_districts = [
            district for district, count in counts.items()
            if count == top_count
        ]

        return top_districts, top_count

    # 4. 선택 시설을 보유한 자치구 수
    def get_district_coverage(self, facility_type):
        counts = self.get_count_by_district(facility_type)
        return sum(count > 0 for count in counts.values())


# 시험용 
# if __name__ == "__main__":
#     facilities = [
#         {"facility_type": "수영장", "district": "노원구"},
#         {"facility_type": "수영장", "district": "노원구"},
#         {"facility_type": "수영장", "district": "강남구"},
#         {"facility_type": "축구장", "district": "강북구"}
#     ]

#     districts = ["노원구", "강남구", "강북구"]
#     analyzer = FacilityAnalyzer(facilities, districts)

#     print(analyzer.get_total_count("수영장"))
#     print(analyzer.get_count_by_district("수영장"))
#     print(analyzer.get_top_district("수영장"))
#     print(analyzer.get_district_coverage("수영장"))
