from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.handlers.deps import Deps
from bot.handlers.text import process_user_text

router = Router(name="voice")
logger = logging.getLogger(__name__)


@router.message(F.voice)
async def handle_voice(msg: Message, deps: Deps) -> None:
    if msg.from_user is None or msg.voice is None or msg.bot is None:
        return
    try:
        file = await msg.bot.get_file(msg.voice.file_id)
        if file.file_path is None:
            await msg.answer("Не удалось скачать голосовое сообщение.")
            return
        buf = await msg.bot.download_file(file.file_path)
        if buf is None:
            await msg.answer("Пустое аудио.")
            return
        text = await deps.whisper.transcribe(buf.read())
        if not text.strip():
            await msg.answer("Не разобрал голосовое, попробуй ещё раз.")
            return
        await msg.answer(f"📝 _{text}_", parse_mode="Markdown")
        await process_user_text(msg, deps, text)
    except Exception:
        logger.exception("Failed to process voice message")
        await msg.answer("Не получилось обработать голосовое.")
