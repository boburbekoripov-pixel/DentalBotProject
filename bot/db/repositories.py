from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from .client import Database
from .schemas import ConversationMessage, Event, EventDraft, Recurrence, Reminder, User


def _event_from_row(row: dict[str, Any]) -> Event:
    recurrence = None
    if row.get("recurrence"):
        recurrence_dict = row["recurrence"]
        if isinstance(recurrence_dict, str):
            recurrence_dict = json.loads(recurrence_dict)
        recurrence = Recurrence(**recurrence_dict)
    return Event(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        start_at=row["start_at"],
        end_at=row["end_at"],
        location=row["location"],
        notes=row["notes"],
        participants=list(row["participants"] or []),
        recurrence=recurrence,
        source=row["source"],
        gcal_event_id=row["gcal_event_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class UserRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def upsert(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        timezone: str = "Asia/Tashkent",
        language: str = "ru",
    ) -> User:
        row = await self.db.pool.fetchrow(
            """
            INSERT INTO users (id, username, first_name, timezone, language)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE
              SET username = EXCLUDED.username,
                  first_name = EXCLUDED.first_name
            RETURNING *
            """,
            user_id,
            username,
            first_name,
            timezone,
            language,
        )
        assert row is not None
        return User(**dict(row))

    async def get(self, user_id: int) -> User | None:
        row = await self.db.pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return User(**dict(row)) if row else None

    async def list_with_digest(self, hour: int) -> list[User]:
        rows = await self.db.pool.fetch(
            "SELECT * FROM users WHERE daily_digest = TRUE AND digest_hour = $1",
            hour,
        )
        return [User(**dict(r)) for r in rows]


class EventRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, user_id: int, draft: EventDraft) -> Event:
        if draft.title is None or draft.start_at is None:
            raise ValueError("Draft must have title and start_at to be created")
        recurrence_json = (
            json.dumps(draft.recurrence.model_dump(mode="json")) if draft.recurrence else None
        )
        row = await self.db.pool.fetchrow(
            """
            INSERT INTO events (user_id, title, start_at, end_at, location, notes,
                                participants, recurrence)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            user_id,
            draft.title,
            draft.start_at,
            draft.end_at,
            draft.location,
            draft.notes,
            draft.participants,
            recurrence_json,
        )
        assert row is not None
        return _event_from_row(dict(row))

    async def get(self, event_id: UUID) -> Event | None:
        row = await self.db.pool.fetchrow("SELECT * FROM events WHERE id = $1", event_id)
        return _event_from_row(dict(row)) if row else None

    async def delete(self, event_id: UUID, user_id: int) -> bool:
        result: str = await self.db.pool.execute(
            "DELETE FROM events WHERE id = $1 AND user_id = $2",
            event_id,
            user_id,
        )
        return bool(result.endswith(" 1"))

    async def list_in_range(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> list[Event]:
        rows = await self.db.pool.fetch(
            """
            SELECT * FROM events
            WHERE user_id = $1 AND start_at >= $2 AND start_at < $3
            ORDER BY start_at
            """,
            user_id,
            start,
            end,
        )
        return [_event_from_row(dict(r)) for r in rows]

    async def list_upcoming(self, user_id: int, limit: int = 5) -> list[Event]:
        rows = await self.db.pool.fetch(
            """
            SELECT * FROM events
            WHERE user_id = $1 AND start_at >= NOW()
            ORDER BY start_at
            LIMIT $2
            """,
            user_id,
            limit,
        )
        return [_event_from_row(dict(r)) for r in rows]


class ReminderRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create_many(self, reminders: list[Reminder]) -> None:
        if not reminders:
            return
        await self.db.pool.executemany(
            """
            INSERT INTO reminders (id, event_id, user_id, fire_at, offset_min, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            [(r.id, r.event_id, r.user_id, r.fire_at, r.offset_min, r.status) for r in reminders],
        )

    async def mark_sent(self, reminder_id: UUID) -> None:
        await self.db.pool.execute(
            "UPDATE reminders SET status = 'sent', sent_at = NOW() WHERE id = $1",
            reminder_id,
        )

    async def mark_failed(self, reminder_id: UUID) -> None:
        await self.db.pool.execute(
            "UPDATE reminders SET status = 'failed' WHERE id = $1",
            reminder_id,
        )

    async def list_pending_after(self, after: datetime) -> list[Reminder]:
        rows = await self.db.pool.fetch(
            """
            SELECT * FROM reminders
            WHERE status = 'pending' AND fire_at > $1
            ORDER BY fire_at
            """,
            after,
        )
        return [Reminder(**dict(r)) for r in rows]


class PendingEventRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def upsert(self, user_id: int, draft: EventDraft, question: str | None) -> None:
        await self.db.pool.execute(
            """
            INSERT INTO pending_events (user_id, draft, question)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
              SET draft = EXCLUDED.draft,
                  question = EXCLUDED.question,
                  updated_at = NOW()
            """,
            user_id,
            json.dumps(draft.model_dump(mode="json")),
            question,
        )

    async def get(self, user_id: int) -> tuple[EventDraft, str | None] | None:
        row = await self.db.pool.fetchrow(
            "SELECT draft, question FROM pending_events WHERE user_id = $1",
            user_id,
        )
        if not row:
            return None
        draft_data = row["draft"]
        if isinstance(draft_data, str):
            draft_data = json.loads(draft_data)
        return EventDraft(**draft_data), row["question"]

    async def clear(self, user_id: int) -> None:
        await self.db.pool.execute("DELETE FROM pending_events WHERE user_id = $1", user_id)

    async def is_stale(self, user_id: int, max_age: timedelta) -> bool:
        row = await self.db.pool.fetchrow(
            "SELECT updated_at FROM pending_events WHERE user_id = $1",
            user_id,
        )
        if not row:
            return False
        age = datetime.now(row["updated_at"].tzinfo) - row["updated_at"]
        return bool(age > max_age)


class ConversationRepo:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def append(self, user_id: int, role: str, content: str) -> None:
        await self.db.pool.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES ($1, $2, $3)",
            user_id,
            role,
            content,
        )

    async def last(self, user_id: int, limit: int = 10) -> list[ConversationMessage]:
        rows = await self.db.pool.fetch(
            """
            SELECT role, content, created_at FROM conversations
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
        return list(reversed([ConversationMessage(**dict(r)) for r in rows]))
