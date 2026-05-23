from datetime import datetime
from zoneinfo import ZoneInfo

from bot.db.schemas import EventDraft, Recurrence


def test_merge_keeps_existing_when_other_is_empty() -> None:
    base = EventDraft(
        title="Встреча",
        start_at=datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("UTC")),
    )
    other = EventDraft()  # all defaults
    merged = base.merge(other)
    assert merged.title == "Встреча"
    assert merged.start_at == base.start_at


def test_merge_overwrites_when_other_has_value() -> None:
    base = EventDraft(title="старое")
    other = EventDraft(title="новое")
    merged = base.merge(other)
    assert merged.title == "новое"


def test_merge_adds_missing_field() -> None:
    base = EventDraft(title="Встреча")
    other = EventDraft(start_at=datetime(2026, 5, 24, 9, 0, tzinfo=ZoneInfo("UTC")))
    merged = base.merge(other)
    assert merged.title == "Встреча"
    assert merged.start_at is not None


def test_merge_reminder_offsets_overwrite_only_when_non_default() -> None:
    base = EventDraft(title="X", reminder_offsets_minutes=[60])
    other = EventDraft()  # default [15] — should not overwrite
    merged = base.merge(other)
    assert merged.reminder_offsets_minutes == [60]


def test_merge_reminder_offsets_overwrite_when_explicit() -> None:
    base = EventDraft(title="X", reminder_offsets_minutes=[60])
    other = EventDraft(reminder_offsets_minutes=[20])
    merged = base.merge(other)
    assert merged.reminder_offsets_minutes == [20]


def test_recurrence_model_accepts_weekly() -> None:
    r = Recurrence(freq="weekly", byweekday=["MO", "WE"])
    assert r.interval == 1
    assert r.byweekday == ["MO", "WE"]
