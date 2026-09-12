"""Chooses the provider.

The selection lives in the `settings` table so a dept head can switch it at
runtime, falling back to the environment default when nothing is stored. The
dept head settings screen writes that row; agent code only ever calls
`get_provider()`.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.setting import LLM_PROVIDER_KEY, Setting
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.local import LocalProvider

logger = logging.getLogger(__name__)


def build_provider(name: str) -> LLMProvider:
    settings = get_settings()
    if name == "local":
        return LocalProvider(settings.local_model_base_url)
    return GeminiProvider(settings.gemini_api_key)


def get_provider(session: Session | None = None) -> LLMProvider:
    """The active provider: the stored choice if present, else the configured one."""
    name = get_settings().llm_provider
    if session is not None:
        stored = session.scalar(select(Setting).where(Setting.key == LLM_PROVIDER_KEY))
        if stored is not None and stored.value in {"gemini", "local"}:
            name = stored.value
    return build_provider(name)
