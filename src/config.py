from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Baltiyskiy Bereg Bot API"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = False
    log_level: str = "INFO"

    telegram_bot_enabled: bool = True
    telegram_bot_token: SecretStr | None = None

    yandex_gpt_api_key: SecretStr | None = None
    yandex_gpt_folder_id: str | None = None
    yandex_gpt_model: str = "yandexgpt/latest"
    yandex_gpt_timeout_seconds: float = 30.0
    yandex_gpt_temperature: float = 0.2
    yandex_gpt_max_tokens: int = 800
    yandex_gpt_system_prompt: str = (
        "Ты полезный IT-ассистент компании Балтийский Берег. "
        "Отвечай кратко, понятно и по делу."
    )

    @property
    def yandex_gpt_endpoint(self) -> str:
        return "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    @property
    def yandex_gpt_api_key_value(self) -> str:
        if self.yandex_gpt_api_key is None:
            raise ValueError("YANDEX_GPT_API_KEY is not configured")
        return self.yandex_gpt_api_key.get_secret_value()

    @property
    def telegram_bot_token_value(self) -> str:
        if self.telegram_bot_token is None:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured")
        return self.telegram_bot_token.get_secret_value()

    @property
    def yandex_gpt_model_uri(self) -> str:
        if not self.yandex_gpt_folder_id:
            raise ValueError("YANDEX_GPT_FOLDER_ID is not configured")
        return f"gpt://{self.yandex_gpt_folder_id}/{self.yandex_gpt_model}"

    def validate_yandex(self) -> None:
        _ = self.yandex_gpt_api_key_value
        _ = self.yandex_gpt_model_uri

    def validate_telegram(self) -> None:
        if self.telegram_bot_enabled:
            _ = self.telegram_bot_token_value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
