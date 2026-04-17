from __future__ import annotations

import os
import random
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from datetime import date, datetime, time
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.api.models import (
    ChatRequest,
    ChatResponse,
    DailyPoint,
    HealthResponse,
    HourlyPoint,
    Source,
    StatsResponse,
    TicketItem,
    TicketsResponse,
)
from src.db import crud
from src.db.database import get_db, init_db

load_dotenv()

USE_STUBS = os.getenv("USE_STUBS", "false").lower() == "true"

_pipeline = None

# ── Stub responses ────────────────────────────────────────────────────────────

_STUB_RESPONSES = [
    {
        "keywords": ["vpn", "удаленн", "подключ", "remote"],
        "answer": (
            "Для подключения VPN выполните следующие шаги:\n\n"
            "1. Установите клиент **UniVPN** с корпоративного портала `portal.company.ru`\n"
            "2. Введите адрес сервера: `vpn.company.ru`\n"
            "3. Авторизуйтесь с доменными учётными данными\n\n"
            "Если соединение не устанавливается — проверьте настройки брандмауэра."
        ),
        "confidence_score": 8.5,
        "confidence_label": "high",
        "escalate": False,
        "sources": [
            Source(title="Тикет #23451: Настройка VPN-подключения", excerpt="Пользователю предложено установить UniVPN и подключиться к vpn.company.ru.", score=0.94, ticket_id=23451),
            Source(title="KB #87: Инструкция по настройке VPN", excerpt="Пошаговая инструкция по установке UniVPN. Поддерживаемые ОС: Windows 10/11, macOS 12+.", score=0.88, kb_doc_id=87),
        ],
    },
    {
        "keywords": ["пароль", "забыл", "сброс", "войти", "учётн", "учетн"],
        "answer": (
            "Для сброса пароля воспользуйтесь одним из способов:\n\n"
            "**Самостоятельно:** перейдите на `password.company.ru` и подтвердите личность через корп. почту\n\n"
            "**Через поддержку:** `+7 (812) 000-00-01` (доб. 101), назовите ФИО и табельный номер"
        ),
        "confidence_score": 9.0,
        "confidence_label": "high",
        "escalate": False,
        "sources": [
            Source(title="KB #12: Сброс пароля учётной записи", excerpt="Инструкция по самостоятельному сбросу пароля через портал или с помощью техподдержки.", score=0.97, kb_doc_id=12),
        ],
    },
    {
        "keywords": ["принтер", "печать", "сканер"],
        "answer": (
            "Для устранения проблем с принтером:\n\n"
            "1. Очистите очередь печати: `Устройства и принтеры → ПКМ → Просмотр очереди → Очистить`\n"
            "2. Переустановите драйвер с `drivers.company.ru`"
        ),
        "confidence_score": 7.2,
        "confidence_label": "medium",
        "escalate": False,
        "sources": [
            Source(title="Тикет #18934: Принтер HP LaserJet не печатает", excerpt="Решено переустановкой драйвера с корпоративного портала.", score=0.79, ticket_id=18934),
        ],
    },
    {
        "keywords": ["1с", "1c", "бухгалтер"],
        "answer": (
            "По вопросам 1С:\n\n"
            "- **Не запускается:** перезапустите службу через `services.msc → 1C:Enterprise`\n"
            "- **Ошибка соединения:** проверьте доступность `1c-srv.company.ru:1541`"
        ),
        "confidence_score": 6.5,
        "confidence_label": "medium",
        "escalate": False,
        "sources": [
            Source(title="KB #34: Часто задаваемые вопросы по 1С", excerpt="Решение типичных проблем: не запускается, ошибка авторизации, медленная работа.", score=0.83, kb_doc_id=34),
        ],
    },
]

_STUB_ESCALATION = {
    "answer": (
        "К сожалению, не удалось найти подходящее решение в базе знаний.\n\n"
        "Ваш запрос передан специалисту. Ожидайте ответа в течение **1 рабочего дня**.\n\n"
        "Для срочных вопросов: `+7 (812) 000-00-01`"
    ),
    "confidence_score": 3.0,
    "confidence_label": "low",
    "escalate": True,
    "sources": [],
}


def _stub_chat(message: str, session_id: str) -> ChatResponse:
    msg_lower = message.lower()
    stub = next(
        (s for s in _STUB_RESPONSES if any(kw in msg_lower for kw in s["keywords"])),
        random.choice(_STUB_RESPONSES),
    )
    return ChatResponse(
        answer=stub["answer"],
        confidence_score=stub["confidence_score"],
        confidence_label=stub["confidence_label"],
        escalate=stub["escalate"],
        sources=stub["sources"],
        session_id=session_id,
    )


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    try:
        init_db()
    except Exception as e:
        print(f"[warn] DB init failed: {e}")

    if not USE_STUBS:
        try:
            from src.rag.pipeline import RAGPipeline
            _pipeline = RAGPipeline()
        except Exception:
            pass
    yield
    _pipeline = None


app = FastAPI(title="Baltiyskiy Bereg Service Desk Bot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db_connected() -> bool:
    if USE_STUBS:
        return True
    try:
        import pymssql
        conn = pymssql.connect(
            server=os.getenv("MSSQL_HOST", "localhost"),
            port=int(os.getenv("MSSQL_PORT", "1433")),
            user=os.getenv("MSSQL_USER", "SA"),
            password=os.environ.get("MSSQL_SA_PASSWORD", ""),
            database=os.getenv("MSSQL_DATABASE", "service_desk_tdbb"),
            login_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    if USE_STUBS:
        return HealthResponse(status="ok", db_connected=True, vector_store_connected=True)
    db_ok = _db_connected()
    vs_ok = _pipeline.vector_store_connected if _pipeline else False
    return HealthResponse(status="ok" if db_ok else "degraded", db_connected=db_ok, vector_store_connected=vs_ok)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())

    if USE_STUBS:
        response = _stub_chat(req.message, session_id)
    elif _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialised")
    else:
        result = await _pipeline.arun(req.message)
        sources = [
            Source(title=c.title, excerpt=c.text[:200], score=round(c.score, 3), ticket_id=c.ticket_id, kb_doc_id=c.kb_doc_id)
            for c in result.chunks
        ]
        response = ChatResponse(
            answer=result.answer,
            confidence_score=round(result.confidence_score, 1),
            confidence_label=result.confidence_label,
            escalate=result.escalate,
            sources=sources,
            session_id=session_id,
        )

    try:
        crud.save_session(
            db,
            session_id=session_id,
            message=req.message,
            answer=response.answer,
            confidence_score=response.confidence_score,
            confidence_label=response.confidence_label,
            escalated=response.escalate,
        )
    except Exception:
        pass

    return response


# ── Analytics ─────────────────────────────────────────────────────────────────

def _parse_dates(date_from: date | None, date_to: date | None):
    df = datetime.combine(date_from, time.min) if date_from else None
    dt = datetime.combine(date_to, time.max) if date_to else None
    return df, dt


@app.get("/analytics/stats", response_model=StatsResponse)
def analytics_stats(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StatsResponse:
    df, dt = _parse_dates(date_from, date_to)
    return StatsResponse(**crud.get_stats(db, date_from=df, date_to=dt))


@app.get("/analytics/hourly", response_model=list[HourlyPoint])
def analytics_hourly(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[HourlyPoint]:
    df, dt = _parse_dates(date_from, date_to)
    return [HourlyPoint(**p) for p in crud.get_hourly(db, date_from=df, date_to=dt)]


@app.get("/analytics/daily", response_model=list[DailyPoint])
def analytics_daily(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DailyPoint]:
    df, dt = _parse_dates(date_from, date_to)
    return [DailyPoint(**p) for p in crud.get_daily_failures(db, date_from=df, date_to=dt)]


@app.get("/analytics/tickets", response_model=TicketsResponse)
def analytics_tickets(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    status: str = Query(default="all"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TicketsResponse:
    df, dt = _parse_dates(date_from, date_to)
    result = crud.get_tickets(db, page=page, limit=limit, search=search, status=status, date_from=df, date_to=dt)
    return TicketsResponse(
        total=result["total"],
        page=result["page"],
        pages=result["pages"],
        items=[TicketItem.model_validate(t) for t in result["items"]],
    )
