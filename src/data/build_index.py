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
