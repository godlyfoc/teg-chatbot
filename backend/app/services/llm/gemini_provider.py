"""Gemini streaming provider."""

from collections.abc import AsyncGenerator

import google.generativeai as genai

from app.models.chat import ChatMessage
from app.services.llm.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(self, settings):
        super().__init__(settings)
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.settings.gemini_model

    def _build_prompt(self, message: str, history: list[ChatMessage]) -> str:
        lines = [
            "You are a helpful AI assistant for a website chatbot. "
            "Answer questions clearly and concisely.\n"
        ]
        for msg in history:
            role = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role}: {msg.content}")
        lines.append(f"User: {message}")
        lines.append("Assistant:")
        return "\n".join(lines)

    async def stream(
        self, message: str, history: list[ChatMessage]
    ) -> AsyncGenerator[str, None]:
        prompt = self._build_prompt(message, history)
        response = await self.model.generate_content_async(prompt, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text
