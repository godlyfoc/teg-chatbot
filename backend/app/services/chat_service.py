"""Chat business logic."""

from collections.abc import AsyncGenerator

from app.config import Settings
from app.models.chat import ChatMessage
from app.services.llm.base import get_llm_provider


class ChatService:
    def __init__(self, settings: Settings):
        self.llm = get_llm_provider(settings)

    async def stream(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.llm.stream(message, history or []):
            yield chunk

    @property
    def provider_info(self) -> dict:
        return {"provider": self.llm.provider_name, "model": self.llm.model_name}
