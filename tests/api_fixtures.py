"""공식 응답 필드를 따르는 가상 데이터. 실제 시설/예약이 아니다."""

from copy import deepcopy
from urllib.parse import urlsplit

import requests

SEOUL_ROWS = [
    {
        "FT_IDX": 1,
        "AR_CD_NAME": "노원",
        "FT_TITLE": "가상 구민수영장",
        "BK_CD_NAME": "공공체육시설",
        "FT_KIND_NAME": "수영장",
        "FT_ADDR": "서울특별시 노원구 가상로 10",
        "FT_ADDR_DETAIL": "지하 1층",
        "FT_WD_TIME": "06:00~22:00",
        "FT_WE_TIME": "09:00~18:00",
        "FT_PHONE": "02-000-0000",
        "FT_MONEY": "성인 5,000원",
        "FT_ORG": "가상시설공단",
        "FT_HOMEPAGE": "https://example.org/pool",
        "FT_SIZE": "성인풀 5레인",
    },
    {
        "FT_IDX": 2,
        "AR_CD_NAME": "강남",
        "FT_TITLE": "가상 테니스장",
        "BK_CD_NAME": "공공체육시설",
        "FT_KIND_NAME": "테니스장",
        "FT_ADDR": "서울특별시 강남구 가상로 20",
    },
    {
        "FT_IDX": 3,
        "AR_CD_NAME": "노원",
        "FT_TITLE": "가상 학교",
        "BK_CD_NAME": "학교체육시설",
        "FT_KIND_NAME": "체육관",
    },
]
NATIONAL_ROWS = [
    {
        "faci_cd": "n1",
        "faci_nm": "가상구민수영장",
        "faci_gb_nm": "공공",
        "ftype_nm": "수영장",
        "cp_nm": "서울특별시",
        "cpb_nm": "노원구",
        "faci_road_addr": "서울시 노원구 가상로 10",
        "faci_road_daddr": "지하 1층",
        "faci_lat": "37.65",
        "faci_lot": "127.05",
        "faci_gfa": "1234",
    },
    {
        "faci_cd": "n2",
        "faci_nm": "가상 보완수영장",
        "faci_gb_nm": "공공",
        "ftype_nm": "수영장",
        "cp_nm": "서울특별시",
        "cpb_nm": "강남구",
        "faci_road_addr": "서울특별시 강남구 가상로 30",
        "faci_tel_no": "02-000-1111",
        "faci_lat": "37.5",
        "faci_lot": "127.04",
    },
    {
        "faci_cd": "private",
        "faci_nm": "가상 민간수영장",
        "faci_gb_nm": "신고",
        "ftype_nm": "수영장",
        "cp_nm": "서울특별시",
        "cpb_nm": "노원구",
    },
    {
        "faci_cd": "other",
        "faci_nm": "가상 타지역시설",
        "faci_gb_nm": "공공",
        "ftype_nm": "수영장",
        "cp_nm": "부산광역시",
        "cpb_nm": "중구",
    },
]
RESERVATION_ROWS = [
    {
        "SVCID": "r1",
        "SVCNM": "가상 구민수영장 평일 자유수영",
        "PLACENM": "가상 구민수영장",
        "AREANM": "노원구",
        "MINCLASSNM": "수영장",
        "SVCSTATNM": "접수중",
        "RCPTBGNDT": "2026-11-01 09:00",
        "RCPTENDDT": "2026-11-30 18:00",
        "SVCOPNBGNDT": "2026-12-01",
        "SVCOPNENDDT": "2026-12-31",
        "PAYATNM": "유료",
        "SVCURL": "https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=r1",
    },
    {
        "SVCID": "r2",
        "SVCNM": "가상 구민수영장 주말 자유수영",
        "PLACENM": "가상 구민수영장",
        "AREANM": "노원구",
        "MINCLASSNM": "수영장",
        "SVCSTATNM": "예약마감",
        "RCPTBGNDT": "2026-11-01",
        "RCPTENDDT": "2026-11-20",
        "SVCURL": "https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=r2",
    },
    {
        "SVCID": "r3",
        "SVCNM": "동명 다른 구",
        "PLACENM": "가상 구민수영장",
        "AREANM": "강남구",
        "MINCLASSNM": "수영장",
    },
    {
        "SVCID": "r4",
        "SVCNM": "다른 종목",
        "PLACENM": "가상 구민수영장",
        "AREANM": "노원구",
        "MINCLASSNM": "테니스장",
    },
]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return deepcopy(self.payload)


class ApiHTTP:
    """실제 HTTP 경계에서만 대체하여 앱/정규화/검색/캐시 코드를 그대로 실행한다."""

    def __init__(self, fail="", empty=False):
        self.fail, self.empty = fail, empty
        self.calls = []

    def __call__(self, url, params=None, timeout=None):
        if "ListPublicReservationSport" in url:
            source, rows = "reservation", RESERVATION_ROWS
        elif "/facilities/" in url:
            source, rows = "seoul", SEOUL_ROWS
        else:
            source, rows = "national", NATIONAL_ROWS
        self.calls.append((source, url, deepcopy(params), timeout))
        if self.fail == source:
            raise requests.Timeout("fake transport exception includes test key in URL")
        rows = [] if self.empty else deepcopy(rows)
        if source == "national":
            start = (int(params["pageNo"]) - 1) * int(params["numOfRows"])
            size = int(params["numOfRows"])
            return FakeResponse(
                {
                    "response": {
                        "header": {"resultCode": "00"},
                        "body": {
                            "totalCount": len(rows),
                            "items": {"item": rows[start : start + size]},
                        },
                    }
                }
            )
        parts = urlsplit(url).path.strip("/").split("/")
        start, end = int(parts[-2]), int(parts[-1])
        service = "facilities" if source == "seoul" else "ListPublicReservationSport"
        return FakeResponse(
            {
                service: {
                    "RESULT": {"CODE": "INFO-000"},
                    "list_total_count": len(rows),
                    "row": rows[start - 1 : end],
                }
            }
        )
