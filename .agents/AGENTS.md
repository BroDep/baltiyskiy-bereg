# AGENTS.md — Baltiyskiy Bereg Service Desk Chatbot v2

## Project Overview

LLM chatbot for the Baltiyskiy Bereg service desk. Connects to MSSQL database containing ~104,000 tickets and ~1,000 KB articles. Uses YandexGPT for LLM capabilities.

**Stack:** Python 3.11+, MSSQL, Docker, YandexGPT (OpenAI-compatible API)

---

## Quick Start

### VPS Access
- Host: 111.88.159.116
- User: theimage01
- SSH Key: ~/.ssh/baltiyskiy_bereg_new

### Connect
```bash
ssh -i ~/.ssh/baltiyskiy_bereg_new theimage01@111.88.159.116
```

---

## Build / Run / Test

### Setup
```bash
uv sync
cp .env.example .env
```

### Running
```bash
uv run python src/main.py
```

### Linting
```bash
uv run ruff check .
uv run ruff format .
```

### Testing
```bash
uv run pytest
```

---

## Git Flow

1. Create branch from `v2-master`
2. Make changes and commit
3. Push and create PR

---

## Code Style

- PEP 8 baseline
- Max line length: 100
- Type hints required
- Import order: stdlib → third-party → local

---

## Database

| Table | Purpose |
|-------|---------|
| Task | ~104k tickets |
| KBDocument | ~1k KB articles |
| TaskExpenses | Work records |
| TaskFieldValues | Custom fields |

---

## Task Workflow (/up:* commands)

This project uses a structured task workflow inspired by ultrapack.

### Quick Start
```
/up:make <description>
```

Example: `/up:make add user authentication`

### Commands

| Command | Description |
|---------|-------------|
| `/up:make` | Orchestrate full workflow |
| `/up:design` | Discuss requirements, discover invariants |
| `/up:plan` | Create implementation plan |
| `/up:execute` | Implement in phases |
| `/up:verify` | Manual smoke testing |
| `/up:review` | Independent code review |
| `/up:debug` | Root cause investigation |

### Task Files

All tasks tracked in `docs/tasks/<slug>.md`:
- This file is the source of truth
- Any new session can continue by reading it
- File evolves: Design → Plan → Execute → Verify → Review → Done

### Template

See `docs/tasks/TEMPLATE.md` for task file structure.

### Principles

- Don't delete things (copy and rename instead)
- Work in git branch
- Clear context between stages
- Fix only critical/important issues
