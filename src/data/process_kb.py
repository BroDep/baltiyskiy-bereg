# TODO: Обработать статьи KBDocument для индексации
#
# 1. Выбрать из MSSQL: KBDocument.Id, Name, Description (HTML), IsPublished, Rating
#    + теги через JOIN KBDocumentTag → KBTag
#    + путь папки через KBFolder (рекурсивный CTE)
# 2. Отфильтровать IsPublished = 1
# 3. Для каждой статьи:
#    - Извлечь чистый текст из HTML (BeautifulSoup), сохранить структуру заголовков h1/h2
#    - Разбить на чанки 300–500 токенов с перекрытием 20%
# 4. Каждый чанк сохранить как документ в JSONL:
#    { "text": "...", "kb_doc_id": 42, "title": "...", "tags": [...],
#      "folder_path": "ИТ / Сеть", "rating": 4.5 }
# 5. Ожидаемый объём: ~4 000 документов
# 6. Вывод: data/kb_chunks.jsonl
