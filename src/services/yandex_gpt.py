from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal

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

    async def generate_reply(
        self,
        message: str,
        system_prompt: str | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        return await self.generate_text(
            messages=[{"role": "user", "text": message}],
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_text(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        self._settings.validate_yandex()
        payload = self._build_completion_payload(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response_data = await self._post_json(
            self._settings.yandex_gpt_endpoint,
            payload,
        )

        try:
            reply = response_data["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.exception("YandexGPT response parsing failed")
            raise YandexGPTError("Invalid response format from YandexGPT") from exc

        cleaned_reply = reply.strip()
        if not cleaned_reply:
            raise YandexGPTError("YandexGPT returned an empty response")

        logger.info("Received completion from YandexGPT: reply_length=%s", len(cleaned_reply))
        return cleaned_reply

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        response_text = await self.generate_text(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._extract_json_object(response_text)

    async def embed_text(
        self,
        text: str,
        *,
        kind: Literal["doc", "query"],
    ) -> list[float]:
        self._settings.validate_yandex()
        model_uri = (
            self._settings.yandex_embedding_doc_model_uri
            if kind == "doc"
            else self._settings.yandex_embedding_query_model_uri
        )
        payload = {
            "modelUri": model_uri,
            "text": " ".join(text.split()),
        }
        response_data = await self._post_json(
            self._settings.yandex_embedding_endpoint,
            payload,
        )
        embedding = response_data.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise YandexGPTError("Invalid embedding response from YandexGPT")
        return [float(value) for value in embedding]

    def _build_completion_payload(
        self,
        *,
        messages: list[dict[str, str]],
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        prompt = system_prompt or self._settings.yandex_gpt_system_prompt
        full_messages: list[dict[str, str]] = []
        if prompt:
            full_messages.append({"role": "system", "text": prompt})
        full_messages.extend(messages)
        return {
            "modelUri": self._settings.yandex_gpt_model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": (
                    self._settings.yandex_gpt_temperature
                    if temperature is None
                    else temperature
                ),
                "maxTokens": str(max_tokens or self._settings.yandex_gpt_max_tokens),
            },
            "messages": full_messages,
        }

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Api-Key {self._settings.yandex_gpt_api_key_value}",
            "Content-Type": "application/json",
        }
        for attempt in range(5):
            logger.info("Sending request to Yandex AI endpoint: url=%s", url)
            try:
                response = await self._http_client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code in {429, 500, 502, 503, 504} and attempt < 4:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                logger.exception("Yandex AI HTTP request failed")
                raise YandexGPTError("Failed to call Yandex AI endpoint") from exc
            except httpx.HTTPError as exc:
                logger.exception("Yandex AI HTTP request failed")
                raise YandexGPTError("Failed to call Yandex AI endpoint") from exc

            try:
                return response.json()
            except ValueError as exc:
                logger.exception("Failed to decode Yandex AI response JSON")
                raise YandexGPTError("Invalid JSON from Yandex AI endpoint") from exc

        raise YandexGPTError("Failed to call Yandex AI endpoint")

    def _extract_json_object(self, response_text: str) -> dict[str, Any]:
        stripped = response_text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            stripped = stripped.removeprefix("json").strip()

        for start_token, end_token in (("{", "}"), ("[", "]")):
            start_index = stripped.find(start_token)
            end_index = stripped.rfind(end_token)
            if start_index == -1 or end_index == -1 or end_index <= start_index:
                continue
            candidate = stripped[start_index : end_index + 1]
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"items": parsed}

        raise YandexGPTError("YandexGPT did not return valid JSON")
