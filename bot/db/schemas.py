from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Weekday = Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
Freq = Literal["daily", "weekly", "monthly", "yearly"]


class Recurrence(BaseModel):
    freq: Freq
    interval: int = 1
    byweekday: list[Weekday] = Field(default_factory=list)
    until: datetime | None = None


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None = None
    first_name: str | None = None
    timezone: str = "Asia/Tashkent"
    language: str = "ru"
    daily_digest: bool = True
    digest_hour: int = 8
    created_at: datetime | None = None


class Event(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    title: str
    start_at: datetime
    end_at: datetime | None = None
    location: str | None = None
    notes: str | None = None
    participants: list[str] = Field(default_factory=list)
    recurrence: Recurrence | None = None
    source: str = "telegram"
    gcal_event_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Reminder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: int
    fire_at: datetime
    offset_min: int
    status: Literal["pending", "sent", "failed", "cancelled"] = "pending"
    sent_at: datetime | None = None


# Draft used during multi-turn clarification before committing to events table.
class EventDraft(BaseModel):
    title: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    location: str | None = None
    notes: str | None = None
    participants: list[str] = Field(default_factory=list)
    reminder_offsets_minutes: list[int] = Field(default_factory=lambda: [15])
    recurrence: Recurrence | None = None

    def merge(self, other: EventDraft) -> EventDraft:
        merged_data: dict[str, Any] = self.model_dump()
        for key, value in other.model_dump().items():
            # Skip empty / default-y values so we don't overwrite known fields.
            if value in (None, [], "") and key != "reminder_offsets_minutes":
                continue
            if key == "reminder_offsets_minutes" and value == [15]:
                continue
            merged_data[key] = value
        return EventDraft(**merged_data)


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime | None = None
