"""On-premise provider, shaped for Ollama.

The point of this class is the deployment claim: with SUTRADHAR_LLM_PROVIDER
set to `local`, every request goes to a host the department runs, and no citizen
data crosses the network boundary. The wire format below is Ollama's, which
several self-hosted runtimes also speak.
"""

import base64
import logging

import httpx

from app.providers.base import LLMProvider, ProviderUnavailable

logger = logging.getLogger(__name__)


class LocalProvider(LLMProvider):
    name = "local"

    def __init__(self, base_url: str, model: str = "llama3.2-vision") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def _chat(self, messages: list[dict]) -> str:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json={"model": self._model, "messages": messages, "stream": False,
                          "options": {"temperature": 0.0}},
                )
        except httpx.HTTPError as exc:
            logger.warning("local model request failed: %s", type(exc).__name__)
            raise ProviderUnavailable(
                "The on-premise reading service could not be reached."
            ) from exc

        if response.status_code != 200:
            logger.warning("local model returned status %s", response.status_code)
            raise ProviderUnavailable("The on-premise reading service rejected the request.")

        try:
            return response.json()["message"]["content"]
        except (KeyError, ValueError) as exc:
            raise ProviderUnavailable("The on-premise service returned nothing usable.") from exc

    async def generate(self, system: str, user: str) -> str:
        return await self._chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )

    async def extract_from_image(self, image_bytes: bytes, prompt: str) -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return await self._chat(
            [{"role": "user", "content": prompt, "images": [encoded]}]
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                return (await client.get(f"{self._base_url}/api/tags")).status_code == 200
        except httpx.HTTPError:
            return False
