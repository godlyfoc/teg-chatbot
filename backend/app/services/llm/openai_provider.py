"""OpenAI streaming chat client."""

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.config import Settings
from app.models.chat import ChatMessage
from app.models.retrieval import RetrievedChunk
from app.services.language import LanguageCode
from app.services.llm.prompts import build_system_message


class OpenAIChat:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def model_name(self) -> str:
        return self.settings.openai_model

    def _build_messages(
        self,
        message: str,
        history: list[ChatMessage],
        *,
        context_chunks: list[RetrievedChunk] | None = None,
        query_language: LanguageCode | None = None,
    ) -> list[dict]:
        messages = [
            {
                "role": "system",
                "content": build_system_message(
                    message,
                    context_chunks=context_chunks,
                    max_context_chars=self.settings.retrieval_max_context_chars,
                    query_language=query_language,
                ),
            }
        ]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})
        return messages

    async def stream(
        self,
        message: str,
        history: list[ChatMessage],
        *,
        context_chunks: list[RetrievedChunk] | None = None,
        query_language: LanguageCode | None = None,
    ) -> AsyncGenerator[str, None]:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=self._build_messages(
                message,
                history,
                context_chunks=context_chunks,
                query_language=query_language,
            ),
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            stream=True,
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
