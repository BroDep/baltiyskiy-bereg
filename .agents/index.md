# Baltiyskiy Bereg — Service Desk Chatbot

## Project Overview

LLM chatbot for the "Baltiyskiy Bereg" service desk. Connects to MSSQL database containing **104,395 tickets** and **1,060 KB articles**. Uses YandexGPT for LLM capabilities.

**Stack:** Python 3.11+, MSSQL, Docker, YandexGPT (OpenAI-compatible API)

---

## Repository Structure

```
baltiyskiy-bereg/
├── .agents/              # Agent documentation (this folder)
│   ├── index.md          # This file - project overview
│   ├── AGENTS.md         # Coding guidelines for AI agents
│   ├── REQUIREMENTS.md   # Project requirements (TODO)
│   └── ROADMAP.md       # Development roadmap (TODO)
├── src/                  # Application source code
├── tests/                # Test files
├── data/                 # Database backup files
├── .github/              # GitHub Actions workflows
├── docker-compose.yml    # Docker services definition
├── pyproject.toml        # Python dependencies
└── README.md            # Project documentation
```

---

## Database

**Server:** `111.88.159.116:1433`  
**Database:** `service_desk_tdbb`  
**User:** `SA`

### Key Tables

| Table | Description | Row Count |
|-------|-------------|-----------|
| `Task` | Service desk tickets with Q&A | 104,395 |
| `KBDocument` | Knowledge base articles | 1,060 |
| `TaskFieldValues` | Custom field values | — |
| `TaskExpenses` | Work time records | — |
| `Service`, `Status`, `Priority` | Lookup tables | — |

### Ticket Structure
- **Name** — short title
- **Description** — detailed description
- **Comment** — HTML Q&A conversation between user and support
- **StatusId, ServiceId, TypeId** — categories

---

## CI/CD

### GitHub Actions

| Workflow | Trigger | Description |
|----------|---------|-------------|
| **CI** | Push to `main` or `dev` | Linting, syntax check |
| **CD** | Push to `dev` | Deploy to VPS |

### Deploy Pipeline

1. CI checks code quality
2. CD pulls latest code to `111.88.159.116`
3. If `Dockerfile` exists → rebuilds containers
4. Starts services with `docker compose`
5. Health check validates MSSQL connection

### Server Access

```
Host: 111.88.159.116
User: theimage01
SSH Key: ~/.ssh/baltiyskiy_bereg_new
```

**SSH Connection:**
```bash
ssh -i ~/.ssh/baltiyskiy_bereg_new theimage01@111.88.159.116
```

**Useful Commands:**
```bash
# Check containers
docker ps

# View logs
docker compose logs --tail=50

# Restart services
docker compose down && docker compose up -d

# Connect to MSSQL
docker exec -it mssql-baltbereg /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U SA -P '$MSSQL_SA_PASSWORD' \
  -Q 'SELECT COUNT(*) FROM service_desk_tdbb.dbo.Task'
```

---

## Contributing

Contributions are welcome! Please contact **www.sooskolkos@gmail.com** for collaboration.

### Before Adding New Module

When adding a new module or service:
1. Read `.agents/AGENTS.md` for coding guidelines
2. Update this `index.md` in the appropriate section
3. Document new environment variables in `.env.example`
4. Add new tables/fields to Database section if applicable

---

## Links

- **GitHub:** https://github.com/BroDep/baltiyskiy-bereg
- **VPS:** 111.88.159.116
- **API Key Contact:** www.sooskolkos@gmail.com
