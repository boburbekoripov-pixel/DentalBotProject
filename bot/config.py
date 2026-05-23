from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(..., alias="BOT_TOKEN")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_nlu_model: str = Field("gpt-4o-mini", alias="OPENAI_NLU_MODEL")
    openai_chat_model: str = Field("gpt-4o-mini", alias="OPENAI_CHAT_MODEL")
    openai_whisper_model: str = Field("whisper-1", alias="OPENAI_WHISPER_MODEL")

    database_url: str = Field(..., alias="DATABASE_URL")

    default_timezone: str = Field("Asia/Tashkent", alias="DEFAULT_TIMEZONE")
    default_language: str = Field("ru", alias="DEFAULT_LANGUAGE")

    log_level: str = Field("INFO", alias="LOG_LEVEL")

    allowed_user_ids_raw: str = Field("", alias="ALLOWED_USER_IDS")

    @property
    def allowed_user_ids(self) -> set[int]:
        if not self.allowed_user_ids_raw.strip():
            return set()
        return {int(x.strip()) for x in self.allowed_user_ids_raw.split(",") if x.strip()}


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
