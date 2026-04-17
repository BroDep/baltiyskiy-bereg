from __future__ import annotations

import os
from dataclasses import dataclass, field

from src.rag.llm import GenerationResult, generate

ESCALATION_ANSWER = (
    "К сожалению, я не нашёл точного решения в базе знаний. "
    "Передаю вопрос специалисту — он свяжется с вами в ближайшее время."
)

ESCALATION_THRESHOLD = float(os.getenv("ESCALATION_THRESHOLD", "7"))


@dataclass
class RetrievedChunk:
    text: str
    score: float
    title: str
    ticket_id: int | None = None
    kb_doc_id: int | None = None


@dataclass
class PipelineResult:
    answer: str
    confidence_score: float
    confidence_label: str
    escalate: bool
    chunks: list[RetrievedChunk] = field(default_factory=list)


def _label(score: float) -> str:
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


class RAGPipeline:
    """
    Hybrid RAG pipeline: BM25 + dense retrieval → cross-encoder re-ranking → LLM generation + verification.

    When the vector store is not yet initialised (no QDRANT_URL configured), the pipeline
    falls back to a direct LLM call without retrieval context.
    """

    def __init__(self) -> None:
        self._retriever_ready = False
        qdrant_url = os.getenv("QDRANT_URL")
        if qdrant_url:
            self._init_retriever(qdrant_url)

    def _init_retriever(self, url: str) -> None:
        try:
            from qdrant_client import QdrantClient  # noqa: PLC0415

            self._qdrant = QdrantClient(url=url)
            self._retriever_ready = True
        except Exception:
            self._retriever_ready = False

    # ------------------------------------------------------------------
    # Retrieval (stub — replace with real hybrid search once index built)
    # ------------------------------------------------------------------

    async def _retrieve(self, query: str) -> list[RetrievedChunk]:
        """Return top-3 re-ranked chunks. Returns empty list when index not ready."""
        if not self._retriever_ready:
            return []

        # TODO: implement hybrid BM25 + dense search via Qdrant,
        #       then re-rank with DiTy/cross-encoder-russian-msmarco.
        return []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def arun(self, query: str) -> PipelineResult:
        chunks = await self._retrieve(query)

        context = "\n\n---\n\n".join(
            f"[{c.title}]\n{c.text}" for c in chunks
        )

        result: GenerationResult = await generate(query, context)

        if result.confidence_score < ESCALATION_THRESHOLD:
            return PipelineResult(
                answer=ESCALATION_ANSWER,
                confidence_score=result.confidence_score,
                confidence_label=_label(result.confidence_score),
                escalate=True,
                chunks=chunks,
            )

        return PipelineResult(
            answer=result.answer,
            confidence_score=result.confidence_score,
            confidence_label=_label(result.confidence_score),
            escalate=False,
            chunks=chunks,
        )

    @property
    def vector_store_connected(self) -> bool:
        return self._retriever_ready
