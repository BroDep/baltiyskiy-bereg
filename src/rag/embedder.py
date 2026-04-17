# TODO: Реализовать генерацию эмбеддингов для индексации и запросов
#
# - Вариант A (API): YandexGPT text-embedding-v3, размерность 1024
#   POST https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding
# - Вариант B (локально): intfloat/multilingual-e5-large через sentence-transformers
#   Быстрее на CPU, не требует API-квоты для индексации
# - Поддержать батч-обработку для build_index.py (тысячи документов)
# - Функция embed_query(text) — для одного запроса в runtime
# - Функция embed_documents(texts) — для батч-индексации
