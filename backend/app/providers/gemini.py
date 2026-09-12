"""Gemini provider.

Uses the REST API over httpx rather than the vendor SDK, so the dependency
surface stays small and the request shape is visible in this file. Nothing
outside this module knows Gemini exists.
"""

import base64
import logging

import httpx

from app.providers.base import LLMProvider, ProviderUnavailable

logger = logging.getLogger(__name__)

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None, model: str = "gemini-2.0-flash") -> None:
        self._api_key = api_key
        self._model = model

    def _require_key(self) -> str:
        if not self._api_key:
            raise ProviderUnavailable(
                "SUTRADHAR_GEMINI_API_KEY is not set, so the document could not be read."
            )
        return self._api_key

    async def _post(self, parts: list[dict], system: str | None) -> str:
        key = self._require_key()
        payload: dict = {"contents": [{"role": "user", "parts": parts}]}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        # Deterministic reads: this is an extraction task, not a creative one.
        payload["generationConfig"] = {"temperature": 0.0}

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    _ENDPOINT.format(model=self._model),
                    params={"key": key},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            # Log the class of failure, never the payload: it carries citizen data.
            logger.warning("gemini request failed: %s", type(exc).__name__)
            raise ProviderUnavailable("The reading service could not be reached.") from exc

        if response.status_code != 200:
            logger.warning("gemini returned status %s", response.status_code)
            raise ProviderUnavailable("The reading service rejected the request.")

        body = response.json()
        try:
            return body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ProviderUnavailable("The reading service returned nothing usable.") from exc

    async def generate(self, system: str, user: str) -> str:
        return await self._post([{"text": user}], system)

    async def extract_from_image(self, image_bytes: bytes, prompt: str) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        parts = [
            {"inline_data": {"mime_type": "image/png", "data": encoded}},
            {"text": prompt},
        ]
        return await self._post(parts, None)

    async def health(self) -> bool:
        return bool(self._api_key)
