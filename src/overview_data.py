"""현황 전용 출처별 스냅샷. 검색용 통합 목록과 예약 API를 사용하지 않는다."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
import time

from .api_clients import FacilityApi, NATIONAL, SEOUL, SourceResult
from .config import FACILITY_CACHE_TTL
from .http_client import JsonTransport

KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class OverviewSnapshot:
    result: SourceResult
    fetched_at: datetime


class OverviewService:
    def __init__(self, apis, *, clock=time.monotonic, now=None):
        self.apis = apis
        self.clock = clock
        self.now = now or (lambda: datetime.now(KST))
        self._snapshots = {}
        self._lock = RLock()

    @classmethod
    def from_settings(cls, settings):
        return cls(
            {
                NATIONAL: FacilityApi(NATIONAL, settings.national_key, JsonTransport()),
                SEOUL: FacilityApi(SEOUL, settings.seoul_key, JsonTransport()),
            }
        )

    def load(self, source, *, refresh=False):
        api = self.apis[source]
        with self._lock:
            if refresh:
                self._snapshots.pop(source, None)
                api.transport.clear()
            cached = self._snapshots.get(source)
            if cached and self.clock() < cached[0]:
                return deepcopy(cached[1])
            # 스냅샷 갱신 시 페이지 캐시도 비워 한 번의 조회 묶음으로 읽는다.
            api.transport.clear()
            result = api.fetch()
            snapshot = OverviewSnapshot(result, self.now())
            # 실패·일부 응답은 스냅샷으로 고정하지 않고 다음 실행에서 재시도한다.
            if result.state == "ok":
                self._snapshots[source] = (self.clock() + FACILITY_CACHE_TTL, snapshot)
            return deepcopy(snapshot)
