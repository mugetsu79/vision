from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from argus.services.app import (
    _MAX_HISTORY_BUCKETS,
    _ensure_history_window,
    _effective_granularity,
)


def test_effective_granularity_keeps_requested_when_under_cap() -> None:
    starts = datetime(2026, 4, 23, tzinfo=timezone.utc)
    ends = starts + timedelta(hours=1)  # 60 one-minute buckets, well under 500
    assert _effective_granularity("1m", starts_at=starts, ends_at=ends) == ("1m", False)


def test_effective_granularity_bumps_when_buckets_exceed_cap() -> None:
    starts = datetime(2026, 4, 23, tzinfo=timezone.utc)
    # 10 days at 1m is 14400 buckets, way over 500 -> bump
    ends = starts + timedelta(days=10)
    new, adjusted = _effective_granularity("1m", starts_at=starts, ends_at=ends)
    assert adjusted is True
    assert new in {"5m", "1h", "1d"}


def test_ensure_history_window_rejects_over_31_days() -> None:
    starts = datetime(2026, 4, 1, tzinfo=timezone.utc)
    ends = starts + timedelta(days=32)
    with pytest.raises(Exception) as info:
        _ensure_history_window(starts, ends)
    assert "31 days" in str(info.value)


def test_ensure_history_window_allows_exactly_31_days() -> None:
    starts = datetime(2026, 4, 1, tzinfo=timezone.utc)
    ends = starts + timedelta(days=31)
    _ensure_history_window(starts, ends)  # no raise
