from __future__ import annotations

import logging
from typing import Any

import httpx

from src.config import Settings

logger = logging.getLogger(__name__)


class YandexGPTError(RuntimeError):
    """Raised when YandexGPT request or response handling fails."""


class YandexGPTClient:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._http_client = http_client or httpx.AsyncClient(
            timeout=settings.yandex_gpt_timeout_seconds
        )
        self._owns_http_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    def _build_payload(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        prompt = system_prompt or self._settings.yandex_gpt_system_prompt
        return {
            "modelUri": self._settings.yandex_gpt_model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self._settings.yandex_gpt_temperature,
                "maxTokens": str(self._settings.yandex_gpt_max_tokens),
            },
            "messages": [
                {"role": "system", "text": prompt},
                {"role": "user", "text": message},
            ],
        }

    async def generate_reply(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        self._settings.validate_yandex()
        payload = self._build_payload(message=message, system_prompt=system_prompt)
        headers = {
            "Authorization": f"Api-Key {self._settings.yandex_gpt_api_key_value}",
            "Content-Type": "application/json",
        }

        logger.info(
            "Sending request to YandexGPT: message_length=%s",
            len(message),
        )

        try:
            response = await self._http_client.post(
                self._settings.yandex_gpt_endpoint,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("YandexGPT HTTP request failed")
            raise YandexGPTError("Failed to call YandexGPT") from exc

        try:
            response_data = response.json()
            reply = response_data["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.exception("YandexGPT response parsing failed")
            raise YandexGPTError("Invalid response format from YandexGPT") from exc

        cleaned_reply = reply.strip()
        if not cleaned_reply:
            raise YandexGPTError("YandexGPT returned an empty response")

        logger.info(
            "Received response from YandexGPT: reply_length=%s",
            len(cleaned_reply),
        )
        return cleaned_reply
