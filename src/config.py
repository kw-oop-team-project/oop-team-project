"""인증 정보는 메모리에서만 사용한다."""

from collections.abc import Mapping
from dataclasses import dataclass, field
import os

HTTP_TIMEOUT = (3.05, 12)
FACILITY_CACHE_TTL = 300
RESERVATION_CACHE_TTL = 60
API_PAGE_SIZE = 500
API_MAX_PAGES = 100
RESULT_PAGE_SIZE = 25


DISTRICTS = tuple(
    sorted(
        f"{name}구"
        for name in (
            "강남",
            "강동",
            "강북",
            "강서",
            "관악",
            "광진",
            "구로",
            "금천",
            "노원",
            "도봉",
            "동대문",
            "동작",
            "마포",
            "서대문",
            "서초",
            "성동",
            "성북",
            "송파",
            "양천",
            "영등포",
            "용산",
            "은평",
            "종로",
            "중",
            "중랑",
        )
    )
)


@dataclass(frozen=True)
class ApiSettings:
    seoul_key: str = field(default="", repr=False)
    national_key: str = field(default="", repr=False)
    reservation_key: str = field(default="", repr=False)

    @property
    def effective_reservation_key(self):
        return self.reservation_key or self.seoul_key

    @classmethod
    def from_environment(cls, secrets: Mapping | None = None):
        secrets = secrets if secrets is not None else {}
        environment = dict(os.environ)

        def read(name):
            return str(environment.get(name) or secrets.get(name, "")).strip()

        return cls(
            read("SEOUL_OPEN_API_KEY"),
            read("DATA_GO_KR_SERVICE_KEY"),
            read("SEOUL_RESERVATION_API_KEY"),
        )
