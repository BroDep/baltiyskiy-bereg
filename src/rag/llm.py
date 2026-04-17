from __future__ import annotations

import os
from dataclasses import dataclass

from openai import AsyncOpenAI


@dataclass
class GenerationResult:
    answer: str
    confidence_score: float  # 0–10


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ["YANDEX_GPT_API_KEY"],
        base_url=os.getenv(
            "YANDEX_GPT_BASE_URL",
            "https://llm.api.cloud.yandex.net/foundationModels/v1/",
        ),
    )


def _model() -> str:
    folder_id = os.environ["YANDEX_GPT_FOLDER_ID"]
    model = os.getenv("YANDEX_GPT_MODEL", "yandexgpt/latest")
    return f"gpt://{folder_id}/{model}"


_ANSWER_SYSTEM = (
    "Ты — ИИ-ассистент службы технической поддержки компании «Балтийский Берег». "
    "Отвечай строго на основе предоставленного контекста. "
    "Если контекст не содержит достаточной информации, честно скажи об этом. "
    "Не придумывай решений, которых нет в контексте. "
    "Отвечай на русском языке, кратко и по делу."
)

_VERIFY_SYSTEM = (
    "Ты — эксперт по оценке качества ответов. "
    "Оцени, насколько ответ основан на предоставленном контексте по шкале 0–10. "
    "10 — ответ полностью опирается на контекст, 0 — ответ не связан с контекстом или содержит выдуманную информацию. "
    "Верни только число от 0 до 10, без пояснений."
)


async def generate(query: str, context: str) -> GenerationResult:
    """Generate answer and verify its groundedness in two LLM calls."""
    client = _client()
    model = _model()

    context_block = f"Контекст:\n{context}\n\n" if context else ""
    answer_prompt = f"{context_block}Вопрос сотрудника: {query}"

    answer_resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _ANSWER_SYSTEM},
            {"role": "user", "content": answer_prompt},
        ],
        max_tokens=512,
        temperature=0.1,
    )
    answer = answer_resp.choices[0].message.content or ""

    # Skip verification when no context was retrieved
    if not context:
        return GenerationResult(answer=answer, confidence_score=4.0)

    verify_prompt = (
        f"Контекст:\n{context}\n\n"
        f"Вопрос: {query}\n\n"
        f"Ответ ассистента: {answer}"
    )
    verify_resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _VERIFY_SYSTEM},
            {"role": "user", "content": verify_prompt},
        ],
        max_tokens=4,
        temperature=0.0,
    )
    raw = (verify_resp.choices[0].message.content or "").strip()
    try:
        score = max(0.0, min(10.0, float(raw)))
    except ValueError:
        score = 5.0

    return GenerationResult(answer=answer, confidence_score=score)
