"""In-process budget guard for a single Streamlit deployment instance."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable


class RateLimitExceeded(RuntimeError):
    pass


class RateLimiter:
    def __init__(
        self,
        per_user_hour: int = 6,
        per_user_day: int = 20,
        global_day: int = 100,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.per_user_hour = per_user_hour
        self.per_user_day = per_user_day
        self.global_day = global_day
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._global_events: deque[datetime] = deque()
        self._lock = Lock()

    def consume(self, user_id: str) -> None:
        current = self._now()
        hour_ago = current - timedelta(hours=1)
        day_ago = current - timedelta(days=1)
        with self._lock:
            user_events = self._events[user_id]
            while user_events and user_events[0] <= day_ago:
                user_events.popleft()
            while self._global_events and self._global_events[0] <= day_ago:
                self._global_events.popleft()

            hourly_count = sum(event > hour_ago for event in user_events)
            if hourly_count >= self.per_user_hour:
                raise RateLimitExceeded("本账号每小时的 AI 调用次数已达到上限。")
            if len(user_events) >= self.per_user_day:
                raise RateLimitExceeded("本账号今天的 AI 调用次数已达到上限。")
            if len(self._global_events) >= self.global_day:
                raise RateLimitExceeded("应用今天的 AI 调用预算已用完，请明天再试。")

            user_events.append(current)
            self._global_events.append(current)
