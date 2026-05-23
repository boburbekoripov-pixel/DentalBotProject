from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def now_in(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def day_bounds(tz_name: str, day_offset: int = 0) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start = (now + timedelta(days=day_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def week_bounds(tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=7)


def to_user_tz(dt: datetime, tz_name: str) -> datetime:
    return dt.astimezone(ZoneInfo(tz_name))


def ensure_aware(dt: datetime, tz_name: str) -> datetime:
    """Attach a timezone to naive datetimes; passes aware datetimes through."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo(tz_name))
    return dt
