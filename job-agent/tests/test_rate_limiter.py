from datetime import datetime, timezone

import pytest

from app.services.rate_limiter import RateLimitExceeded, RateLimiter


def test_per_user_hour_limit() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    limiter = RateLimiter(per_user_hour=2, per_user_day=5, global_day=10, now=lambda: now)
    limiter.consume("user-a")
    limiter.consume("user-a")

    with pytest.raises(RateLimitExceeded, match="每小时"):
        limiter.consume("user-a")


def test_global_daily_budget() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    limiter = RateLimiter(per_user_hour=5, per_user_day=5, global_day=2, now=lambda: now)
    limiter.consume("user-a")
    limiter.consume("user-b")

    with pytest.raises(RateLimitExceeded, match="预算"):
        limiter.consume("user-c")
