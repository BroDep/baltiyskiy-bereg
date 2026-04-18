from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from src.config import Settings
from src.services.mssql_knowledge_base import MSSQLKnowledgeBase
from src.services.qdrant_store import QdrantStore
from src.services.rag_models import RagDocument, SyncStatus, SyncSummary
from src.services.yandex_gpt import YandexGPTClient

logger = logging.getLogger(__name__)


class RagSyncService:
    def __init__(
        self,
        settings: Settings,
        knowledge_base: MSSQLKnowledgeBase,
        qdrant_store: QdrantStore,
        yandex_client: YandexGPTClient,
    ) -> None:
        self._settings = settings
        self._knowledge_base = knowledge_base
        self._qdrant_store = qdrant_store
        self._yandex_client = yandex_client
        self._status = SyncStatus()
        self._sync_lock = asyncio.Lock()
        self._background_task: asyncio.Task[None] | None = None
        self._state = self._load_state()

    async def start(self) -> None:
        if not self._settings.rag_enabled:
            return
        if not self._settings.rag_sync_on_startup and self._settings.rag_sync_interval_seconds <= 0:
            return
        if self._background_task and not self._background_task.done():
            return
        self._background_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._background_task is None:
            return
        self._background_task.cancel()
        try:
            await self._background_task
        except asyncio.CancelledError:
            pass
        self._background_task = None

    async def sync_now(self, *, full_sync: bool | None = None) -> SyncSummary:
        async with self._sync_lock:
            return await self._sync_now_locked(full_sync=full_sync)

    async def get_status(self) -> SyncStatus:
        status = SyncStatus(
            ready=self._status.ready,
            running=self._status.running,
            last_sync_started_at=self._status.last_sync_started_at,
            last_sync_finished_at=self._status.last_sync_finished_at,
            last_sync_success=self._status.last_sync_success,
            last_error=self._status.last_error,
            indexed_documents=await asyncio.to_thread(self._qdrant_store.count_documents),
        )
        status.ready = status.indexed_documents > 0 and self._status.last_sync_success
        return status

    async def _run_loop(self) -> None:
        run_initial_sync = self._settings.rag_sync_on_startup
        while True:
            try:
                if run_initial_sync or self._settings.rag_sync_interval_seconds > 0:
                    await self.sync_now(full_sync=None)
                    run_initial_sync = False
                if self._settings.rag_sync_interval_seconds <= 0:
                    return
                await asyncio.sleep(self._settings.rag_sync_interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - defensive logging for background loop
                logger.exception("Background RAG sync failed")
                if self._settings.rag_sync_interval_seconds <= 0:
                    return
                await asyncio.sleep(self._settings.rag_sync_interval_seconds)

    async def _sync_now_locked(self, *, full_sync: bool | None) -> SyncSummary:
        self._status.running = True
        self._status.last_sync_started_at = datetime.now(tz=UTC)
        self._status.last_error = None

        try:
            should_run_full_sync = full_sync
            if should_run_full_sync is None:
                indexed_documents = await asyncio.to_thread(self._qdrant_store.count_documents)
                should_run_full_sync = indexed_documents == 0 or not self._state.get(
                    "last_successful_sync_at"
                )

            summary = (
                await self._run_full_sync()
                if should_run_full_sync
                else await self._run_incremental_sync()
            )
            finished_at = datetime.now(tz=UTC)
            self._state["last_successful_sync_at"] = finished_at.isoformat()
            self._save_state()

            self._status.last_sync_success = True
            self._status.last_sync_finished_at = finished_at
            self._status.indexed_documents = await asyncio.to_thread(
                self._qdrant_store.count_documents
            )
            self._status.ready = self._status.indexed_documents > 0
            logger.info(
                "RAG sync finished: full_sync=%s ticket_documents=%s kb_documents=%s indexed=%s",
                summary.full_sync,
                summary.ticket_documents,
                summary.kb_documents,
                self._status.indexed_documents,
            )
            return summary
        except Exception as exc:
            self._status.last_sync_success = False
            self._status.last_sync_finished_at = datetime.now(tz=UTC)
            self._status.last_error = str(exc)
            logger.exception("RAG sync failed")
            raise
        finally:
            self._status.running = False

    async def _run_full_sync(self) -> SyncSummary:
        summary = SyncSummary(full_sync=True)
        tickets_done = self._state.get("full_sync_tickets_done") == "true"
        last_ticket_id = int(self._state.get("full_sync_ticket_last_id", "0"))
        if not tickets_done:
            while True:
                ticket_documents = await asyncio.to_thread(
                    self._knowledge_base.fetch_ticket_batch_after_id,
                    last_ticket_id,
                    self._settings.rag_sync_batch_size,
                )
                if not ticket_documents:
                    self._state["full_sync_tickets_done"] = "true"
                    self._state.pop("full_sync_ticket_last_id", None)
                    self._save_state()
                    break
                await self._index_documents(ticket_documents, replace=False)
                summary.ticket_documents += len(ticket_documents)
                last_ticket_id = max(document.source_id for document in ticket_documents)
                self._state["full_sync_ticket_last_id"] = str(last_ticket_id)
                self._save_state()

        last_kb_id = int(self._state.get("full_sync_kb_last_id", "0"))
        while True:
            kb_documents = await asyncio.to_thread(
                self._knowledge_base.fetch_kb_batch_after_id,
                last_kb_id,
                self._settings.rag_sync_batch_size,
            )
            if not kb_documents:
                break
            await self._index_documents(kb_documents, replace=True)
            summary.kb_documents += len(kb_documents)
            last_kb_id = max(document.source_id for document in kb_documents)
            self._state["full_sync_kb_last_id"] = str(last_kb_id)
            self._save_state()

        self._state.pop("full_sync_ticket_last_id", None)
        self._state.pop("full_sync_tickets_done", None)
        self._state.pop("full_sync_kb_last_id", None)
        self._save_state()

        return summary

    async def _run_incremental_sync(self) -> SyncSummary:
        summary = SyncSummary(full_sync=False)
        last_successful_sync_at = self._state.get("last_successful_sync_at")
        if not last_successful_sync_at:
            return await self._run_full_sync()

        changed_after = datetime.fromisoformat(last_successful_sync_at)
        ticket_documents = await asyncio.to_thread(
            self._knowledge_base.fetch_ticket_documents_changed_after,
            changed_after,
        )
        kb_documents = await asyncio.to_thread(
            self._knowledge_base.fetch_kb_documents_changed_after,
            changed_after,
        )

        await self._index_documents(ticket_documents, replace=False)
        await self._index_documents(kb_documents, replace=True)
        summary.ticket_documents = len(ticket_documents)
        summary.kb_documents = len(kb_documents)
        return summary

    async def _index_documents(
        self,
        documents: list[RagDocument],
        *,
        replace: bool,
    ) -> None:
        if not documents:
            return

        embeddings = await self._embed_documents(documents)
        await asyncio.to_thread(self._qdrant_store.ensure_collection, len(embeddings[0]))
        if replace:
            await asyncio.to_thread(self._qdrant_store.replace_documents, documents, embeddings)
            return
        await asyncio.to_thread(self._qdrant_store.upsert_documents, documents, embeddings)

    async def _embed_documents(self, documents: list[RagDocument]) -> list[list[float]]:
        semaphore = asyncio.Semaphore(1)

        async def embed(document: RagDocument) -> list[float]:
            async with semaphore:
                embedding = await self._yandex_client.embed_text(document.content, kind="doc")
                await asyncio.sleep(0.2)
                return embedding

        return await asyncio.gather(*(embed(document) for document in documents))

    def _load_state(self) -> dict[str, str]:
        path = self._settings.rag_sync_state_file
        try:
            if not path.exists():
                return {}
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            logger.warning("Failed to parse sync state file, starting from empty state")
            return {}
        except OSError:
            logger.warning("Failed to read sync state file %s, starting from empty state", path)
            return {}

    def _save_state(self) -> None:
        path = self._settings.rag_sync_state_file
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._state, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        except OSError:
            logger.warning("Failed to persist sync state file %s", path)
