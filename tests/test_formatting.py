from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from bot.db.schemas import Event, Recurrence
from bot.services.formatting import (
    format_day_agenda,
    format_event_card,
    format_reminder,
    format_week_agenda,
)


def _event(title: str, start: datetime, **kwargs: object) -> Event:
    return Event(
        id=uuid4(),
        user_id=1,
        title=title,
        start_at=start,
        **kwargs,  # type: ignore[arg-type]
    )


def test_format_event_card_includes_title_and_time() -> None:
    e = _event("Встреча", datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("Asia/Tashkent")))
    card = format_event_card(e, "Asia/Tashkent")
    assert "Встреча" in card
    assert "09:00" in card
    assert "мая" in card


def test_format_event_card_includes_location_and_participants() -> None:
    e = _event(
        "Созвон",
        datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("Asia/Tashkent")),
        location="Zoom",
        participants=["Джахонгир", "Анна"],
    )
    card = format_event_card(e, "Asia/Tashkent")
    assert "Zoom" in card
    assert "Джахонгир" in card
    assert "Анна" in card


def test_format_event_card_recurrence_label() -> None:
    e = _event(
        "Тренировка",
        datetime(2026, 5, 25, 19, 0, tzinfo=ZoneInfo("Asia/Tashkent")),
        recurrence=Recurrence(freq="weekly", byweekday=["MO"]),
    )
    card = format_event_card(e, "Asia/Tashkent")
    assert "еженедельно" in card


def test_format_day_agenda_empty() -> None:
    text = format_day_agenda([], "UTC", "*Сегодня:*")
    assert "свободен" in text


def test_format_day_agenda_groups_events() -> None:
    events = [
        _event("A", datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("UTC"))),
        _event("B", datetime(2026, 5, 24, 14, 0, tzinfo=ZoneInfo("UTC"))),
    ]
    text = format_day_agenda(events, "UTC", "*Сегодня:*")
    assert "A" in text and "B" in text
    assert text.index("A") < text.index("B")


def test_format_week_agenda_groups_by_day() -> None:
    events = [
        _event("Mon", datetime(2026, 5, 25, 9, 0, tzinfo=ZoneInfo("UTC"))),
        _event("Wed", datetime(2026, 5, 27, 14, 0, tzinfo=ZoneInfo("UTC"))),
    ]
    text = format_week_agenda(events, "UTC")
    assert "Mon" in text and "Wed" in text


def test_format_reminder_minutes() -> None:
    e = _event("X", datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("UTC")))
    out = format_reminder(e, 20, "UTC")
    assert "20 мин" in out
    assert "X" in out


def test_format_reminder_hours() -> None:
    e = _event("Y", datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("UTC")))
    out = format_reminder(e, 120, "UTC")
    assert "2 ч" in out
