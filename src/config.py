from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

from src.settings.models import LLMSettings

DEFAULT_APP_NAME = "baltiyskiy-bereg-api"
DEFAULT_SETTINGS_DATABASE_PATH = Path("data/runtime/settings.sqlite3")
DEFAULT_SYSTEM_PROMPT = "Ты внутренний ассистент сервис-деска Балтийский Берег."
DEFAULT_MODEL_NAME = "yandexgpt/latest"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 512
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_YANDEX_BASE_URL = "https://llm.api.cloud.yandex.net"


@dataclass(frozen=True, slots=True)
class MSSQLConfig:
    host: str
    port: int
    database: str
    user: str
    password: str | None
    read_only: bool = True


@dataclass(frozen=True, slots=True)
class YandexGPTConfig:
    api_key: str | None
    folder_id: str | None
    model_name: str
    base_url: str
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_name: str
    settings_database_path: Path
    default_system_prompt: str
    default_llm_settings: LLMSettings
    mssql: MSSQLConfig
    yandex: YandexGPTConfig


def load_config(env: Mapping[str, str] | None = None) -> AppConfig:
    values = dict(_load_values(env))

    model_name = _get_str(values, "YANDEX_GPT_MODEL", DEFAULT_MODEL_NAME)
    timeout_seconds = _get_float(values, "LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    default_llm_settings = LLMSettings(
        model_name=model_name,
        temperature=_get_float(values, "LLM_TEMPERATURE", DEFAULT_TEMPERATURE),
        max_tokens=_get_int(values, "LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS),
        timeout_seconds=timeout_seconds,
    )

    return AppConfig(
        app_name=_get_str(values, "APP_NAME", DEFAULT_APP_NAME),
        settings_database_path=Path(
            _get_str(
                values, "SETTINGS_DATABASE_PATH", str(DEFAULT_SETTINGS_DATABASE_PATH)
            )
        ),
        default_system_prompt=_get_str(
            values, "DEFAULT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT
        ),
        default_llm_settings=default_llm_settings,
        mssql=MSSQLConfig(
            host=_get_str(values, "MSSQL_HOST", "localhost"),
            port=_get_int(values, "MSSQL_PORT", 1433),
            database=_get_str(values, "MSSQL_DATABASE", "service_desk_tdbb"),
            user=_get_str(values, "MSSQL_USER", "SA"),
            password=_get_optional_str(values, "MSSQL_SA_PASSWORD"),
        ),
        yandex=YandexGPTConfig(
            api_key=_get_optional_str(values, "YANDEX_GPT_API_KEY"),
            folder_id=_get_optional_str(values, "YANDEX_GPT_FOLDER_ID"),
            model_name=model_name,
            base_url=_get_str(values, "YANDEX_GPT_BASE_URL", DEFAULT_YANDEX_BASE_URL),
            timeout_seconds=timeout_seconds,
        ),
    )


def _load_values(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env

    load_dotenv()
    return os.environ


def _get_str(values: Mapping[str, str], key: str, default: str) -> str:
    raw_value = values.get(key)
    if raw_value is None:
        return default

    stripped_value = raw_value.strip()
    return stripped_value or default


def _get_optional_str(values: Mapping[str, str], key: str) -> str | None:
    raw_value = values.get(key)
    if raw_value is None:
        return None

    stripped_value = raw_value.strip()
    return stripped_value or None


def _get_int(values: Mapping[str, str], key: str, default: int) -> int:
    raw_value = values.get(key)
    if raw_value is None:
        return default

    return int(raw_value)


def _get_float(values: Mapping[str, str], key: str, default: float) -> float:
    raw_value = values.get(key)
    if raw_value is None:
        return default

    return float(raw_value)
