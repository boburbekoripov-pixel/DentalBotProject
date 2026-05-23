from __future__ import annotations

import contextlib
import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.handlers.deps import Deps

router = Router(name="callbacks")
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("del:"))
async def cb_delete(query: CallbackQuery, deps: Deps) -> None:
    if query.from_user is None or query.data is None:
        return
    try:
        event_id = UUID(query.data.split(":", 1)[1])
    except ValueError:
        await query.answer("Bad callback")
        return
    ok = await deps.event_repo.delete(event_id, query.from_user.id)
    if ok:
        await query.answer("Удалено ✓")
        if query.message is not None and hasattr(query.message, "edit_text"):
            with contextlib.suppress(Exception):
                await query.message.edit_text("✓ Событие удалено")
    else:
        await query.answer("Не нашёл событие")
