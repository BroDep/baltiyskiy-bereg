from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import pymssql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import ChatRequest, ChatResponse, HealthResponse, Source
from src.rag.pipeline import RAGPipeline

load_dotenv()

_pipeline: RAGPipeline | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    _pipeline = RAGPipeline()
    yield
    _pipeline = None


app = FastAPI(
    title="Baltiyskiy Bereg Service Desk Bot",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _db_connected() -> bool:
    try:
        conn = pymssql.connect(
            server=os.getenv("MSSQL_HOST", "localhost"),
            port=int(os.getenv("MSSQL_PORT", "1433")),
            user=os.getenv("MSSQL_USER", "SA"),
            password=os.environ["MSSQL_SA_PASSWORD"],
            database=os.getenv("MSSQL_DATABASE", "service_desk_tdbb"),
            login_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_ok = _db_connected()
    vs_ok = _pipeline.vector_store_connected if _pipeline else False
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        vector_store_connected=vs_ok,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialised")

    session_id = req.session_id or str(uuid.uuid4())
    result = await _pipeline.arun(req.message)

    sources = [
        Source(
            title=chunk.title,
            excerpt=chunk.text[:200],
            score=round(chunk.score, 3),
            ticket_id=chunk.ticket_id,
            kb_doc_id=chunk.kb_doc_id,
        )
        for chunk in result.chunks
    ]

    return ChatResponse(
        answer=result.answer,
        confidence_score=round(result.confidence_score, 1),
        confidence_label=result.confidence_label,
        escalate=result.escalate,
        sources=sources,
        session_id=session_id,
    )
