# classify_service.py
import os
import json
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ticket Classifier", version="1.0")

# Модели данных
class ClassifyRequest(BaseModel):
    description: str
    user_context: Optional[Dict] = None

class ClassifyResponse(BaseModel):
    service_id: Optional[str]
    service_name: Optional[str]
    task_type_id: Optional[str]
    task_type_name: Optional[str]
    priority_id: Optional[str]
    priority_name: Optional[str]
    confidence: float
    explanation: str

# Данные для классификации (в реальном проекте - из БД)
SERVICES = [
    {"id": "1", "name": "ИТ-инфраструктура", "keywords": ["сеть", "vpn", "интернет", "сервер", "компьютер"]},
    {"id": "2", "name": "1С", "keywords": ["1с", "отчет", "бухгалтерия", "документ"]},
    {"id": "3", "name": "Почта и коммуникации", "keywords": ["почта", "outlook", "мессенджер", "телефония"]},
    {"id": "4", "name": "Периферия", "keywords": ["принтер", "сканер", "мышь", "клавиатура"]},
    {"id": "5", "name": "Доступы и права", "keywords": ["пароль", "доступ", "логин", "ad", "аккаунт"]},
]

TASK_TYPES = [
    {"id": "1", "name": "Инцидент", "description": "Что-то не работает"},
    {"id": "2", "name": "Запрос на обслуживание", "description": "Нужна помощь или информация"},
    {"id": "3", "name": "Изменение", "description": "Нужно что-то изменить/настроить"},
]

PRIORITIES = [
    {"id": "1", "name": "Критический", "keywords": ["всё", "критично", "срочно", "стоп", "аврал"]},
    {"id": "2", "name": "Высокий", "keywords": ["важно", "срочно", "немедленно"]},
    {"id": "3", "name": "Средний", "keywords": ["медленно", "неудобно", "помогите"]},
    {"id": "4", "name": "Низкий", "keywords": ["вопрос", "как", "подскажите", "уточнить"]},
]

# Zero-shot классификация через YandexGPT
class ZeroShotClassifier:
    def __init__(self):
        self.api_key = os.getenv("YANDEX_GPT_API_KEY")
        self.folder_id = os.getenv("YANDEX_GPT_FOLDER_ID")
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
    async def classify_service(self, description: str) -> tuple:
        """Классификация сервиса через LLM"""
        services_str = "\n".join([f"{s['id']}. {s['name']}" for s in SERVICES])
        
        prompt = f"""Ты классификатор IT-заявок. Определи, к какому сервису относится проблема.

Список сервисов:
{services_str}

Описание проблемы: "{description}"

Ответь ТОЛЬКО JSON в формате:
{{"service_id": "id", "service_name": "название", "confidence": 0.95}}
"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Api-Key {self.api_key}",
                        "x-folder-id": self.folder_id,
                        "Content-Type": "application/json"
                    },
                    json={
                        "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
                        "completionOptions": {"temperature": 0.1, "maxTokens": 200},
                        "messages": [{"role": "user", "text": prompt}]
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result["result"]["alternatives"][0]["message"]["text"]
                    # Извлекаем JSON из ответа
                    json_start = text.find('{')
                    json_end = text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        data = json.loads(text[json_start:json_end])
                        return data.get("service_id"), data.get("service_name"), data.get("confidence", 0.8)
        except Exception as e:
            logger.error(f"Ошибка классификации сервиса: {e}")
        
        return None, None, 0.5
    
    async def classify_priority(self, description: str) -> tuple:
        """Определение приоритета"""
        priorities_str = "\n".join([f"{p['id']}. {p['name']}: характерные слова - {', '.join(p.get('keywords', []))}" for p in PRIORITIES])
        
        prompt = f"""Определи приоритет заявки по описанию.

Приоритеты:
{priorities_str}

Описание: "{description}"

Ответь JSON: {{"priority_id": "id", "priority_name": "название", "confidence": 0.9}}
"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Api-Key {self.api_key}",
                        "x-folder-id": self.folder_id,
                        "Content-Type": "application/json"
                    },
                    json={
                        "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
                        "completionOptions": {"temperature": 0.1, "maxTokens": 200},
                        "messages": [{"role": "user", "text": prompt}]
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result["result"]["alternatives"][0]["message"]["text"]
                    json_start = text.find('{')
                    json_end = text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        data = json.loads(text[json_start:json_end])
                        return data.get("priority_id"), data.get("priority_name"), data.get("confidence", 0.8)
        except Exception as e:
            logger.error(f"Ошибка классификации приоритета: {e}")
        
        return "3", "Средний", 0.5  # По умолчанию средний
    
    async def classify(self, description: str) -> Dict[str, Any]:
        """Полная классификация"""
        service_id, service_name, service_conf = await self.classify_service(description)
        priority_id, priority_name, priority_conf = await self.classify_priority(description)
        
        # Тип заявки определяем просто по ключевым словам
        task_type_id = "1"  # По умолчанию инцидент
        task_type_name = "Инцидент"
        if any(word in description.lower() for word in ["как", "подскажите", "помогите"]):
            task_type_id = "2"
            task_type_name = "Запрос на обслуживание"
        
        return {
            "service_id": service_id,
            "service_name": service_name,
            "task_type_id": task_type_id,
            "task_type_name": task_type_name,
            "priority_id": priority_id,
            "priority_name": priority_name,
            "confidence": min(service_conf, priority_conf),
            "explanation": f"Сервис определён с уверенностью {service_conf:.0%}, приоритет - с {priority_conf:.0%}"
        }


# Инициализация классификатора
classifier = ZeroShotClassifier()

@app.post("/classify", response_model=ClassifyResponse)
async def classify_ticket(request: ClassifyRequest):
    """Эндпоинт для классификации заявки по описанию"""
    if not request.description or len(request.description) < 5:
        raise HTTPException(status_code=400, detail="Описание слишком короткое")
    
    result = await classifier.classify(request.description)
    
    return ClassifyResponse(**result)


@app.get("/services")
async def get_services():
    """Список доступных сервисов"""
    return {"services": SERVICES}


@app.get("/task_types")
async def get_task_types():
    """Список типов заявок"""
    return {"task_types": TASK_TYPES}


@app.get("/priorities")
async def get_priorities():
    """Список приоритетов"""
    return {"priorities": PRIORITIES}
    
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
