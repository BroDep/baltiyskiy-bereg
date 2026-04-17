# AGENTS.md — Baltiyskiy Bereg Service Desk Chatbot

## Project Overview

LLM chatbot for the "Baltiyskiy Bereg" service desk. Connects to MSSQL database containing ~104,000 tickets and ~1,000 KB articles. Uses YandexGPT for LLM capabilities.

**Stack:** Python 3.11+, MSSQL, Docker, YandexGPT (OpenAI-compatible API)

---

## Build / Run / Test Commands

### Setup
```bash
# Install dependencies (uses uv)
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Running
```bash
# Run the application
uv run python src/main.py

# Or with activated environment
source .venv/bin/activate
python src/main.py
```

### Database
```bash
# Start MSSQL container
docker compose up -d

# Check database connection
docker exec -it mssql-baltbereg /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
    -Q "SELECT TOP 1 Name FROM service_desk_tdbb.dbo.Task"
```

### Linting & Type Checking
```bash
# Install dev dependencies for linting
uv add --dev ruff mypy

# Run ruff linter
uv run ruff check .

# Run ruff with auto-fix
uv run ruff check --fix .

# Format code with ruff
uv run ruff format .

# Type checking
uv run mypy .
```

### Testing
```bash
# Install pytest
uv add --dev pytest pytest-cov

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_database.py

# Run tests matching pattern
uv run pytest -k "test_search"

# Run with verbose output
uv run pytest -v

# Run and stop on first failure
uv run pytest -x
```

### Code Quality
```bash
# Run all quality checks
uv run ruff check . && uv run mypy . && uv run pytest

# Pre-commit hooks (when configured)
uv run pre-commit run --all-files
```

---

## Contributing

Contributions are welcome! Please contact **www.sooskolkos@gmail.com** for collaboration details.

---

## Documentation Sync Rule ⚠️

**IMPORTANT:** When adding new modules, services, or components, you MUST update `.agents/index.md`:

| Change Type | Update Section in index.md |
|-------------|---------------------------|
| New source module | Repository Structure |
| New database table/field | Key Tables |
| New environment variable | Environment Variables (in .env.example) |
| New service/endpoint | Document in appropriate section |

This ensures all AI agents have up-to-date context about the project.

---

## Code Style Guidelines

### General Principles

- **PEP 8** is the baseline — follow it strictly
- Write code for humans first, computers second
- Keep functions small and focused (ideally < 40 lines)
- Maximum line length: **100 characters**
- Use type hints for all function signatures

### Security

- **NEVER commit API keys, passwords, tokens, or secrets to git**
- All secrets must be in `.env` and `.env` must be in `.gitignore`
- If you accidentally commit secrets, treat it as a security incident
- When adding new secrets, document them only in `.env.example` (without real values)

### Imports

**Order (per file):**
1. Standard library
2. Third-party packages
3. Local application imports
4. Separate each group with a blank line

```python
# Standard library
import os
from datetime import datetime
from typing import Optional

# Third-party
import pymssql
import requests
from dotenv import load_dotenv

# Local
from src.config import Settings
from src.database import DatabaseClient
```

**Rules:**
- Never use wildcard imports (`from module import *`)
- Avoid relative imports when possible
- Sort imports alphabetically within each group

### Type Hints

**Always use type hints for:**
- Function parameters
- Return types
- Class attributes
- Variable declarations where type isn't obvious

```python
# Good
def search_tickets(query: str, limit: int = 10) -> list[dict]:
    ...

def get_connection() -> pymssql.Connection:
    ...

# Bad
def search_tickets(query, limit=10):
    ...
```

**Use these patterns:**
- `Optional[X]` or `X | None` for nullable types
- `list[X]`, `dict[K, V]`, `set[X]` for generics
- `Any` only as last resort

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | snake_case | `database_client.py` |
| Classes | PascalCase | `TicketSearch` |
| Functions | snake_case | `search_tickets()` |
| Variables | snake_case | `ticket_list` |
| Constants | UPPER_SNAKE | `MAX_RESULTS` |
| Private members | _leading_underscore | `_cache` |

**Additional rules:**
- Use descriptive names (min 3 chars, no single letters except loop counters)
- Avoid abbreviations unless universally known (db, id, url, api)
- Boolean variables should be prefixed: `is_`, `has_`, `can_`, `should_`

### Error Handling

**Patterns:**
```python
# Use specific exceptions
def connect_db() -> Connection:
    try:
        return pymssql.connect(...)
    except pymssql.OperationalError as e:
        raise DatabaseConnectionError(f"Failed to connect: {e}") from e

# Handle gracefully with logging
import logging
logger = logging.getLogger(__name__)

def get_ticket(ticket_id: int) -> Optional[Ticket]:
    try:
        return Ticket.from_db(ticket_id)
    except NotFoundError:
        logger.warning(f"Ticket {ticket_id} not found")
        return None
```

**Rules:**
- Never use bare `except:`
- Always catch specific exceptions
- Log errors before raising
- Include context in error messages
- Use `from e` to preserve stack trace

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed info for debugging")
logger.info("Normal operation info")
logger.warning("Something unexpected but handled")
logger.error("Something failed")
logger.critical("System unusable")
```

### Documentation

**For modules:**
```python
"""Database client for MSSQL service desk connection.

Handles connection pooling, query execution, and result formatting
for the Baltiyskiy Bereg ticket system.
"""
```

**For functions:**
```python
def search_kb_articles(query: str, limit: int = 5) -> list[dict]:
    """Search knowledge base articles by query.
    
    Args:
        query: Search terms to match against article content
        limit: Maximum number of results to return (default 5)
    
    Returns:
        List of matching articles with name, description, and relevance score
    
    Raises:
        DatabaseError: If query execution fails
    """
```

### Project Structure

```
baltiyskiy-bereg/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Environment/config handling
│   ├── database/
│   │   ├── __init__.py
│   │   ├── client.py        # DB connection
│   │   └── queries.py       # SQL queries
│   ├── services/
│   │   ├── __init__.py
│   │   ├── search.py        # Search logic
│   │   └── llm.py           # LLM integration
│   └── models/
│       ├── __init__.py
│       ├── ticket.py
│       └── kb_article.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # pytest fixtures
│   ├── test_database.py
│   └── test_search.py
├── data/                    # DB backup files
├── .env.example
├── pyproject.toml
├── docker-compose.yml
└── AGENTS.md
```

### Database Access

- Use parameterized queries only (no string concatenation)
- Close connections explicitly or use context managers
- Limit result sets (add `TOP` / `LIMIT` clauses)
- Use read-only connections where possible

```python
# Good
cursor.execute(
    "SELECT TOP %d Name, Description FROM Task WHERE Name LIKE %s",
    (limit, f"%{query}%")
)

# Bad
cursor.execute(f"SELECT TOP {limit} Name FROM Task WHERE Name LIKE '%{query}%'")
```

### Async Code (if needed)

- Use `asyncpg` or `aiomysql` for async database access
- Use `httpx` for async HTTP requests
- Follow the same style guidelines as sync code

---

## Key Tables Reference

| Table | Purpose |
|-------|---------|
| `Task` | ~104,000 tickets. Key columns: Name, Description, Comment (HTML Q&A), StatusId, ServiceId, TypeId |
| `TaskFieldValues` | Custom field values |
| `TaskExpenses` | Work records: Comments, Minutes, Date |
| `KBDocument` | ~1,000 KB articles: Name, Description (HTML), IsPublished, Rating |
| `Service`, `TaskType`, `Status`, `Priority` | Lookup tables |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY` | Team API key for competition platform |
| `MSSQL_SA_PASSWORD` | Database password |
| `MSSQL_HOST` | Database host (default: localhost) |
| `MSSQL_PORT` | Database port (default: 1433) |
| `MSSQL_DATABASE` | Database name (service_desk_tdbb) |
| `MSSQL_USER` | Database user (SA) |
| `YANDEX_GPT_API_KEY` | YandexGPT API key |
| `YANDEX_GPT_FOLDER_ID` | Yandex Cloud folder ID |
| `YANDEX_GPT_MODEL` | Model name (default: yandexgpt/latest) |
| `YANDEX_GPT_BASE_URL` | API base URL (optional, for OpenAI compatibility) |
