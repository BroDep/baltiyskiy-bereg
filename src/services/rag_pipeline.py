from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from src.config import Settings
from src.services.qdrant_store import QdrantStore
from src.services.rag_models import Citation, GroundedAnswer, RetrievedDocument
from src.services.rag_sync import RagSyncService
from src.services.text_normalization import trim_text
from src.services.yandex_gpt import YandexGPTClient, YandexGPTError

logger = logging.getLogger(__name__)

SOURCE_TOKEN_RE = re.compile(r"\[(S\d+)\]")


class RagPipeline:
    def __init__(
        self,
        settings: Settings,
        yandex_client: YandexGPTClient,
        qdrant_store: QdrantStore,
        rag_sync_service: RagSyncService,
    ) -> None:
        self._settings = settings
        self._yandex_client = yandex_client
        self._qdrant_store = qdrant_store
        self._rag_sync_service = rag_sync_service

    async def answer(self, question: str) -> GroundedAnswer:
        cleaned_question = question.strip()
        if not cleaned_question:
            return self._refuse(
                "Нужен текстовый вопрос, чтобы выполнить поиск по базе знаний и тикетам.",
                reason="empty_question",
            )

        sync_status = await self._rag_sync_service.get_status()
        if sync_status.indexed_documents == 0 and sync_status.running:
            return self._refuse(
                "База знаний сейчас синхронизируется с MSSQL. Повторите запрос чуть позже.",
                reason="sync_in_progress",
            )
        if sync_status.indexed_documents == 0:
            return self._refuse(
                "Индекс знаний пока пуст, поэтому я не могу ответить только по данным из базы.",
                reason="index_empty",
            )

        query_embedding = await self._yandex_client.embed_text(cleaned_question, kind="query")
        retrieved_documents = await asyncio.to_thread(
            self._qdrant_store.search,
            query_embedding,
            limit=self._settings.rag_retrieval_limit,
            score_threshold=self._settings.rag_min_vector_score,
        )
        if not retrieved_documents:
            return self._refuse(
                "Не нашёл в базе знаний и истории тикетов достаточно релевантного контекста для уверенного ответа.",
                reason="no_retrieval_hits",
            )

        reranked_documents = await self._rerank_documents(cleaned_question, retrieved_documents)
        selected_documents = self._select_documents_for_answer(reranked_documents)
        if not selected_documents:
            return self._refuse(
                "Нашёл похожие документы, но их недостаточно, чтобы ответить без риска ошибки.",
                reason="low_relevance_after_rerank",
            )

        retrieval_confidence = self._compute_retrieval_confidence(selected_documents)
        draft_answer = await self._generate_grounded_answer(cleaned_question, selected_documents)
        if not bool(draft_answer.get("answerable")):
            return self._refuse(
                "Не могу уверенно ответить только по найденным данным из базы. Лучше передать вопрос специалисту.",
                reason=str(draft_answer.get("reason") or "model_refusal"),
                retrieval_confidence=retrieval_confidence,
            )
        citations = self._build_citations(draft_answer, selected_documents)
        if not citations:
            return self._refuse(
                "Не удалось собрать ответ с проверяемыми цитатами из базы, поэтому лучше не буду угадывать.",
                reason="missing_citations",
                retrieval_confidence=retrieval_confidence,
            )

        verification = await self._verify_answer(
            question=cleaned_question,
            answer_text=draft_answer["answer_text"],
            cited_documents=[document for _, document in citations],
        )
        verification_confidence = float(verification.get("confidence") or 0.0)
        unsupported_claims = verification.get("unsupported_claims") or []
        grounded = bool(verification.get("grounded")) and not unsupported_claims
        model_confidence = float(draft_answer.get("confidence") or 0.0)
        final_confidence = min(model_confidence, retrieval_confidence, verification_confidence)

        if (
            not grounded
            or final_confidence < self._settings.rag_min_final_confidence
            or bool(draft_answer.get("needs_human"))
        ):
            return self._refuse(
                "Не могу уверенно ответить только по данным из базы. Лучше передать вопрос специалисту.",
                reason=str(verification.get("reason") or draft_answer.get("reason") or "low_confidence"),
                retrieval_confidence=retrieval_confidence,
                verification_confidence=verification_confidence,
            )

        answer_text = self._replace_source_tokens(
            draft_answer["answer_text"],
            {token: document.citation_label for token, document in citations},
        )
        return GroundedAnswer(
            reply=answer_text,
            citations=[
                Citation(
                    label=document.citation_label,
                    source_type=document.source_type,
                    source_id=document.source_id,
                    title=document.title,
                    excerpt=document.excerpt,
                )
                for _, document in citations
            ],
            confidence=final_confidence,
            grounded=True,
            needs_human=False,
            reason=str(verification.get("reason") or draft_answer.get("reason") or "grounded"),
            retrieval_confidence=retrieval_confidence,
            verification_confidence=verification_confidence,
        )

    async def _rerank_documents(
        self,
        question: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        rerank_candidates = documents[: self._settings.rag_rerank_limit]
        if not rerank_candidates:
            return []

        candidate_blocks = []
        token_to_document: dict[str, RetrievedDocument] = {}
        for index, document in enumerate(rerank_candidates, start=1):
            token = f"S{index}"
            token_to_document[token] = document
            candidate_blocks.append(
                "\n".join(
                    [
                        f"[{token}] type={document.source_type} title={document.title}",
                        f"vector_score={document.vector_score:.4f}",
                        trim_text(document.content, 1200),
                    ]
                )
            )

        rerank_prompt = (
            "Ты помогаешь internal RAG ранжировать найденные документы. "
            "Оцени, насколько каждый документ помогает ответить на вопрос. "
            "Верни только JSON формата "
            '{"scores": [{"id": "S1", "score": 0.0, "reason": "..."}]}. '
            "score должен быть числом от 0 до 1."
        )
        response = await self._yandex_client.generate_json(
            messages=[
                {
                    "role": "user",
                    "text": (
                        f"Вопрос пользователя:\n{question}\n\n"
                        "Документы-кандидаты:\n"
                        + "\n\n".join(candidate_blocks)
                    ),
                }
            ],
            system_prompt=rerank_prompt,
            temperature=0.0,
            max_tokens=700,
        )

        rerank_scores: dict[str, float] = {}
        for item in response.get("scores") or response.get("items") or []:
            if not isinstance(item, dict):
                continue
            token = str(item.get("id") or "")
            try:
                score = float(item.get("score") or 0.0)
            except (TypeError, ValueError):
                score = 0.0
            rerank_scores[token] = max(0.0, min(1.0, score))

        reranked: list[RetrievedDocument] = []
        for token, document in token_to_document.items():
            llm_score = rerank_scores.get(token, max(0.0, min(1.0, document.vector_score)))
            kb_bonus = 0.08 if document.source_type == "kb" else 0.0
            closed_ticket_bonus = 0.03 if document.metadata.get("is_closed") else 0.0
            final_score = min(1.0, llm_score * 0.7 + document.vector_score * 0.3 + kb_bonus + closed_ticket_bonus)
            document.rerank_score = llm_score
            document.final_score = final_score
            reranked.append(document)

        remaining_documents = documents[self._settings.rag_rerank_limit :]
        for document in remaining_documents:
            document.final_score = document.vector_score
            reranked.append(document)

        reranked.sort(key=lambda document: document.final_score or 0.0, reverse=True)
        return reranked

    def _select_documents_for_answer(
        self,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        selected: list[RetrievedDocument] = []
        seen_sources: set[tuple[str, int]] = set()
        for document in documents:
            score = document.final_score or 0.0
            if score < self._settings.rag_min_rerank_score:
                continue
            source_key = (document.source_type, document.source_id)
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            selected.append(document)
            if len(selected) >= 5:
                break
        return selected

    def _compute_retrieval_confidence(self, documents: list[RetrievedDocument]) -> float:
        if not documents:
            return 0.0
        scores = [float(document.final_score or document.vector_score) for document in documents[:4]]
        average_score = sum(scores) / len(scores)
        kb_bonus = 0.1 if any(document.source_type == "kb" for document in documents[:3]) else 0.0
        evidence_bonus = min(0.1, 0.03 * len(documents))
        return min(1.0, average_score * 0.8 + kb_bonus + evidence_bonus)

    async def _generate_grounded_answer(
        self,
        question: str,
        documents: list[RetrievedDocument],
    ) -> dict[str, Any]:
        source_blocks = []
        for index, document in enumerate(documents, start=1):
            token = f"S{index}"
            source_blocks.append(
                "\n".join(
                    [
                        f"[{token}] {document.citation_label} | {document.title}",
                        trim_text(document.content, 1500),
                    ]
                )
            )

        answer_prompt = (
            "Ты готовишь ответ сотруднику только на основе найденных документов из MSSQL-базы. "
            "Нельзя использовать внешние знания. Если данных не хватает, верни отказ. "
            "Верни только JSON формата "
            '{"answerable": true, "answer": "... [S1]", "used_source_ids": ["S1"], '
            '"confidence": 0.0, "needs_human": false, "reason": "..."}. '
            "В answer каждое фактическое утверждение должно иметь citation token вида [S1]."
        )
        response = await self._yandex_client.generate_json(
            messages=[
                {
                    "role": "user",
                    "text": (
                        f"Вопрос пользователя:\n{question}\n\n"
                        "Доступные источники:\n"
                        + "\n\n".join(source_blocks)
                    ),
                }
            ],
            system_prompt=answer_prompt,
            temperature=0.0,
            max_tokens=1200,
        )

        answer_text = str(response.get("answer") or "").strip()
        if bool(response.get("answerable")) and not answer_text:
            raise YandexGPTError("Model returned empty grounded answer")

        return {
            "answerable": bool(response.get("answerable")),
            "answer_text": answer_text,
            "used_source_ids": [str(value) for value in response.get("used_source_ids") or []],
            "confidence": float(response.get("confidence") or 0.0),
            "needs_human": bool(response.get("needs_human")),
            "reason": str(response.get("reason") or "grounded_answer"),
        }

    async def _verify_answer(
        self,
        *,
        question: str,
        answer_text: str,
        cited_documents: list[RetrievedDocument],
    ) -> dict[str, Any]:
        source_blocks = []
        for index, document in enumerate(cited_documents, start=1):
            source_blocks.append(
                "\n".join(
                    [
                        f"[{index}] {document.citation_label} | {document.title}",
                        trim_text(document.content, 1500),
                    ]
                )
            )

        verifier_prompt = (
            "Проверь, подтверждается ли ответ источниками. Особенно учитывай KB как более надёжный источник. "
            "Если есть неподтверждённые факты, grounded=false. "
            "Верни только JSON формата "
            '{"grounded": true, "confidence": 0.0, "unsupported_claims": [], "reason": "..."}. '
        )
        response = await self._yandex_client.generate_json(
            messages=[
                {
                    "role": "user",
                    "text": (
                        f"Вопрос:\n{question}\n\n"
                        f"Ответ:\n{answer_text}\n\n"
                        "Источники:\n"
                        + "\n\n".join(source_blocks)
                    ),
                }
            ],
            system_prompt=verifier_prompt,
            temperature=0.0,
            max_tokens=700,
        )
        response.setdefault("unsupported_claims", [])
        response.setdefault("grounded", False)
        response.setdefault("confidence", 0.0)
        return response

    def _build_citations(
        self,
        draft_answer: dict[str, Any],
        documents: list[RetrievedDocument],
    ) -> list[tuple[str, RetrievedDocument]]:
        token_to_document = {f"S{index}": document for index, document in enumerate(documents, start=1)}
        requested_tokens = [str(token) for token in draft_answer.get("used_source_ids") or []]
        answer_tokens = SOURCE_TOKEN_RE.findall(draft_answer["answer_text"])
        all_tokens = []
        for token in requested_tokens + answer_tokens:
            if token not in all_tokens:
                all_tokens.append(token)

        citations: list[tuple[str, RetrievedDocument]] = []
        for token in all_tokens:
            document = token_to_document.get(token)
            if document is None:
                continue
            citations.append((token, document))
        return citations

    def _replace_source_tokens(
        self,
        answer_text: str,
        replacements: dict[str, str],
    ) -> str:
        replaced = answer_text
        for token, label in replacements.items():
            replaced = replaced.replace(f"[{token}]", f"[{label}]")
        return replaced

    def _refuse(
        self,
        reply: str,
        *,
        reason: str,
        retrieval_confidence: float = 0.0,
        verification_confidence: float = 0.0,
    ) -> GroundedAnswer:
        return GroundedAnswer(
            reply=reply,
            citations=[],
            confidence=min(retrieval_confidence, verification_confidence),
            grounded=False,
            needs_human=True,
            reason=reason,
            retrieval_confidence=retrieval_confidence,
            verification_confidence=verification_confidence,
        )
