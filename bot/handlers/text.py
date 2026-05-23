from __future__ import annotations

import json
import logging
from datetime import timedelta

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.db.schemas import EventDraft
from bot.handlers.deps import Deps
from bot.services.formatting import format_event_card
from bot.services.nlu import NLUResult
from bot.utils.tz import ensure_aware, now_in

router = Router(name="text")
logger = logging.getLogger(__name__)

PENDING_TTL = timedelta(minutes=30)


async def process_user_text(msg: Message, deps: Deps, text: str) -> None:
    if msg.from_user is None:
        return
    user_id = msg.from_user.id
    user = await deps.user_repo.get(user_id)
    if user is None:
        user = await deps.user_repo.upsert(
            user_id=user_id,
            username=msg.from_user.username,
            first_name=msg.from_user.first_name,
            timezone=deps.settings.default_timezone,
            language=deps.settings.default_language,
        )
        deps.digest.schedule_for_user(user)

    # Drop stale clarification draft.
    if await deps.pending_repo.is_stale(user_id, PENDING_TTL):
        await deps.pending_repo.clear(user_id)

    pending = await deps.pending_repo.get(user_id)
    pending_draft = pending[0] if pending else None

    now = now_in(user.timezone)
    upcoming_events = await deps.event_repo.list_in_range(
        user_id,
        now,
        now + timedelta(days=7),
    )
    recent_events_str = json.dumps(
        [
            {"id": str(e.id), "title": e.title, "start_at": e.start_at.isoformat()}
            for e in upcoming_events
        ],
        ensure_ascii=False,
    )

    history = await deps.conversation_repo.last(user_id, limit=6)
    await deps.conversation_repo.append(user_id, "user", text)

    result = await deps.nlu.extract(
        text,
        now=now,
        timezone=user.timezone,
        recent_events=recent_events_str,
        pending_draft=pending_draft,
        history=history,
    )

    await _dispatch_result(msg, deps, result, pending_draft, user_tz=user.timezone)


async def _dispatch_result(
    msg: Message,
    deps: Deps,
    result: NLUResult,
    pending_draft: EventDraft | None,
    user_tz: str,
) -> None:
    assert msg.from_user is not None
    user_id = msg.from_user.id

    if result.intent in ("create_event", "clarify"):
        await _handle_create_or_clarify(msg, deps, result, pending_draft, user_tz)
        return

    if result.intent == "delete_event":
        await _handle_delete(msg, deps, result, user_tz)
        return

    # query_schedule and small_talk both rely on the model's free-form reply.
    reply = result.reply or "Готово."
    await deps.conversation_repo.append(user_id, "assistant", reply)
    await msg.answer(reply)


async def _handle_create_or_clarify(
    msg: Message,
    deps: Deps,
    result: NLUResult,
    pending_draft: EventDraft | None,
    user_tz: str,
) -> None:
    assert msg.from_user is not None
    user_id = msg.from_user.id

    new_draft = result.draft or EventDraft()
    draft = pending_draft.merge(new_draft) if pending_draft else new_draft

    # Normalize naive datetimes from the LLM to the user's timezone.
    if draft.start_at:
        draft.start_at = ensure_aware(draft.start_at, user_tz)
    if draft.end_at:
        draft.end_at = ensure_aware(draft.end_at, user_tz)

    # Check what's still missing.
    missing_question = _what_is_missing(draft)
    if result.needs_clarification or missing_question:
        question = result.clarification_question or missing_question
        assert question is not None
        await deps.pending_repo.upsert(user_id, draft, question)
        await deps.conversation_repo.append(user_id, "assistant", question)
        await msg.answer(question)
        return

    # Commit event.
    assert draft.title and draft.start_at
    event = await deps.event_repo.create(user_id, draft)
    reminders = await deps.reminders.schedule_for_event(event, draft.reminder_offsets_minutes)
    await deps.pending_repo.clear(user_id)

    card = format_event_card(event, user_tz)
    suffix = f"\n\n✓ Сохранил. Напоминания: {len(reminders)}" if reminders else "\n\n✓ Сохранил."
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{event.id}"),
            ]
        ],
    )
    await deps.conversation_repo.append(user_id, "assistant", f"Создано событие: {event.title}")
    await msg.answer(card + suffix, parse_mode="Markdown", reply_markup=keyboard)


async def _handle_delete(
    msg: Message,
    deps: Deps,
    result: NLUResult,
    user_tz: str,
) -> None:
    assert msg.from_user is not None
    user_id = msg.from_user.id
    hint = (result.target_event_hint or "").strip().lower()
    if not hint:
        await msg.answer("Какое событие удалить? Скажи название.")
        return

    upcoming = await deps.event_repo.list_upcoming(user_id, limit=20)
    matches = [e for e in upcoming if hint in e.title.lower()]
    if not matches:
        await msg.answer("Не нашёл такое событие.")
        return
    if len(matches) > 1:
        rows = [
            [
                InlineKeyboardButton(
                    text=f"🗑 {e.title} ({e.start_at.strftime('%d.%m %H:%M')})",
                    callback_data=f"del:{e.id}",
                )
            ]
            for e in matches[:5]
        ]
        await msg.answer(
            "Нашёл несколько подходящих, что удалить?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        return

    target = matches[0]
    await deps.event_repo.delete(target.id, user_id)
    await msg.answer(f"Удалил: *{target.title}*", parse_mode="Markdown")


def _what_is_missing(draft: EventDraft) -> str | None:
    if not draft.title:
        return "Как назвать это событие?"
    if not draft.start_at:
        return "Когда? Укажи дату и время."
    return None


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(msg: Message, deps: Deps) -> None:
    if not msg.text:
        return
    try:
        await process_user_text(msg, deps, msg.text)
    except Exception:
        logger.exception("Failed to process text message")
        await msg.answer("Что-то пошло не так. Попробуй ещё раз.")
