from __future__ import annotations

from importlib import import_module
from pathlib import Path

from fastapi.testclient import TestClient


def test_load_config_reads_defaults_and_env_overrides(tmp_path: Path) -> None:
    config_module = import_module("src.config")
    load_config = getattr(config_module, "load_config")

    config = load_config(
        {
            "SETTINGS_DATABASE_PATH": str(tmp_path / "runtime-settings.sqlite3"),
            "DEFAULT_SYSTEM_PROMPT": "Новый системный промпт",
            "YANDEX_GPT_MODEL": "yandexgpt-lite/latest",
            "LLM_TEMPERATURE": "0.35",
            "LLM_MAX_TOKENS": "256",
            "LLM_TIMEOUT_SECONDS": "12.5",
            "MSSQL_HOST": "mssql.internal",
            "TELEGRAM_BOT_TOKEN": "test-telegram-token",
            "BACKEND_API_BASE_URL": "http://api.internal:8000",
            "API_TIMEOUT_SECONDS": "9.5",
        }
    )

    assert config.app_name == "baltiyskiy-bereg-api"
    assert config.settings_database_path == tmp_path / "runtime-settings.sqlite3"
    assert config.default_system_prompt == "Новый системный промпт"
    assert config.default_llm_settings.model_name == "yandexgpt-lite/latest"
    assert config.default_llm_settings.temperature == 0.35
    assert config.default_llm_settings.max_tokens == 256
    assert config.default_llm_settings.timeout_seconds == 12.5
    assert config.mssql.host == "mssql.internal"
    assert config.mssql.read_only is True
    assert config.telegram.bot_token == "test-telegram-token"
    assert config.telegram.backend_api_base_url == "http://api.internal:8000"
    assert config.telegram.api_timeout_seconds == 9.5


def test_sqlite_repository_returns_seeded_system_prompt(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)

    prompt = repository.get_system_prompt()

    assert prompt.prompt == "Ты внутренний ассистент сервис-деска Балтийский Берег."


def test_sqlite_repository_persists_updated_system_prompt(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)

    saved = repository.save_system_prompt("Обновлённый системный промпт")
    reloaded = _build_repository(tmp_path)

    assert saved.prompt == "Обновлённый системный промпт"
    assert reloaded.get_system_prompt().prompt == "Обновлённый системный промпт"


def test_sqlite_repository_returns_seeded_llm_settings(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)

    settings = repository.get_llm_settings()

    assert settings.model_name == "yandexgpt/latest"
    assert settings.temperature == 0.2
    assert settings.max_tokens == 512
    assert settings.timeout_seconds == 30.0


def test_sqlite_repository_persists_updated_llm_settings(tmp_path: Path) -> None:
    repository = _build_repository(tmp_path)
    settings_models = import_module("src.settings.models")
    llm_settings_class = getattr(settings_models, "LLMSettings")

    saved = repository.save_llm_settings(
        llm_settings_class(
            model_name="yandexgpt-pro/latest",
            temperature=0.65,
            max_tokens=1024,
            timeout_seconds=45.0,
        )
    )
    reloaded = _build_repository(tmp_path)

    assert saved.model_name == "yandexgpt-pro/latest"
    assert saved.temperature == 0.65
    assert reloaded.get_llm_settings().model_name == "yandexgpt-pro/latest"
    assert reloaded.get_llm_settings().timeout_seconds == 45.0


def test_app_factory_bootstraps_health_route_and_settings_repository(
    tmp_path: Path,
) -> None:
    config_module = import_module("src.config")
    main_module = import_module("src.main")
    load_config = getattr(config_module, "load_config")
    create_app = getattr(main_module, "create_app")

    config = load_config({"SETTINGS_DATABASE_PATH": str(tmp_path / "app.sqlite3")})
    app = create_app(config=config)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert app.state.config.settings_database_path == tmp_path / "app.sqlite3"
    assert app.state.settings_repository.get_system_prompt().prompt


def test_api_models_export_runtime_contract_types() -> None:
    models_module = import_module("src.api.models")

    required_symbols = [
        "ChatErrorResponse",
        "ChatSuccessResponse",
        "GenerateErrorResponse",
        "GenerateRequest",
        "GenerateResponseMetadata",
        "GenerateSuccessResponse",
        "LiveResponse",
        "ReadyResponse",
    ]

    for symbol in required_symbols:
        assert getattr(models_module, symbol)


def _build_repository(tmp_path: Path):
    database_module = import_module("src.database.client")
    settings_models = import_module("src.settings.models")
    repository_module = import_module("src.settings.repository")

    database_client_class = getattr(database_module, "SQLiteDatabaseClient")
    llm_settings_class = getattr(settings_models, "LLMSettings")
    repository_class = getattr(repository_module, "SQLiteSettingsRepository")

    repository = repository_class(
        database_client=database_client_class(tmp_path / "settings.sqlite3"),
        default_system_prompt="Ты внутренний ассистент сервис-деска Балтийский Берег.",
        default_llm_settings=llm_settings_class(
            model_name="yandexgpt/latest",
            temperature=0.2,
            max_tokens=512,
            timeout_seconds=30.0,
        ),
    )
    repository.initialize()
    return repository
