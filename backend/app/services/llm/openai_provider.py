"""OpenAI streaming provider."""

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.models.chat import ChatMessage
from app.services.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, settings):
        super().__init__(settings)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.settings.openai_model

    def _build_messages(self, message: str, history: list[ChatMessage]) -> list[dict]:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant for a website chatbot. "
                    "Answer questions clearly and concisely."
                ),
            }
        ]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})
        return messages

    async def stream(
        self, message: str, history: list[ChatMessage]
    ) -> AsyncGenerator[str, None]:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=self._build_messages(message, history),
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
