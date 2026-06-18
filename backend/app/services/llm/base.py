"""LLM provider interface and factory."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.config import Settings
from app.models.chat import ChatMessage


class BaseLLMProvider(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    async def stream(
        self,
        message: str,
        history: list[ChatMessage],
    ) -> AsyncGenerator[str, None]:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


def get_llm_provider(settings: Settings) -> BaseLLMProvider:
    if settings.llm_provider == "openai":
        from app.services.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(settings)

    if settings.llm_provider == "gemini":
        from app.services.llm.gemini_provider import GeminiProvider

        return GeminiProvider(settings)

    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
