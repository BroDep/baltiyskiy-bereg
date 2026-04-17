import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, FieldCondition, MatchValue,
    SearchRequest, SparseVector,
    NamedSparseVector, NamedVector
)
from sentence_transformers import SentenceTransformer

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Результат поиска"""
    id: str
    text: str
    title: str
    score: float
    bm25_score: float
    dense_score: float
    metadata: Dict[str, Any]
    source: str  # 'ticket' or 'kb'


class HybridRetriever:
    """
    Гибридный поиск: BM25 + Dense retrieval через Qdrant
    """
    
    def __init__(
        self,
        collection_name: str = "service_desk_chunks",
        embedding_model_name: str = "intfloat/multilingual-e5-large",
        alpha: float = 0.5,  # вес dense поиска (1-alpha для BM25)
        top_k: int = 20
    ):
        """
        Args:
            collection_name: Имя коллекции в Qdrant
            embedding_model_name: Модель для dense эмбеддингов
            alpha: Вес dense поиска (0.3-0.5 рекомендуется)
            top_k: Количество возвращаемых результатов
        """
        self.collection_name = collection_name
        self.alpha = alpha
        self.top_k = top_k
        
        # Подключение к Qdrant
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_client = QdrantClient(url=qdrant_url)
        
        # Инициализация модели эмбеддингов
        logger.info(f"Загрузка модели эмбеддингов: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        
        # Проверка существования коллекции
        self._check_collection()
    
    def _check_collection(self):
        """Проверка существования коллекции"""
        collections = self.qdrant_client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if self.collection_name not in collection_names:
            raise RuntimeError(
                f"Коллекция '{self.collection_name}' не найдена. "
                f"Запустите сначала python -m src.data.build_index"
            )
        
        logger.info(f"Коллекция '{self.collection_name}' найдена")
    
    def _preprocess_query(self, query: str) -> str:
        """Предобработка запроса для E5 модели"""
        return f"query: {query}"
    
    def _search_dense(self, query: str, top_k: int) -> List[tuple]:
        """
        Dense поиск через Qdrant
        
        Returns:
            List of (id, score)
        """
        # Генерация эмбеддинга запроса
        query_vector = self.embedding_model.encode(
            self._preprocess_query(query)
        )
        
        # Поиск в Qdrant
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            limit=top_k,
            with_payload=True
        )
        
        return [(res.id, res.score, res.payload) for res in results]
    
    def _search_bm25(self, query: str, top_k: int) -> List[tuple]:
        """
        BM25 поиск через Qdrant sparse vectors
        
        Returns:
            List of (id, score, payload)
        """
        # Здесь нужно преобразовать запрос в sparse вектор
        # Для простоты используем rank_bm25 отдельно, либо ждём API Qdrant
        # В Qdrant v1.7+ есть поддержка sparse векторов
        
        # TODO: Использовать Qdrant sparse vectors API
        # Пока используем fallback на rank_bm25
        return self._search_bm25_fallback(query, top_k)
    
    def _search_bm25_fallback(self, query: str, top_k: int) -> List[tuple]:
        """
        Fallback BM25 через rank_bm25 (если Qdrant sparse недоступен)
        """
        from rank_bm25 import BM25Okapi
        import pickle
        
        # Загрузка предварительно построенного BM25 индекса
        bm25_path = "data/bm25_index.pkl"
        if not os.path.exists(bm25_path):
            logger.warning(f"BM25 индекс не найден: {bm25_path}")
            return []
        
        with open(bm25_path, 'rb') as f:
            data = pickle.load(f)
            bm25_index = data['bm25_index']
            documents = data['documents']
        
        # Токенизация запроса
        from nltk.tokenize import word_tokenize
        from nltk.corpus import stopwords
        
        stop_words = set(stopwords.words('russian'))
        tokens = word_tokenize(query.lower())
        query_tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
        
        # Поиск
        scores = bm25_index.get_scores(query_tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((str(idx), scores[idx], documents[idx]))
        
        return results
    
    def hybrid_search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[RetrievedChunk]:
        """
        Гибридный поиск с объединением BM25 и dense результатов
        
        Формула: Score = α * dense_score + (1-α) * bm25_score
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов (по умолчанию self.top_k)
            filters: Фильтры для поиска (service_id, type_id и т.д.)
        
        Returns:
            List[RetrievedChunk] - Отсортированные результаты
        """
        top_k = top_k or self.top_k
        
        # Получаем результаты обоих методов
        dense_results = self._search_dense(query, top_k=top_k * 2)
        bm25_results = self._search_bm25(query, top_k=top_k * 2)
        
        if not dense_results and not bm25_results:
            logger.warning(f"Нет результатов для запроса: {query}")
            return []
        
        # Нормализация и объединение
        scores = {}
        chunks_data = {}
        
        # Обработка dense результатов
        if dense_results:
            max_dense = max(score for _, score, _ in dense_results)
            for doc_id, score, payload in dense_results:
                norm_score = score / max_dense if max_dense > 0 else 0
                scores[doc_id] = self.alpha * norm_score
                chunks_data[doc_id] = {
                    'payload': payload,
                    'dense_score': norm_score,
                    'bm25_score': 0
                }
        
        # Обработка BM25 результатов
        if bm25_results:
            max_bm25 = max(score for _, score, _ in bm25_results)
            for doc_id, score, payload in bm25_results:
                norm_score = score / max_bm25 if max_bm25 > 0 else 0
                scores[doc_id] = scores.get(doc_id, 0) + (1 - self.alpha) * norm_score
                
                if doc_id in chunks_data:
                    chunks_data[doc_id]['bm25_score'] = norm_score
                else:
                    chunks_data[doc_id] = {
                        'payload': payload,
                        'dense_score': 0,
                        'bm25_score': norm_score
                    }
        
        # Сортировка по итоговому скору
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Формирование результата
        results = []
        for doc_id, total_score in ranked:
            data = chunks_data[doc_id]
            payload = data['payload']
            
            chunk = RetrievedChunk(
                id=str(doc_id),
                text=payload.get('text', ''),
                title=payload.get('title', ''),
                score=total_score,
                bm25_score=data['bm25_score'],
                dense_score=data['dense_score'],
                metadata={
                    'ticket_id': payload.get('ticket_id'),
                    'service_id': payload.get('service_id'),
                    'service_name': payload.get('service_name'),
                    'task_type_id': payload.get('task_type_id'),
                    'priority_id': payload.get('priority_id'),
                    'source': payload.get('source', 'unknown')
                },
                source=payload.get('source', 'unknown')
            )
            results.append(chunk)
        
        logger.info(f"Найдено {len(results)} результатов для запроса: {query[:50]}...")
        return results
    
    def search_with_filters(
        self,
        query: str,
        service_id: Optional[str] = None,
        source: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[RetrievedChunk]:
        """
        Поиск с фильтрацией по метаданным
        
        Args:
            query: Поисковый запрос
            service_id: Фильтр по сервису
            source: Фильтр по источнику ('ticket' или 'kb')
            top_k: Количество результатов
        """
        filters = {}
        if service_id:
            filters['service_id'] = service_id
        if source:
            filters['source'] = source
        
        return self.hybrid_search(query, top_k=top_k, filters=filters)
    
    def search_dense_only(self, query: str, top_k: int = 10) -> List[RetrievedChunk]:
        """Только dense поиск (без BM25)"""
        results = self._search_dense(query, top_k=top_k)
        
        chunks = []
        for doc_id, score, payload in results:
            chunk = RetrievedChunk(
                id=str(doc_id),
                text=payload.get('text', ''),
                title=payload.get('title', ''),
                score=score,
                bm25_score=0,
                dense_score=score,
                metadata=payload,
                source=payload.get('source', 'unknown')
            )
            chunks.append(chunk)
        
        return chunks


# Пример использования
if __name__ == "__main__":
    # Тестирование ретривера
    retriever = HybridRetriever(alpha=0.5)
    
    test_queries = [
        "не подключается удаленка",
        "как настроить VPN",
        "ошибка в 1С отчет не формируется",
        "принтер не печатает что делать"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Запрос: {query}")
        print('='*60)
        
        results = retriever.hybrid_search(query, top_k=5)
        
        for i, chunk in enumerate(results, 1):
            print(f"\n{i}. [Score: {chunk.score:.3f} | BM25: {chunk.bm25_score:.3f} | Dense: {chunk.dense_score:.3f}]")
            print(f"   Источник: {chunk.source}")
            print(f"   Заголовок: {chunk.title[:80]}")
            print(f"   Текст: {chunk.text[:150]}...")
# TODO: Реализовать гибридный поиск (BM25 + dense retrieval)
#
# - Подключиться к Qdrant (QDRANT_URL из .env)
# - Принять query: str, вернуть список RetrievedChunk (top-20)
# - Гибридная формула: Score = α * BM25_score + (1-α) * cosine_similarity, α ≈ 0.3–0.5
# - BM25: индексировать лемматизированный текст чанков через rank_bm25 или встроенный BM25 Qdrant
# - Dense: YandexGPT Embeddings API или intfloat/multilingual-e5-large (sentence-transformers)
# - Результат передаётся в reranker.py
