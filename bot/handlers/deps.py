"""Container of services injected into handlers via aiogram's workflow_data."""

from __future__ import annotations

from dataclasses import dataclass

from bot.config import Settings
from bot.db.repositories import (
    ConversationRepo,
    EventRepo,
    PendingEventRepo,
    ReminderRepo,
    UserRepo,
)
from bot.services.digest import DigestService
from bot.services.nlu import NLUService
from bot.services.reminders import ReminderService
from bot.services.whisper import WhisperService


@dataclass
class Deps:
    settings: Settings
    user_repo: UserRepo
    event_repo: EventRepo
    reminder_repo: ReminderRepo
    pending_repo: PendingEventRepo
    conversation_repo: ConversationRepo
    nlu: NLUService
    whisper: WhisperService
    reminders: ReminderService
    digest: DigestService
