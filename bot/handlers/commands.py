from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.handlers.deps import Deps
from bot.services.formatting import format_day_agenda, format_event_card, format_week_agenda
from bot.utils.tz import day_bounds, week_bounds

router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(msg: Message, deps: Deps) -> None:
    if msg.from_user is None:
        return
    user = await deps.user_repo.upsert(
        user_id=msg.from_user.id,
        username=msg.from_user.username,
        first_name=msg.from_user.first_name,
        timezone=deps.settings.default_timezone,
        language=deps.settings.default_language,
    )
    deps.digest.schedule_for_user(user)
    await msg.answer(
        "Привет! Я твой персональный планер 🗓\n\n"
        "Пиши задачи и встречи свободным текстом или голосом — например:\n"
        "• «завтра в 9 встреча с Джахонгиром, напомни за 20 минут»\n"
        "• «каждый понедельник тренировка в 19:00»\n"
        "• «через 2 часа позвонить маме»\n\n"
        "Команды:\n"
        "/today — план на сегодня\n"
        "/week — на неделю\n"
        "/upcoming — ближайшие события",
    )


@router.message(Command("today"))
async def cmd_today(msg: Message, deps: Deps) -> None:
    if msg.from_user is None:
        return
    user = await deps.user_repo.get(msg.from_user.id)
    tz = user.timezone if user else deps.settings.default_timezone
    start, end = day_bounds(tz)
    events = await deps.event_repo.list_in_range(msg.from_user.id, start, end)
    await msg.answer(
        format_day_agenda(events, tz, "*Сегодня:*"),
        parse_mode="Markdown",
    )


@router.message(Command("tomorrow"))
async def cmd_tomorrow(msg: Message, deps: Deps) -> None:
    if msg.from_user is None:
        return
    user = await deps.user_repo.get(msg.from_user.id)
    tz = user.timezone if user else deps.settings.default_timezone
    start, end = day_bounds(tz, day_offset=1)
    events = await deps.event_repo.list_in_range(msg.from_user.id, start, end)
    await msg.answer(
        format_day_agenda(events, tz, "*Завтра:*"),
        parse_mode="Markdown",
    )


@router.message(Command("week"))
async def cmd_week(msg: Message, deps: Deps) -> None:
    if msg.from_user is None:
        return
    user = await deps.user_repo.get(msg.from_user.id)
    tz = user.timezone if user else deps.settings.default_timezone
    start, end = week_bounds(tz)
    events = await deps.event_repo.list_in_range(msg.from_user.id, start, end)
    await msg.answer(format_week_agenda(events, tz), parse_mode="Markdown")


@router.message(Command("upcoming"))
async def cmd_upcoming(msg: Message, deps: Deps) -> None:
    if msg.from_user is None:
        return
    user = await deps.user_repo.get(msg.from_user.id)
    tz = user.timezone if user else deps.settings.default_timezone
    events = await deps.event_repo.list_upcoming(msg.from_user.id, limit=5)
    if not events:
        await msg.answer("Ближайших событий нет ✨")
        return
    text = "*Ближайшие события:*\n\n" + "\n\n".join(format_event_card(e, tz) for e in events)
    await msg.answer(text, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(msg: Message, deps: Deps) -> None:
    if msg.from_user is None:
        return
    await deps.pending_repo.clear(msg.from_user.id)
    await msg.answer("Отменил текущий черновик ✓")
