from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
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

    rag_enabled: bool = True
    rag_ticket_max_chars: int = 6000
    rag_kb_chunk_size_chars: int = 1800
    rag_kb_chunk_overlap_chars: int = 250
    rag_retrieval_limit: int = 24
    rag_rerank_limit: int = 8
    rag_min_vector_score: float = 0.15
    rag_min_rerank_score: float = 0.45
    rag_min_retrieval_confidence: float = 0.45
    rag_min_final_confidence: float = 0.62
    rag_sync_on_startup: bool = True
    rag_sync_interval_seconds: int = 1800
    rag_sync_batch_size: int = 200
    rag_sync_state_path: str = "data/rag-sync-state.json"

    telegram_bot_enabled: bool = False
    telegram_bot_token: SecretStr | None = None
    frontend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    mssql_host: str = "localhost"
    mssql_port: int = 1433
    mssql_database: str = "service_desk_tdbb"
    mssql_user: str = "SA"
    mssql_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("MSSQL_PASSWORD", "MSSQL_SA_PASSWORD"),
    )

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "service_desk_knowledge"
    qdrant_api_key: SecretStr | None = None
    qdrant_timeout_seconds: float = 30.0

    yandex_gpt_api_key: SecretStr | None = None
    yandex_gpt_folder_id: str | None = None
    yandex_gpt_model: str = "yandexgpt/latest"
    yandex_embedding_doc_model: str = "text-search-doc/latest"
    yandex_embedding_query_model: str = "text-search-query/latest"
    yandex_gpt_timeout_seconds: float = 30.0
    yandex_gpt_temperature: float = 0.2
    yandex_gpt_max_tokens: int = 800
    yandex_gpt_system_prompt: str = (
        "Ты support-ассистент компании Балтийский Берег. "
        "Отвечай только на основе предоставленного контекста и не выдумывай факты."
    )

    @property
    def yandex_gpt_endpoint(self) -> str:
        return "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    @property
    def yandex_embedding_endpoint(self) -> str:
        return "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"

    @property
    def yandex_gpt_api_key_value(self) -> str:
        if self.yandex_gpt_api_key is None:
            raise ValueError("YANDEX_GPT_API_KEY is not configured")
        return self.yandex_gpt_api_key.get_secret_value()

    @property
    def mssql_password_value(self) -> str:
        if self.mssql_password is None:
            raise ValueError("MSSQL password is not configured")
        return self.mssql_password.get_secret_value()

    @property
    def qdrant_api_key_value(self) -> str | None:
        if self.qdrant_api_key is None:
            return None
        return self.qdrant_api_key.get_secret_value()

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

    @property
    def yandex_embedding_doc_model_uri(self) -> str:
        if not self.yandex_gpt_folder_id:
            raise ValueError("YANDEX_GPT_FOLDER_ID is not configured")
        return f"emb://{self.yandex_gpt_folder_id}/{self.yandex_embedding_doc_model}"

    @property
    def yandex_embedding_query_model_uri(self) -> str:
        if not self.yandex_gpt_folder_id:
            raise ValueError("YANDEX_GPT_FOLDER_ID is not configured")
        return f"emb://{self.yandex_gpt_folder_id}/{self.yandex_embedding_query_model}"

    @property
    def rag_sync_state_file(self) -> Path:
        return Path(self.rag_sync_state_path)

    def validate_yandex(self) -> None:
        _ = self.yandex_gpt_api_key_value
        _ = self.yandex_gpt_model_uri
        _ = self.yandex_embedding_doc_model_uri
        _ = self.yandex_embedding_query_model_uri

    def validate_mssql(self) -> None:
        _ = self.mssql_password_value

    def validate_telegram(self) -> None:
        if self.telegram_bot_enabled:
            _ = self.telegram_bot_token_value

    def validate_rag(self) -> None:
        if not self.rag_enabled:
            return
        self.validate_yandex()
        self.validate_mssql()

    @property
    def frontend_cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
