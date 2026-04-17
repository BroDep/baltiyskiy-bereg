# TODO: Реализовать гибридный поиск (BM25 + dense retrieval)
#
# - Подключиться к Qdrant (QDRANT_URL из .env)
# - Принять query: str, вернуть список RetrievedChunk (top-20)
# - Гибридная формула: Score = α * BM25_score + (1-α) * cosine_similarity, α ≈ 0.3–0.5
# - BM25: индексировать лемматизированный текст чанков через rank_bm25 или встроенный BM25 Qdrant
# - Dense: YandexGPT Embeddings API или intfloat/multilingual-e5-large (sentence-transformers)
# - Результат передаётся в reranker.py
