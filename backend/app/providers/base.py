"""The model adapter seam.

Agent code never imports a vendor SDK. It depends on this interface, and the
concrete provider is chosen by configuration at startup. That is what makes
"citizen data never leaves the government's own servers" a switch rather than a
slogan: point SUTRADHAR_LLM_PROVIDER at `local`, and no request leaves the host.
"""

from abc import ABC, abstractmethod


class ProviderUnavailable(RuntimeError):
    """The configured provider cannot be reached or is not configured.

    Raised rather than returning a guess. The caller turns this into an
    `unverifiable` finding so the officer is told the check could not run,
    instead of being shown a confident answer the system did not actually make.
    """


class LLMProvider(ABC):
    """A text and vision model, reduced to the two things Sutradhar needs."""

    #: Shown on the dept head settings screen. Never shown to an officer.
    name: str = "unknown"

    @abstractmethod
    async def generate(self, system: str, user: str) -> str:
        """Answer a prompt. `user` may contain untrusted document text."""

    @abstractmethod
    async def extract_from_image(self, image_bytes: bytes, prompt: str) -> str:
        """Read the text of a document image."""

    async def health(self) -> bool:
        """Whether the provider is currently usable."""
        return True
