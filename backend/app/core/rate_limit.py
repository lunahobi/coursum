from collections import deque
from threading import Lock
from time import monotonic

from app.core.config import get_settings


class FixedWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def hit(self, key: str) -> bool:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            window = self._events.setdefault(key, deque())
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= self.limit:
                return False
            window.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_settings = get_settings()
auth_rate_limiter = FixedWindowRateLimiter(
    limit=_settings.auth_rate_limit_attempts,
    window_seconds=_settings.auth_rate_limit_window_seconds,
)
