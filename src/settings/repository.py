from __future__ import annotations

import json
from typing import Protocol

from src.database.client import SQLiteDatabaseClient
from src.settings.models import LLMSettings, SystemPrompt

SYSTEM_PROMPT_KEY = "system_prompt"
LLM_SETTINGS_KEY = "llm_settings"


class SettingsRepository(Protocol):
    def initialize(self) -> None:
        """Create persistence structures and ensure defaults are present."""

    def get_system_prompt(self) -> SystemPrompt:
        """Return the current persisted system prompt."""

    def save_system_prompt(self, prompt: str | SystemPrompt) -> SystemPrompt:
        """Persist a new system prompt value."""

    def get_llm_settings(self) -> LLMSettings:
        """Return the current persisted LLM runtime settings."""

    def save_llm_settings(self, settings: LLMSettings) -> LLMSettings:
        """Persist runtime LLM settings."""


class SQLiteSettingsRepository:
    """SQLite-backed persistence for system prompt and LLM runtime settings."""

    def __init__(
        self,
        database_client: SQLiteDatabaseClient,
        default_system_prompt: str,
        default_llm_settings: LLMSettings,
    ) -> None:
        self._database_client = database_client
        self._default_system_prompt = SystemPrompt(prompt=default_system_prompt)
        self._default_llm_settings = default_llm_settings

    def initialize(self) -> None:
        with self._database_client.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    setting_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO app_settings(setting_key, payload_json) VALUES(?, ?)",
                (
                    SYSTEM_PROMPT_KEY,
                    json.dumps(
                        self._default_system_prompt.model_dump(mode="json"),
                        ensure_ascii=False,
                    ),
                ),
            )
            connection.execute(
                "INSERT OR IGNORE INTO app_settings(setting_key, payload_json) VALUES(?, ?)",
                (
                    LLM_SETTINGS_KEY,
                    json.dumps(
                        self._default_llm_settings.model_dump(mode="json"),
                        ensure_ascii=False,
                    ),
                ),
            )
            connection.commit()

    def get_system_prompt(self) -> SystemPrompt:
        self.initialize()
        row = self._fetch_payload(SYSTEM_PROMPT_KEY)
        return SystemPrompt.model_validate(json.loads(row))

    def save_system_prompt(self, prompt: str | SystemPrompt) -> SystemPrompt:
        self.initialize()
        system_prompt = (
            prompt if isinstance(prompt, SystemPrompt) else SystemPrompt(prompt=prompt)
        )
        self._save_payload(
            SYSTEM_PROMPT_KEY,
            json.dumps(system_prompt.model_dump(mode="json"), ensure_ascii=False),
        )
        return system_prompt

    def get_llm_settings(self) -> LLMSettings:
        self.initialize()
        row = self._fetch_payload(LLM_SETTINGS_KEY)
        return LLMSettings.model_validate(json.loads(row))

    def save_llm_settings(self, settings: LLMSettings) -> LLMSettings:
        self.initialize()
        self._save_payload(
            LLM_SETTINGS_KEY,
            json.dumps(settings.model_dump(mode="json"), ensure_ascii=False),
        )
        return settings

    def ping(self) -> bool:
        self.initialize()
        with self._database_client.connect() as connection:
            row = connection.execute("SELECT 1 AS is_ready").fetchone()

        return bool(row and row["is_ready"] == 1)

    def _fetch_payload(self, setting_key: str) -> str:
        with self._database_client.connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM app_settings WHERE setting_key = ?",
                (setting_key,),
            ).fetchone()

        if row is None:
            raise KeyError(f"Missing setting '{setting_key}'.")

        return str(row["payload_json"])

    def _save_payload(self, setting_key: str, payload_json: str) -> None:
        with self._database_client.connect() as connection:
            connection.execute(
                """
                INSERT INTO app_settings(setting_key, payload_json)
                VALUES(?, ?)
                ON CONFLICT(setting_key)
                DO UPDATE SET payload_json = excluded.payload_json
                """,
                (setting_key, payload_json),
            )
            connection.commit()
