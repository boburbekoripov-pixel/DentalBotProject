from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from bot.db.schemas import Event

WEEKDAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS_RU = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]


def _format_dt(dt: datetime, tz_name: str) -> str:
    local = dt.astimezone(ZoneInfo(tz_name))
    return f"{local.day} {MONTHS_RU[local.month - 1]}, {local.strftime('%H:%M')}"


def _format_time(dt: datetime, tz_name: str) -> str:
    return dt.astimezone(ZoneInfo(tz_name)).strftime("%H:%M")


def format_event_card(event: Event, tz_name: str) -> str:
    parts = [f"📌 *{event.title}*", f"🕐 {_format_dt(event.start_at, tz_name)}"]
    if event.end_at:
        parts.append(f"   до {_format_time(event.end_at, tz_name)}")
    if event.location:
        parts.append(f"📍 {event.location}")
    if event.participants:
        parts.append(f"👥 {', '.join(event.participants)}")
    if event.recurrence:
        rec = event.recurrence
        rec_text = {
            "daily": "ежедневно",
            "weekly": "еженедельно",
            "monthly": "ежемесячно",
            "yearly": "ежегодно",
        }[rec.freq]
        parts.append(f"🔁 {rec_text}")
    if event.notes:
        parts.append(f"💬 {event.notes}")
    return "\n".join(parts)


def format_day_agenda(events: list[Event], tz_name: str, header: str) -> str:
    if not events:
        return f"{header}\n\nСобытий нет — день свободен ✨"
    lines = [header, ""]
    for e in events:
        lines.append(f"• {_format_time(e.start_at, tz_name)} — *{e.title}*")
        if e.location:
            lines.append(f"  📍 {e.location}")
    return "\n".join(lines)


def format_week_agenda(events: list[Event], tz_name: str) -> str:
    if not events:
        return "На неделю событий нет ✨"
    tz = ZoneInfo(tz_name)
    by_day: dict[str, list[Event]] = {}
    for e in events:
        key = e.start_at.astimezone(tz).strftime("%Y-%m-%d")
        by_day.setdefault(key, []).append(e)
    lines = ["*Неделя:*", ""]
    for day in sorted(by_day):
        d = datetime.strptime(day, "%Y-%m-%d")
        weekday = WEEKDAYS_RU[d.weekday()]
        lines.append(f"*{weekday}, {d.day} {MONTHS_RU[d.month - 1]}*")
        for e in by_day[day]:
            lines.append(f"  • {_format_time(e.start_at, tz_name)} — {e.title}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_reminder(event: Event, offset_min: int, tz_name: str) -> str:
    if offset_min == 0:
        when = "сейчас"
    elif offset_min < 60:
        when = f"через {offset_min} мин"
    else:
        hours = offset_min // 60
        when = f"через {hours} ч"
    return f"⏰ Напоминание: *{event.title}* {when}\n🕐 {_format_time(event.start_at, tz_name)}" + (
        f"\n📍 {event.location}" if event.location else ""
    )
