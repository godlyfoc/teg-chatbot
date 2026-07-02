"""Chat business logic with LangGraph RAG retrieval."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.config import Settings
from app.models.chat import ChatMessage
from app.models.retrieval import RetrievalResult
from app.services.rag.pipeline import RAGPipeline
from app.services.retrieval.graph import RetrievalGraphRunner

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.rag_pipeline = RAGPipeline(settings)
        self.retrieval_graph = RetrievalGraphRunner(settings)

    async def retrieve(self, query: str) -> RetrievalResult:
        return await self.retrieval_graph.run(query)

    async def stream(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        async for event in self.rag_pipeline.stream_execute(message, history or []):
            yield event

    @property
    def model_info(self) -> dict:
        from app.observability.langsmith import is_langsmith_enabled

        return {
            "model": self.rag_pipeline.llm.model_name,
            "retrieval_enabled": self.settings.retrieval_enabled,
            "retrieval_engine": "langgraph+cohere-rerank",
            "retrieval_candidate_k": self.settings.retrieval_candidate_k,
            "retrieval_rerank_top_k": self.settings.retrieval_rerank_top_k,
            "validation_max_retries": self.settings.validation_max_retries,
            "langsmith_tracing": is_langsmith_enabled(self.settings),
            "langsmith_project": self.settings.langsmith_project
            if is_langsmith_enabled(self.settings)
            else None,
        }
