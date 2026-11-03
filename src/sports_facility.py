"""서울체육맵: 공공체육시설 한 개를 표현하는 클래스."""


class SportsFacility:
    def __init__(self, name, district, facility_type, owner=None,
                 manager=None, area=None):
        self.name = name
        self.district = district
        self.facility_type = facility_type
        self.owner = owner
        self.manager = manager
        self.area = area

    def get_info(self):
        """화면에 표시할 시설 정보를 딕셔너리로 반환한다."""
        return {
            "시설명": self.name,
            "자치구": self.district,
            "시설종류": self.facility_type,
            "소유기관": self.owner,
            "관리주체": self.manager,
            "부지면적": self.area,
        }

    def has_detail(self):
        """세부 정보를 확인할 수 있는 시설인지 판단한다."""
        return self.facility_type != "간이운동장" and any(
            value is not None for value in (self.owner, self.manager, self.area)
        )

    def __str__(self):
        return f"{self.name} ({self.district}, {self.facility_type})"
