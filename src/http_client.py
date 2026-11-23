"""인증 정보를 출력하지 않는 HTTP 호출과 TTL 메모리 캐시."""

from copy import deepcopy
import hashlib
import json
import time
from threading import RLock

import requests

from .config import FACILITY_CACHE_TTL, HTTP_TIMEOUT


class ApiError(Exception):
    """키나 원본 응답을 포함하지 않는 사용자 표시용 오류."""


class JsonTransport:
    """성공한 JSON만 TTL 동안 메모리에 보관. 디스크/로그에 키를 저장하지 않는다."""

    def __init__(self, session=None, clock=time.monotonic):
        self.session = session or requests.Session()
        self.clock = clock
        self._cache = {}
        self._lock = RLock()

    def clear(self):
        with self._lock:
            self._cache.clear()

    def get(self, url, params=None, ttl=FACILITY_CACHE_TTL):
        identity = json.dumps([url, params], sort_keys=True, ensure_ascii=False)
        cache_key = hashlib.sha256(identity.encode()).digest()
        with self._lock:
            now = self.clock()
            cached = self._cache.get(cache_key)
            if cached and cached[0] > now:
                return deepcopy(cached[1])
            try:
                response = self.session.get(url, params=params, timeout=HTTP_TIMEOUT)
                response.raise_for_status()
            except requests.Timeout:
                raise ApiError(
                    "API 응답 시간이 초과되었습니다. 잠시 후 다시 조회해 주세요."
                ) from None
            except requests.RequestException:
                raise ApiError(
                    "API 연결 또는 HTTP 오류가 발생했습니다. 잠시 후 다시 조회해 주세요."
                ) from None
            try:
                payload = response.json()
            except ValueError:
                raise ApiError(
                    "API가 JSON을 반환하지 않았습니다. 인증키와 서비스 이용 승인을 확인해 주세요."
                ) from None
            if not isinstance(payload, dict):
                raise ApiError("API 응답 형식이 올바르지 않습니다.")
            # API가 HTTP 200으로 전달하는 오류 응답은 캐시하지 않는다.
            roots = [payload] + [v for v in payload.values() if isinstance(v, dict)]
            codes = [r.get("RESULT", {}).get("CODE") for r in roots]
            codes += [r.get("header", {}).get("resultCode") for r in roots]
            if any(c is not None for c in codes) and all(
                c in (None, "INFO-000", "INFO-200", "00", "0", 0) for c in codes
            ):
                self._cache[cache_key] = (now + ttl, deepcopy(payload))
                if len(self._cache) > 256:
                    self._cache = {k: v for k, v in self._cache.items() if v[0] > now}
                    if len(self._cache) > 256:
                        self._cache.pop(next(iter(self._cache)))
            return payload
