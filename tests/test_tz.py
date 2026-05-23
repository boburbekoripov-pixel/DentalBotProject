from datetime import datetime
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from bot.utils.tz import day_bounds, ensure_aware, now_in, to_user_tz, week_bounds


@freeze_time("2026-05-23 12:00:00", tz_offset=0)
def test_now_in_returns_user_local_time() -> None:
    now = now_in("Asia/Tashkent")
    assert now.tzinfo == ZoneInfo("Asia/Tashkent")
    # 12:00 UTC == 17:00 Tashkent
    assert now.hour == 17


@freeze_time("2026-05-23 12:00:00", tz_offset=0)
def test_day_bounds_starts_at_midnight_local() -> None:
    start, end = day_bounds("Asia/Tashkent")
    assert start.hour == 0
    assert start.minute == 0
    assert start.tzinfo == ZoneInfo("Asia/Tashkent")
    assert (end - start).days == 1


@freeze_time("2026-05-23 12:00:00", tz_offset=0)
def test_day_bounds_with_offset() -> None:
    start_today, _ = day_bounds("UTC")
    start_tomorrow, _ = day_bounds("UTC", day_offset=1)
    assert (start_tomorrow - start_today).days == 1


@freeze_time("2026-05-23 12:00:00", tz_offset=0)
def test_week_bounds_is_7_days() -> None:
    start, end = week_bounds("UTC")
    assert (end - start).days == 7


def test_ensure_aware_attaches_tz_for_naive() -> None:
    naive = datetime(2026, 5, 23, 9, 0)
    aware = ensure_aware(naive, "Asia/Tashkent")
    assert aware.tzinfo == ZoneInfo("Asia/Tashkent")


def test_ensure_aware_passes_through_aware() -> None:
    aware = datetime(2026, 5, 23, 9, 0, tzinfo=ZoneInfo("UTC"))
    result = ensure_aware(aware, "Asia/Tashkent")
    assert result.tzinfo == ZoneInfo("UTC")


def test_to_user_tz_converts_correctly() -> None:
    utc_dt = datetime(2026, 5, 23, 12, 0, tzinfo=ZoneInfo("UTC"))
    tashkent = to_user_tz(utc_dt, "Asia/Tashkent")
    assert tashkent.hour == 17
