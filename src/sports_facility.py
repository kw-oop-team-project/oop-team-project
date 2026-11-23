"""여러 공공 API의 시설 정보를 공통 객체로 표현한다."""

from dataclasses import dataclass, field
import hashlib


@dataclass
class SportsFacility:
    name: str
    district: str
    facility_type: str
    owner: str | None = None
    manager: str | None = None
    area: str | float | None = None
    facility_id: str = ""
    address: str = ""
    address_detail: str = ""
    hours: str = ""
    phone: str = ""
    fee: str = ""
    homepage: str = ""
    latitude: float | None = None
    longitude: float | None = None
    sources: tuple[str, ...] = ()
    source_details: dict = field(default_factory=dict)
    size: str = ""
    total_floor_area: str = ""

    def __post_init__(self):
        if not self.facility_id:
            identity = "|".join(
                (self.name, self.district, self.address, self.facility_type)
            )
            self.facility_id = (
                "facility:" + hashlib.sha256(identity.encode()).hexdigest()[:20]
            )

    def get_info(self):
        return {
            "name": self.name,
            "district": self.district,
            "facility_type": self.facility_type,
            "owner": self.owner,
            "manager": self.manager,
            "site_area": self.area,
            "address": " ".join(filter(None, (self.address, self.address_detail))),
            "hours": self.hours,
            "phone": self.phone,
            "fee": self.fee,
            "size": self.size,
            "total_floor_area": self.total_floor_area,
        }

    def has_detail(self):
        # 기본정보만 제공하는 API 시설도 검색·상세 화면에서 숨기지 않는다.
        return True

    def __str__(self):
        return f"{self.name} ({self.district}, {self.facility_type})"
