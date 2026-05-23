from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import TelegramObject
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from openai import AsyncOpenAI

from bot.config import get_settings
from bot.db.client import Database
from bot.db.repositories import (
    ConversationRepo,
    EventRepo,
    PendingEventRepo,
    ReminderRepo,
    UserRepo,
)
from bot.handlers import callbacks, commands, text, voice
from bot.handlers.deps import Deps
from bot.services.digest import DigestService
from bot.services.nlu import NLUService
from bot.services.reminders import ReminderService
from bot.services.whisper import WhisperService

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


class DepsMiddleware(BaseMiddleware):
    def __init__(self, deps: Deps) -> None:
        self._deps = deps

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["deps"] = self._deps
        return await handler(event, data)


class AccessMiddleware(BaseMiddleware):
    def __init__(self, allowed_ids: set[int]) -> None:
        self._allowed = allowed_ids

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not self._allowed:
            return await handler(event, data)
        user = getattr(event, "from_user", None)
        if user is None or user.id in self._allowed:
            return await handler(event, data)
        return None


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger(__name__)

    db = Database(settings.database_url)
    await db.connect()
    await db.apply_migrations(Path(__file__).parent.parent / "migrations")

    user_repo = UserRepo(db)
    event_repo = EventRepo(db)
    reminder_repo = ReminderRepo(db)
    pending_repo = PendingEventRepo(db)
    conversation_repo = ConversationRepo(db)

    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    nlu = NLUService(openai_client, settings.openai_nlu_model)
    whisper = WhisperService(openai_client, settings.openai_whisper_model)

    bot = Bot(token=settings.bot_token)
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.start()

    reminder_service = ReminderService(bot, scheduler, reminder_repo, event_repo, user_repo)
    digest_service = DigestService(bot, scheduler, user_repo, event_repo)

    deps = Deps(
        settings=settings,
        user_repo=user_repo,
        event_repo=event_repo,
        reminder_repo=reminder_repo,
        pending_repo=pending_repo,
        conversation_repo=conversation_repo,
        nlu=nlu,
        whisper=whisper,
        reminders=reminder_service,
        digest=digest_service,
    )

    dp = Dispatcher()
    dp.update.middleware(DepsMiddleware(deps))
    dp.update.middleware(AccessMiddleware(settings.allowed_user_ids))
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)
    dp.include_router(voice.router)
    dp.include_router(text.router)

    restored = await reminder_service.restore_pending()
    log.info("Restored %d pending reminders", restored)

    # Schedule digests for all existing users with digest enabled.
    for hour in range(24):
        for user in await user_repo.list_with_digest(hour):
            digest_service.schedule_for_user(user)

    log.info("Bot starting (long polling)…")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
