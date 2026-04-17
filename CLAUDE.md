# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM chatbot for the "Baltiyskiy Bereg" (Baltic Shore) IT service desk — AI Business SPB Hackathon 2026. The bot assists employees with IT tickets by searching ~104,000 historical tickets and ~1,000 KB articles stored in a MSSQL database (`service_desk_tdbb`).

## Architecture

Three-stage RAG pipeline:
1. **Hybrid search** — BM25 + dense vector retrieval (top-20 candidates)
2. **Re-ranking** — cross-encoder `DiTy/cross-encoder-russian-msmarco` narrows to top-3 chunks
3. **Generation + verification** — YandexGPT generates the answer, then a second LLM call scores confidence (0–10); score < 7 triggers escalation to a human agent

```
User → FastAPI → RAG pipeline (Hybrid search → Re-ranking → Generation+Verification) → YandexGPT
                     ↕
              Qdrant (vectors + BM25) ← MSSQL (read-only)
```

**Tech stack:**

| Component | Choice |
|---|---|
| LLM | YandexGPT (OpenAI-compatible API) |
| Embeddings | Yandex Embeddings API or `intfloat/multilingual-e5-large` (local) |
| Vector DB | Qdrant (Docker) — supports built-in BM25 |
| Re-ranker | `DiTy/cross-encoder-russian-msmarco` (HuggingFace) |
| Backend | FastAPI |
| Frontend | Streamlit |

## Setup

```bash
cp .env.example .env
# Fill in MSSQL_SA_PASSWORD, YANDEX_GPT_API_KEY, YANDEX_GPT_FOLDER_ID in .env
```

Install Python dependencies (requires Python ≥ 3.11, uses `uv`):
```bash
uv sync
```

## Database

Download the MSSQL backup and place it at `data/cleaned.bak`, then start the container:
```bash
docker compose up -d
# Wait ~1-2 minutes for restore-db.sh to restore the DB automatically
```

Verify the restore:
```bash
docker exec -it mssql-baltbereg /opt/mssql-tools/bin/sqlcmd \
    -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
    -Q "SELECT TOP 1 Name FROM service_desk_tdbb.dbo.Task"
```

MSSQL is exposed on `localhost:1433`. Connect with `pymssql` using database `service_desk_tdbb`.

### Key Tables

| Table | Contents |
|---|---|
| `Task` | ~104k tickets. `Name`, `Description`, `Comment` (HTML Q&A thread — primary RAG source), `StatusId`, `ServiceId`, `TypeId` |
| `KBDocument` | ~1,000 KB articles: `Name`, `Description` (HTML), `IsPublished`, `Rating` |
| `TaskFieldValues` | Custom field values per ticket |
| `TaskExpenses` | Work log entries: `Comments`, `Minutes`, `Date` |
| `Service`, `TaskType`, `Status`, `Priority` | Lookup tables |

`Task.Comment` is the primary RAG source — it contains HTML Q&A dialogs between employees and support staff. Parse with BeautifulSoup, extract Q&A pairs, store as separate documents with metadata (`ticket_id`, `service_id`, `task_type_id`, `priority_id`, `status_id`, `created_date`). Expected volume: ~300k Q&A pairs from tickets + ~4k chunks from KB articles.

`KBDocument.Description` is HTML — strip to clean text preserving heading structure, then chunk at 300–500 tokens with 20% overlap.

## Data Pipeline Scripts

- `extract_dialogues.py` — parse `Task.Comment` HTML into Q&A pairs → JSONL
- `process_kb.py` — extract clean text from `KBDocument` → JSONL
- `build_index.py` — embed all documents (batch), build BM25 index, store in Qdrant

Hybrid search scoring: `Score = α * BM25 + (1-α) * cosine_similarity`, recommended α = 0.3–0.5.

## LLM Integration

YandexGPT via OpenAI-compatible API. Configure in `.env`:
```
YANDEX_GPT_API_KEY=...
YANDEX_GPT_FOLDER_ID=...
YANDEX_GPT_MODEL=yandexgpt/latest
YANDEX_GPT_BASE_URL=https://llm.api.cloud.yandex.net/foundationModels/v1
```

Answer verification uses a second LLM call that scores whether the generated answer is grounded in the retrieved context (0–10). If score < 7, respond with escalation message instead of the answer.

## Running the Application

```bash
# 1. FastAPI backend
uvicorn src.api.main:app --reload --port 8000

# 2. Flask frontend server (separate terminal)
cd frontend && flask --app flask_app run --port 5000

# 3. React dev server (separate terminal, for development)
cd frontend/react-app && npm install && npm start
```

For production, build React first: `cd frontend/react-app && npm run build`, then Flask serves `react-app/build/` statically.

Frontend: `http://localhost:3000` (dev) or `http://localhost:5000` (prod via Flask). Flask proxies `/api/*` to FastAPI at `API_BASE_URL`.

## API Endpoints

- `POST /chat` — accepts user message, returns answer + source references
- `POST /classify` — predicts `ServiceId`, `TaskTypeId`, `PriorityId` from free-text description (zero-shot via YandexGPT or CatBoost on embeddings)
- `GET /health` — system status

## Solution Requirements

- Response time ≤ 30 seconds (expected ~12–15s: search 2–3s, re-rank 1–2s, generation 3–5s, verification 1–2s)
- ≤50% of queries should escalate to a human agent (lower is better)
- Must be deployable on-premise (not just SaaS)
- Target integrations: Telegram, Max, Bitrix
