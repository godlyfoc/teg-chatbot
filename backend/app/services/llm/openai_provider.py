"""OpenAI streaming chat client."""

from collections.abc import AsyncGenerator

from langsmith import traceable
from openai import AsyncOpenAI
from langsmith import wrappers

from app.config import Settings
from app.models.chat import ChatMessage
from app.models.retrieval import RetrievedChunk
from app.observability.langsmith import is_langsmith_enabled
from app.services.language import LanguageCode
from app.services.llm.prompts import build_system_message


class OpenAIChat:
    def __init__(self, settings: Settings):
        self.settings = settings
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.client = wrappers.wrap_openai(client) if is_langsmith_enabled(settings) else client

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

    def _build_rag_messages(
        self,
        message: str,
        history: list[ChatMessage],
        *,
        system_message: str,
        extra_messages: list[dict] | None = None,
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": system_message}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})
        if extra_messages:
            messages.extend(extra_messages)
        return messages

    async def generate(
        self,
        message: str,
        history: list[ChatMessage],
        *,
        system_message: str,
        extra_messages: list[dict] | None = None,
        temperature: float | None = None,
    ) -> str:
        messages = self._build_rag_messages(
            message,
            history,
            system_message=system_message,
            extra_messages=extra_messages,
        )
        request_kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.settings.max_tokens,
            "temperature": temperature if temperature is not None else self.settings.rag_temperature,
        }
        if is_langsmith_enabled(self.settings):
            request_kwargs["langsmith_extra"] = {
                "metadata": {"mode": "rag_generate"},
            }
        response = await self.client.chat.completions.create(**request_kwargs)
        return (response.choices[0].message.content or "").strip()

    async def translate(
        self,
        text: str,
        target_language: LanguageCode,
    ) -> str:
        if target_language not in ("en", "ga"):
            return text
        target_label = "English" if target_language == "en" else "Irish (Gaeilge)"
        request_kwargs: dict = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Translate the user's message into {target_label}. "
                        "Preserve markdown formatting, links, citation markers like [1], "
                        "and the ### Sources section if present. Return only the translation."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "max_tokens": self.settings.max_tokens,
            "temperature": 0.1,
        }
        if is_langsmith_enabled(self.settings):
            request_kwargs["langsmith_extra"] = {
                "metadata": {"mode": "translate", "target_language": target_language},
            }
        response = await self.client.chat.completions.create(**request_kwargs)
        return (response.choices[0].message.content or text).strip()

    async def generate_stream(
        self,
        message: str,
        history: list[ChatMessage],
        *,
        system_message: str,
        extra_messages: list[dict] | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        messages = self._build_rag_messages(
            message,
            history,
            system_message=system_message,
            extra_messages=extra_messages,
        )
        request_kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.settings.max_tokens,
            "temperature": temperature if temperature is not None else self.settings.rag_temperature,
            "stream": True,
        }
        if is_langsmith_enabled(self.settings):
            request_kwargs["langsmith_extra"] = {
                "metadata": {"mode": "rag_generate_stream"},
            }
        response = await self.client.chat.completions.create(**request_kwargs)
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def stream(
        self,
        message: str,
        history: list[ChatMessage],
        *,
        context_chunks: list[RetrievedChunk] | None = None,
        query_language: LanguageCode | None = None,
    ) -> AsyncGenerator[str, None]:
        messages = self._build_messages(
            message,
            history,
            context_chunks=context_chunks,
            query_language=query_language,
        )
        request_kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.settings.max_tokens,
            "temperature": self.settings.temperature,
            "stream": True,
        }
        if is_langsmith_enabled(self.settings):
            request_kwargs["langsmith_extra"] = {
                "metadata": {
                    "retrieval_chunks": len(context_chunks or []),
                    "query_language": query_language or "unknown",
                }
            }
        response = await self.client.chat.completions.create(**request_kwargs)
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
