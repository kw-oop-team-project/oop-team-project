import pandas as pd
from sports_facility import SportsFacility # 클래스 불러오기

class FacilityManager:
    """manager = FacilityManager("data/공공체육시설.csv") 형태로 사용"""
    def __init__(self, csv_path):
        self.csv_path = csv_path # 전달받은 csv 경로 저장
        self.facilities = [] # 시설 정보를 담을 리스트
        self.load_data() # 데이터 로드

    def load_data(self):
        df = pd.read_csv(self.csv_path)
        for _, row in df.iterrows():
            raw_district = str(row["시군구"]).strip() if pd.notna(row.get("시군구")) else ""
            if not raw_district and pd.notna(row.get("시ㆍ군ㆍ구")):
                raw_district = str(row["시ㆍ군ㆍ구"]).strip()
            
            raw_name = str(row["시설명"]).strip() if pd.notna(row.get("시설명")) else ""
            
            # 요약 행('계', '소계', '합계' 또는 '18', '34' 같은 단순 합계 숫자) 건너뛰기
            if raw_district in ["계", "소계", "합계", "소개"] or raw_name in ["계", "소계", "합계"] or raw_name.isdigit():
                continue

            # 띄어쓰기 및 줄바꿈 정리
            district = raw_district.replace(" ", "").replace("\n", " ") if raw_district else "기타"
            name = raw_name.replace("\n", " ")

            facility_type = str(row["시설종류"]).strip() if pd.notna(row.get("시설종류")) else "기타"
            owner = str(row["소유기관"]).replace("\n", " ").strip() if pd.notna(row.get("소유기관")) else None
            manager = str(row["관리주체"]).replace("\n", " ").strip() if pd.notna(row.get("관리주체")) else None
            
            raw_area = row.get("부지면적")
            area = None
            if pd.notna(raw_area):
                cleaned_area = str(raw_area).replace(",", "").strip()
                if cleaned_area:
                    try:
                        area = float(cleaned_area)
                    except ValueError:
                        area = None

            
            facility = SportsFacility(name, district, facility_type, owner, manager, area)
            self.facilities.append(facility)

    def get_all_facilities(self):
        """전체 체육시설 목록을 반환한다."""
        return self.facilities

    def get_by_district(self, district):
        """
        입력받은 자치구에 속한 시설 목록만 반환한다
        인자 : district (str) : 검색할 자치구 이름 (예: "마포구", "강남구" 등)
        """
        result = []
        for facility in self.facilities:
            if facility.district == district:
                result.append(facility)
        return result

    def get_by_type(self, facility_type):
        """
        입력받은 시설종류(종목)에 속한 시설 목록만 반환한다
        인자 : facility_type (str) : 검색할 시설 종류(종목) (예: "체육관", "테니스장" 등)
        """
        result = []
        for facility in self.facilities:
            if facility.facility_type == facility_type:
                result.append(facility)
        return result

    def get_districts(self):
        """
        등록된 자치구 목록을 중복 없이 오름차순(가나다순)으로 정렬하여 반환합니다
        UI 드롭다운 메뉴나 선택창 등을 만드실 때 활용할 수 있습니다
        """
        districts = {facility.district for facility in self.facilities if facility.district}
        return sorted(list(districts))

    def get_facility_types(self):
        """
        등록된 시설종류(종목) 목록을 중복 없이 오름차순(가나다순)으로 정렬하여 반환합니다
        UI 드롭다운 메뉴나 선택창 등을 만드실 때 활용할 수 있습니다
        """
        types = {facility.facility_type for facility in self.facilities if facility.facility_type}
        return sorted(list(types))



"""테스트 역할"""
if __name__ == "__main__":
    # 1. FacilityManager 인스턴스 생성 (CSV 파일 경로 지정)
    manager = FacilityManager("data/공공체육시설.csv")

    # 2. 로드된 전체 시설 개수 확인
    all_facilities = manager.get_all_facilities()
    print(f"총 로드된 시설 수: {len(all_facilities)}개")

    # 3. 자치구 및 종목 목록 확인
    print(f"등록된 자치구 목록 ({len(manager.get_districts())}개): {manager.get_districts()[:5]} ...")
    print(f"등록된 시설 종류 ({len(manager.get_facility_types())}개): {manager.get_facility_types()[:5]} ...")

    # 4. 필터링 기능 테스트 (예: 마포구 체육시설 조회)
    mapo_facilities = manager.get_by_district("마포구")
    print(f"\n[마포구 체육시설 검색 결과: {len(mapo_facilities)}개]")
    for fac in mapo_facilities[:3]:
        print(f" - {fac}")