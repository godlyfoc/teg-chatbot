"""Chat business logic."""

from collections.abc import AsyncGenerator

from app.config import Settings
from app.models.chat import ChatMessage
from app.services.llm.openai_provider import OpenAIChat


class ChatService:
    def __init__(self, settings: Settings):
        self.llm = OpenAIChat(settings)

    async def stream(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.llm.stream(message, history or []):
            yield chunk

    @property
    def model_info(self) -> dict:
        return {"model": self.llm.model_name}
