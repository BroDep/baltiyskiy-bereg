import os
import json
import httpx
from typing import Dict, Optional


class TicketClassifier:
    """Zero-shot классификация через YandexGPT"""
    
    def __init__(self):
        self.api_key = os.getenv("YANDEX_GPT_API_KEY")
        self.folder_id = os.getenv("YANDEX_GPT_FOLDER_ID")
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
        # Данные для классификации
        self.services = {
            "1": "ИТ-инфраструктура",
            "2": "1С и учётные системы",
            "3": "Почта и коммуникации",
            "4": "Периферия и оборудование",
            "5": "Доступы и права"
        }
        
        self.priorities = {
            "1": "Критический (все не работает)",
            "2": "Высокий (срочно нужно)",
            "3": "Средний (мешает работе)",
            "4": "Низкий (вопрос, уточнение)"
        }
    
    async def classify(self, description: str) -> Dict:
        """Классификация заявки"""
        prompt = f"""Ты классификатор IT-заявок. Определи сервис и приоритет.

Описание: "{description}"

Сервисы:
{self._format_dict(self.services)}

Приоритеты:
{self._format_dict(self.priorities)}

Ответь ТОЛЬКО JSON:
{{"service_id": "id", "service_name": "название", "priority_id": "id", "priority_name": "название", "confidence": 0.95}}
"""
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Api-Key {self.api_key}",
                    "x-folder-id": self.folder_id,
                    "Content-Type": "application/json"
                },
                json={
                    "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
                    "completionOptions": {
                        "temperature": 0.1,
                        "maxTokens": 300
                    },
                    "messages": [{"role": "user", "text": prompt}]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["result"]["alternatives"][0]["message"]["text"]
                
                # Извлечение JSON
                import re
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            return {
                "service_id": "3",
                "service_name": "ИТ-инфраструктура",
                "priority_id": "3",
                "priority_name": "Средний",
                "confidence": 0.5
            }
    
    def _format_dict(self, d: Dict) -> str:
        return "\n".join([f"{k}. {v}" for k, v in d.items()])
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
