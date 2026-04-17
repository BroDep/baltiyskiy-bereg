import os
import json
import time
import logging
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

import numpy as np
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    PayloadIndexParams, PayloadSchemaType,
    SparseVectorParams, SparseIndexParams,
    OptimizersConfigDiff
)
from sentence_transformers import SentenceTransformer

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class HybridIndexBuilder:
    """
    Построитель гибридного индекса в Qdrant
    Поддерживает dense векторы (1024) и BM25 sparse векторы
    """
    
    def __init__(
        self,
        collection_name: str = "service_desk_chunks",
        embedding_model_name: str = "intfloat/multilingual-e5-large",
        vector_size: int = 1024,
        batch_size: int = 256,
        qdrant_url: str = "http://localhost:6333"
    ):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.batch_size = batch_size
        
        # Подключение к Qdrant
        self.qdrant_client = QdrantClient(url=qdrant_url)
        
        # Инициализация модели эмбеддингов
        logger.info(f"Загрузка модели эмбеддингов: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        
        # Статистика
        self.stats = {
            'total_documents': 0,
            'ticket_chunks': 0,
            'kb_chunks': 0,
            'start_time': None,
            'end_time': None
        }
    
    def load_documents(self) -> List[Dict]:
        """
        Загрузка документов из JSONL файлов
        
        Ожидаемая структура:
        - data/dialogues.jsonl: Q&A пары из тикетов
        - data/kb_chunks.jsonl: Чанки из статей KB
        """
        documents = []
        
        # Загрузка Q&A пар из тикетов
        dialogues_path = "data/dialogues.jsonl"
        if os.path.exists(dialogues_path):
            logger.info(f"Загрузка тикетов из {dialogues_path}")
            with open(dialogues_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        doc['source'] = 'ticket'
                        documents.append(doc)
                        self.stats['ticket_chunks'] += 1
            logger.info(f"Загружено {self.stats['ticket_chunks']} Q&A пар")
        else:
            logger.warning(f"Файл {dialogues_path} не найден, создаю тестовые данные")
            documents.extend(self._create_test_dialogues())
        
        # Загрузка чанков из KB
        kb_path = "data/kb_chunks.jsonl"
        if os.path.exists(kb_path):
            logger.info(f"Загрузка KB статей из {kb_path}")
            with open(kb_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line)
                        doc['source'] = 'kb'
                        documents.append(doc)
                        self.stats['kb_chunks'] += 1
            logger.info(f"Загружено {self.stats['kb_chunks']} KB чанков")
        
        self.stats['total_documents'] = len(documents)
        logger.info(f"Всего документов: {self.stats['total_documents']}")
        
        return documents
    
    def _create_test_dialogues(self) -> List[Dict]:
        """Создание тестовых данных для разработки"""
        os.makedirs("data", exist_ok=True)
        
        test_data = [
            {
                "id": "ticket_1_qa_0",
                "ticket_id": "1",
                "title": "Проблема с VPN подключением",
                "text": "Вопрос: Не могу подключиться к удаленному рабочему столу. Ошибка: timeout. Ответ: Проверьте настройки UniVPN и перезапустите службу.",
                "service_id": "1",
                "service_name": "ИТ-инфраструктура",
                "task_type_id": "1",
                "priority_id": "2",
                "created_date": "2024-01-01"
            },
            {
                "id": "ticket_2_qa_0",
                "ticket_id": "2",
                "title": "Ошибка в 1С",
                "text": "Вопрос: Не формируется отчет по продажам. Ответ: Проверьте период отчета и наличие данных в регистрах накопления.",
                "service_id": "2",
                "service_name": "1С",
                "task_type_id": "1",
                "priority_id": "3",
                "created_date": "2024-01-02"
            }
        ]
        
        # Сохраняем тестовые данные
        with open(dialogues_path, 'w', encoding='utf-8') as f:
            for doc in test_data:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        return test_data
    
    def _preprocess_for_embedding(self, text: str) -> str:
        """Предобработка текста для E5 модели"""
        return f"passage: {text}"
    
    def generate_embeddings(self, documents: List[Dict]) -> List[List[float]]:
        """
        Генерация dense эмбеддингов батчами
        """
        logger.info("Генерация dense эмбеддингов...")
        
        texts = [self._preprocess_for_embedding(doc.get('text', '')) for doc in documents]
        embeddings = []
        
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Эмбеддинги"):
            batch = texts[i:i + self.batch_size]
            try:
                batch_embeddings = self.embedding_model.encode(batch)
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Ошибка генерации эмбеддингов для батча {i}: {e}")
                # Добавляем нулевые векторы
                for _ in batch:
                    embeddings.append(np.zeros(self.vector_size))
        
        logger.info(f"Сгенерировано {len(embeddings)} эмбеддингов")
        return [emb.tolist() for emb in embeddings]
    
    def generate_sparse_vectors(self, documents: List[Dict]) -> List[Dict]:
        """
        Генерация sparse векторов для BM25
        Использует Qdrant sparse vectors API
        """
        logger.info("Генерация sparse векторов для BM25...")
        
        from qdrant_client.models import SparseVector
        from sklearn.feature_extraction.text import CountVectorizer
        
        # Простая реализация через TF-IDF
        vectorizer = CountVectorizer(
            token_pattern=r'(?u)\b\w+\b',
            max_features=10000
        )
        
        texts = [doc.get('text', '') for doc in documents]
        sparse_matrix = vectorizer.fit_transform(texts)
        
        sparse_vectors = []
        vocabulary = vectorizer.get_feature_names_out()
        
        for i in tqdm(range(sparse_matrix.shape[0]), desc="Sparse векторы"):
            row = sparse_matrix[i]
            indices = row.indices.tolist()
            values = row.data.tolist()
            
            sparse_vectors.append({
                "indices": indices,
                "values": values
            })
        
        logger.info(f"Сгенерировано {len(sparse_vectors)} sparse векторов")
        return sparse_vectors
    
    def create_collection(self):
        """
        Создание коллекции в Qdrant с поддержкой:
        - Dense vectors (cosine similarity)
        - Sparse vectors (для BM25)
        - Payload индексы
        """
        logger.info(f"Создание коллекции '{self.collection_name}'...")
        
        # Удаляем существующую коллекцию если есть
        collections = self.qdrant_client.get_collections()
        if self.collection_name in [c.name for c in collections.collections]:
            logger.info(f"Удаление существующей коллекции '{self.collection_name}'")
            self.qdrant_client.delete_collection(self.collection_name)
        
        # Создаем коллекцию с dense и sparse векторами
        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "bm25": SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=True
                    )
                )
            },
            optimizers_config=OptimizersConfigDiff(
                default_segment_number=2,
                indexing_threshold=10000
            )
        )
        
        # Создаем payload индексы для фильтрации
        logger.info("Создание payload индексов...")
        
        # Индекс для service_id
        self.qdrant_client.create_payload_index(
            collection_name=self.collection_name,
            field_name="service_id",
            field_schema=PayloadSchemaType.KEYWORD
        )
        
        # Индекс для source (ticket/kb)
        self.qdrant_client.create_payload_index(
            collection_name=self.collection_name,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD
        )
        
        # Индекс для task_type_id
        self.qdrant_client.create_payload_index(
            collection_name=self.collection_name,
            field_name="task_type_id",
            field_schema=PayloadSchemaType.INTEGER
        )
        
        logger.info("Коллекция и индексы созданы")
    
    def upload_documents(self, documents: List[Dict], embeddings: List[List[float]]):
        """
        Загрузка документов в Qdrant с метаданными
        """
        logger.info("Загрузка документов в Qdrant...")
        
        points = []
        for idx, (doc, emb) in enumerate(tqdm(zip(documents, embeddings), total=len(documents))):
            # Формируем payload с метаданными
            payload = {
                "text": doc.get('text', ''),
                "title": doc.get('title', ''),
                "source": doc.get('source', 'unknown'),
                "ticket_id": doc.get('ticket_id'),
                "service_id": doc.get('service_id'),
                "service_name": doc.get('service_name'),
                "task_type_id": doc.get('task_type_id'),
                "priority_id": doc.get('priority_id'),
                "created_date": doc.get('created_date'),
                "kb_doc_id": doc.get('kb_doc_id'),
                "tags": doc.get('tags', [])
            }
            
            # Удаляем None значения
            payload = {k: v for k, v in payload.items() if v is not None}
            
            point = PointStruct(
                id=idx,
                vector={
                    "dense": emb
                },
                payload=payload
            )
            points.append(point)
            
            # Загружаем батчами
            if len(points) >= self.batch_size:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                points = []
        
        # Загружаем остатки
        if points:
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        
        logger.info(f"Загружено {len(documents)} документов")
    
    def save_bm25_index(self, documents: List[Dict]):
        """
        Сохранение BM25 индекса для fallback (если Qdrant sparse недоступен)
        """
        import pickle
        from rank_bm25 import BM25Okapi
        from nltk.tokenize import word_tokenize
        from nltk.corpus import stopwords
        
        logger.info("Сохранение BM25 fallback индекса...")
        
        # Скачиваем nltk данные если нужно
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
        
        stop_words = set(stopwords.words('russian'))
        
        # Токенизация документов
        tokenized_docs = []
        for doc in documents:
            text = doc.get('text', '')
            tokens = word_tokenize(text.lower())
            tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
            tokenized_docs.append(tokens)
        
        # Построение BM25 индекса
        bm25_index = BM25Okapi(tokenized_docs)
        
        # Сохранение
        os.makedirs("data", exist_ok=True)
        with open("data/bm25_index.pkl", 'wb') as f:
            pickle.dump({
                'bm25_index': bm25_index,
                'documents': documents,
                'tokenized_docs': tokenized_docs
            }, f)
        
        logger.info("BM25 fallback индекс сохранён в data/bm25_index.pkl")
    
    def print_stats(self):
        """Вывод статистики индексации"""
        elapsed = self.stats['end_time'] - self.stats['start_time']
        
        print("\n" + "="*60)
        print("СТАТИСТИКА ИНДЕКСАЦИИ")
        print("="*60)
        print(f"Всего документов: {self.stats['total_documents']}")
        print(f"  - Из тикетов (Q&A): {self.stats['ticket_chunks']}")
        print(f"  - Из KB статей: {self.stats['kb_chunks']}")
        print(f"Время индексации: {elapsed:.2f} сек")
        print(f"Скорость: {self.stats['total_documents'] / elapsed:.1f} док/сек")
        print(f"Размерность векторов: {self.vector_size}")
        print(f"Коллекция Qdrant: {self.collection_name}")
        print("="*60)
    
    def run(self):
        """Запуск полного процесса индексации"""
        self.stats['start_time'] = time.time()
        
        # 1. Загрузка документов
        documents = self.load_documents()
        
        if not documents:
            logger.error("Нет документов для индексации")
            return
        
        # 2. Генерация эмбеддингов
        embeddings = self.generate_embeddings(documents)
        
        # 3. Создание коллекции в Qdrant
        self.create_collection()
        
        # 4. Загрузка в Qdrant
        self.upload_documents(documents, embeddings)
        
        # 5. Сохранение BM25 fallback индекса
        self.save_bm25_index(documents)
        
        self.stats['end_time'] = time.time()
        self.print_stats()
        
        logger.info("✅ Индексация завершена успешно!")


def main():
    """Точка входа для скрипта"""
    builder = HybridIndexBuilder()
    builder.run()


if __name__ == "__main__":
    main()

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
