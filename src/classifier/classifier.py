# TODO: Классификатор заявок — предсказать ServiceId, TaskTypeId, PriorityId
#
# Вариант A — Zero-shot через YandexGPT (быстрый прототип):
#   - Передать текст заявки + список допустимых значений (из lookup-таблиц MSSQL)
#   - Попросить вернуть JSON: { "service_id": N, "task_type_id": N, "priority_id": N, "confidence": 0.9 }
#   - Минус: нестабильно на коротких/неоднозначных текстах
#
# Вариант B — CatBoost (точнее, требует обучения):
#   - Признаки: dense-эмбеддинг текста (embedder.py) + длина текста + час создания
#   - Три отдельных классификатора: service, task_type, priority
#   - Обучение на исторических тикетах с известными метками
#   - Сохранение модели: models/classifier_service.cbm и т.д.
#
# Интерфейс:
#   classify(description: str) -> { service_id, task_type_id, priority_id, confidence }
# Используется в POST /classify (src/api/main.py)
