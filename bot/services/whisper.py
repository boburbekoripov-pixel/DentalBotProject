from __future__ import annotations

import io
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class WhisperService:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str:
        # Whisper API accepts ogg/opus directly; no transcoding required.
        buffer = io.BytesIO(audio_bytes)
        buffer.name = filename
        response = await self._client.audio.transcriptions.create(
            model=self._model,
            file=buffer,
            # Auto-detect language (works for RU/UZ/EN mix).
            prompt="Пользователь говорит на русском, узбекском или английском.",
        )
        text = response.text.strip()
        logger.info("Whisper transcribed %d bytes -> %d chars", len(audio_bytes), len(text))
        return text
