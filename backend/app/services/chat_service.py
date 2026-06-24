"""Chat business logic with LangGraph RAG retrieval."""

import logging
from collections.abc import AsyncGenerator

from app.config import Settings
from app.models.chat import ChatMessage
from app.models.retrieval import RetrievalResult
from app.services.language import detect_query_language
from app.services.llm.openai_provider import OpenAIChat
from app.services.retrieval.graph import RetrievalGraphRunner

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = OpenAIChat(settings)
        self.retrieval_graph = RetrievalGraphRunner(settings)

    async def retrieve(self, query: str) -> RetrievalResult:
        return await self.retrieval_graph.run(query)

    async def stream(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[str, None]:
        context_chunks = None
        query_language = detect_query_language(message)

        if self.settings.retrieval_enabled:
            try:
                result = await self.retrieval_graph.run(message)
                context_chunks = result.chunks
                query_language = result.query_language
                logger.info(
                    "LangGraph RAG: %d chunks (%.3fs), query_lang=%s",
                    len(context_chunks),
                    result.elapsed_seconds,
                    query_language,
                )
            except Exception:
                logger.exception("Retrieval graph failed — falling back to direct LLM response")

        async for chunk in self.llm.stream(
            message,
            history or [],
            context_chunks=context_chunks,
            query_language=query_language,
        ):
            yield chunk

    @property
    def model_info(self) -> dict:
        return {
            "model": self.llm.model_name,
            "retrieval_enabled": self.settings.retrieval_enabled,
            "retrieval_engine": "langgraph",
        }
