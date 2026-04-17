# TODO: Извлечь Q&A-пары из поля Task.Comment
#
# 1. Подключиться к MSSQL (pymssql), выбрать Task.Id, Task.Name, Task.Comment,
#    Task.ServiceId, Task.TypeId, Task.PriorityId, Task.StatusId, Task.CreatedDate
# 2. Для каждого тикета распарсить Task.Comment (HTML) через BeautifulSoup:
#    - Выделить отдельные блоки комментариев (автор, дата, текст)
#    - Определить роль автора: сотрудник vs. техподдержка (по наличию имени в служебных ролях)
#    - Сформировать диалоговые пары (вопрос сотрудника → ответ поддержки)
# 3. Каждую пару сохранить как документ в JSONL:
#    { "text": "...", "ticket_id": 123, "service_id": 5, "type_id": 2,
#      "priority_id": 1, "status_id": 3, "created_date": "2024-01-15", "title": "..." }
# 4. Ожидаемый объём: ~300 000 документов
# 5. Вывод: data/dialogues.jsonl
