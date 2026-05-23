from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.db.repositories import EventRepo, ReminderRepo, UserRepo
from bot.db.schemas import Event, Reminder
from bot.services.formatting import format_reminder

logger = logging.getLogger(__name__)


class ReminderService:
    """Schedules and fires reminders. Backed by APScheduler in-process."""

    def __init__(
        self,
        bot: Bot,
        scheduler: AsyncIOScheduler,
        reminder_repo: ReminderRepo,
        event_repo: EventRepo,
        user_repo: UserRepo,
    ) -> None:
        self._bot = bot
        self._scheduler = scheduler
        self._reminder_repo = reminder_repo
        self._event_repo = event_repo
        self._user_repo = user_repo

    async def schedule_for_event(self, event: Event, offsets_min: list[int]) -> list[Reminder]:
        """Create reminder rows for an event and register APScheduler jobs."""
        now = datetime.now(UTC)
        reminders: list[Reminder] = []
        for offset in sorted(set(offsets_min)):
            fire_at = event.start_at - timedelta(minutes=offset)
            if fire_at <= now:
                continue
            reminder = Reminder(
                id=uuid4(),
                event_id=event.id,
                user_id=event.user_id,
                fire_at=fire_at,
                offset_min=offset,
            )
            reminders.append(reminder)
        await self._reminder_repo.create_many(reminders)
        for r in reminders:
            self._schedule_job(r)
        return reminders

    def _schedule_job(self, reminder: Reminder) -> None:
        self._scheduler.add_job(
            self._fire,
            "date",
            run_date=reminder.fire_at,
            args=[reminder.id],
            id=f"rem-{reminder.id}",
            replace_existing=True,
            misfire_grace_time=300,
        )

    async def _fire(self, reminder_id: UUID) -> None:
        try:
            # Re-fetch from DB so we send fresh event data and survive bot restarts.
            pending = await self._reminder_repo.list_pending_after(
                datetime.now(UTC) - timedelta(hours=1),
            )
            target = next((r for r in pending if r.id == reminder_id), None)
            if target is None:
                logger.info("Reminder %s already processed", reminder_id)
                return
            event = await self._event_repo.get(target.event_id)
            if event is None:
                logger.warning("Reminder %s references missing event", reminder_id)
                await self._reminder_repo.mark_failed(reminder_id)
                return
            user = await self._user_repo.get(target.user_id)
            tz = user.timezone if user else "Asia/Tashkent"
            text = format_reminder(event, target.offset_min, tz)
            await self._bot.send_message(target.user_id, text, parse_mode="Markdown")
            await self._reminder_repo.mark_sent(reminder_id)
        except Exception:
            logger.exception("Failed to send reminder %s", reminder_id)
            await self._reminder_repo.mark_failed(reminder_id)

    async def restore_pending(self) -> int:
        """Re-register all pending reminders on bot startup."""
        now = datetime.now(UTC)
        pending = await self._reminder_repo.list_pending_after(now)
        for r in pending:
            self._schedule_job(r)
        logger.info("Restored %d pending reminders", len(pending))
        return len(pending)
