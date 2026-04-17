from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteDatabaseClient:
    """SQLite connection factory for local runtime settings storage."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @property
    def database_path(self) -> Path:
        return self._database_path

    def connect(self) -> sqlite3.Connection:
        if self._database_path != Path(":memory:"):
            self._database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection
