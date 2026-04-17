# build_index.py
import json
import os
import logging
from typing import List, Dict, Any
from tqdm import tqdm
import numpy as np

# Векторизация
from sentence_transformers import SentenceTransformer

# BM25
from rank_bm25 import BM25Okapi

# Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue
)

# Токенизация для BM25
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Скачиваем nltk данные
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

RUSSIAN_STOPWORDS = set(stopwords.words('russian'))

class HybridIndexBuilder:
    def __init__(
        self,
        embedding_model_name: str = "intfloat/multilingual-e5-large",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "tickets_kb",
        vector_size: int = 1024,
        batch_size: int = 32
    ):
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.batch_size = batch_size
        self.documents = []  # для BM25
        self.bm25_index = None
        
    def load_documents(self, jsonl_path: str) -> List[Dict]:
        """Загрузка документов из JSONL"""
        docs = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    docs.append(json.loads(line))
        logger.info(f"Загружено {len(docs)} документов")
        return docs
    
    def preprocess_text(self, text: str) -> List[str]:
        """Токенизация и очистка текста для BM25"""
        if not text:
            return []
        tokens = word_tokenize(text.lower())
        tokens = [t for t in tokens if t.isalpha() and t not in RUSSIAN_STOPWORDS]
        return tokens
    
    def build_bm25_index(self, documents: List[Dict]):
        """Построение BM25 индекса"""
        logger.info("Построение BM25 индекса...")
        self.documents = documents
        
        tokenized_docs = []
        for doc in tqdm(documents, desc="Токенизация для BM25"):
            text = doc.get('text', '') + ' ' + doc.get('title', '')
            tokenized_docs.append(self.preprocess_text(text))
        
        self.bm25_index = BM25Okapi(tokenized_docs)
        logger.info("BM25 индекс построен")
    
    def compute_embeddings(self, documents: List[Dict]) -> np.ndarray:
        """Вычисление эмбеддингов батчами"""
        logger.info("Вычисление эмбеддингов...")
        texts = [doc.get('text', '') for doc in documents]
        
        # Для E5 модели нужен префикс
        texts = [f"query: {t}" if i == 0 else f"passage: {t}" for i, t in enumerate(texts)]
        
        embeddings = []
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Эмбеддинги"):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.embedding_model.encode(batch)
            embeddings.extend(batch_embeddings)
        
        return np.array(embeddings)
    
    def create_qdrant_collection(self):
        """Создание коллекции в Qdrant"""
        existing_collections = self.qdrant_client.get_collections()
        if self.collection_name in [c.name for c in existing_collections.collections]:
            logger.info(f"Коллекция {self.collection_name} уже существует, удаляем...")
            self.qdrant_client.delete_collection(self.collection_name)
        
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Коллекция {self.collection_name} создана")
    
    def upload_to_qdrant(self, documents: List[Dict], embeddings: np.ndarray):
        """Загрузка документов и эмбеддингов в Qdrant"""
        logger.info("Загрузка в Qdrant...")
        
        points = []
        for idx, (doc, emb) in enumerate(tqdm(zip(documents, embeddings), total=len(documents))):
            point = PointStruct(
                id=idx,
                vector=emb.tolist(),
                payload={
                    'text': doc.get('text', ''),
                    'title': doc.get('title', ''),
                    'ticket_id': doc.get('ticket_id'),
                    'service_id': doc.get('service_id'),
                    'service_name': doc.get('service_name'),
                    'task_type_id': doc.get('task_type_id'),
                    'priority_id': doc.get('priority_id'),
                    'source': doc.get('source', 'ticket'),  # 'ticket' or 'kb'
                    'created_date': doc.get('created_date'),
                }
            )
            points.append(point)
            
            # Загружаем батчами по 100
            if len(points) >= 100:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                points = []
        
        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        
        logger.info(f"Загружено {len(documents)} точек в Qdrant")
    
    def save_bm25_index(self, path: str):
        """Сохранение BM25 индекса на диск"""
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'bm25_index': self.bm25_index,
                'documents': self.documents
            }, f)
        logger.info(f"BM25 индекс сохранён в {path}")
    
    def run(self, input_jsonl: str, output_bm25_path: str = "bm25_index.pkl"):
        """Запуск полного процесса индексации"""
        # 1. Загрузка документов
        documents = self.load_documents(input_jsonl)
        
        # 2. Построение BM25 индекса
        self.build_bm25_index(documents)
        self.save_bm25_index(output_bm25_path)
        
        # 3. Вычисление эмбеддингов
        embeddings = self.compute_embeddings(documents)
        
        # 4. Загрузка в Qdrant
        self.create_qdrant_collection()
        self.upload_to_qdrant(documents, embeddings)
        
        logger.info("✅ Индексация завершена!")
        
        return self


class HybridSearcher:
    """Гибридный поиск (BM25 + векторный)"""
    def __init__(
        self,
        embedding_model_name: str = "intfloat/multilingual-e5-large",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "tickets_kb",
        bm25_path: str = "bm25_index.pkl",
        alpha: float = 0.5  # вес векторного поиска
    ):
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.collection_name = collection_name
        self.alpha = alpha
        
        # Загрузка BM25 индекса
        import pickle
        with open(bm25_path, 'rb') as f:
            data = pickle.load(f)
            self.bm25_index = data['bm25_index']
            self.documents = data['documents']
        
        # Токенизатор для BM25
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        
    def preprocess_text(self, text: str) -> List[str]:
        from nltk.tokenize import word_tokenize
        from nltk.corpus import stopwords
        stop_words = set(stopwords.words('russian'))
        tokens = word_tokenize(text.lower())
        return [t for t in tokens if t.isalpha() and t not in stop_words]
    
    def search_bm25(self, query: str, top_k: int = 100) -> List[tuple]:
        """Поиск по BM25"""
        tokenized_query = self.preprocess_text(query)
        scores = self.bm25_index.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(idx, scores[idx]) for idx in top_indices if scores[idx] > 0]
    
    def search_vector(self, query: str, top_k: int = 100) -> List[tuple]:
        """Векторный поиск через Qdrant"""
        query_vector = self.embedding_model.encode(f"query: {query}")
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            limit=top_k
        )
        return [(res.id, res.score) for res in results]
    
    def hybrid_search(self, query: str, top_k: int = 20) -> List[Dict]:
        """Гибридный поиск с объединением результатов"""
        # Получаем результаты
        bm25_results = self.search_bm25(query, top_k=100)
        vector_results = self.search_vector(query, top_k=100)
        
        # Нормализация и объединение
        scores = {}
        
        # BM25 результаты
        max_bm25 = max([s for _, s in bm25_results]) if bm25_results else 1
        for idx, score in bm25_results:
            norm_score = score / max_bm25 if max_bm25 > 0 else 0
            scores[idx] = (1 - self.alpha) * norm_score
        
        # Векторные результаты
        max_vector = max([s for _, s in vector_results]) if vector_results else 1
        for idx, score in vector_results:
            norm_score = score / max_vector if max_vector > 0 else 0
            scores[idx] = scores.get(idx, 0) + self.alpha * norm_score
        
        # Сортировка и возврат
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for idx, score in ranked:
            doc = self.documents[idx].copy()
            doc['hybrid_score'] = score
            results.append(doc)
        
        return results


def test_search(searcher: HybridSearcher, test_queries: List[str]):
    """Тестирование поиска на примерах"""
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ГИБРИДНОГО ПОИСКА")
    print("="*60)
    
    for query in test_queries:
        print(f"\n📝 Запрос: {query}")
        print("-" * 40)
        
        results = searcher.hybrid_search(query, top_k=3)
        
        for i, doc in enumerate(results, 1):
            print(f"\n  {i}. [score={doc['hybrid_score']:.3f}]")
            print(f"     Источник: {doc.get('source', 'unknown')}")
            print(f"     Заголовок: {doc.get('title', 'Нет заголовка')[:80]}")
            print(f"     Текст: {doc.get('text', '')[:150]}...")
            if doc.get('ticket_id'):
                print(f"     Ticket ID: {doc.get('ticket_id')}")


if __name__ == "__main__":
    # Пример использования
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Построить индекс")
    parser.add_argument("--test", action="store_true", help="Протестировать поиск")
    parser.add_argument("--input", type=str, default="data/documents.jsonl", help="Путь к JSONL")
    args = parser.parse_args()
    
    if args.build:
        builder = HybridIndexBuilder()
        builder.run(args.input)
    
    if args.test:
        searcher = HybridSearcher()
        
        test_queries = [
            "не подключается удаленка",
            "как настроить VPN",
            "не работает 1С",
            "проблема с отчетом в 1С",
            "забыл пароль от почты",
            "как подключить принтер",
            "не открывается сайт",
            "медленно работает компьютер"
        ]
        
        test_search(searcher, test_queries)
      
# TODO: Построить гибридный индекс в Qdrant
#
# 1. Загрузить данные из data/dialogues.jsonl и data/kb_chunks.jsonl
# 2. Инициализировать Qdrant-коллекцию с параметрами:
#    - vectors: size=1024, distance=Cosine (под multilingual-e5-large или YaGPT embeddings)
#    - sparse_vectors: для BM25 (Qdrant sparse vectors API)
# 3. Батч-обработка документов:
#    - Сгенерировать dense-эмбеддинги через embedder.py (батчи по 256)
#    - Токенизировать и вычислить BM25 sparse-вектора
#    - Загрузить в Qdrant (upsert) с payload: все метаданные документа
# 4. Создать payload-индексы по service_id, type_id, kb_doc_id для фильтрации
# 5. По окончании вывести статистику: кол-во документов, время индексации
# 6. Запуск: python -m src.data.build_index
