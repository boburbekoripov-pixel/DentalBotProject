from __future__ import annotations

import contextlib
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.db.repositories import EventRepo, UserRepo
from bot.db.schemas import User
from bot.services.formatting import format_day_agenda
from bot.utils.tz import day_bounds

logger = logging.getLogger(__name__)


class DigestService:
    """Sends daily plan summaries. One cron job per user, fired in user's local timezone."""

    def __init__(
        self,
        bot: Bot,
        scheduler: AsyncIOScheduler,
        user_repo: UserRepo,
        event_repo: EventRepo,
    ) -> None:
        self._bot = bot
        self._scheduler = scheduler
        self._user_repo = user_repo
        self._event_repo = event_repo

    def schedule_for_user(self, user: User) -> None:
        job_id = f"digest-{user.id}"
        if not user.daily_digest:
            with contextlib.suppress(Exception):
                self._scheduler.remove_job(job_id)
            return
        self._scheduler.add_job(
            self._fire_for_user,
            trigger=CronTrigger(hour=user.digest_hour, minute=0, timezone=ZoneInfo(user.timezone)),
            args=[user.id],
            id=job_id,
            replace_existing=True,
        )

    async def _fire_for_user(self, user_id: int) -> None:
        user = await self._user_repo.get(user_id)
        if user is None or not user.daily_digest:
            return
        try:
            start, end = day_bounds(user.timezone)
            events = await self._event_repo.list_in_range(user.id, start, end)
            text = format_day_agenda(events, user.timezone, "☀️ Доброе утро! План на сегодня:")
            await self._bot.send_message(user.id, text, parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to send digest to %s", user_id)
