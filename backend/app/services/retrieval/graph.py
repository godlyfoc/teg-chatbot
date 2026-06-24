"""LangGraph retrieval pipeline — hybrid search orchestration."""

import logging
from functools import lru_cache
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.models.retrieval import RetrievedChunk, RetrievalResult
from app.services.language import detect_query_language
from app.services.retrieval.context import format_retrieval_context
from app.services.retrieval.retriever import Retriever
from app.services.retrieval.state import RetrievalGraphState

logger = logging.getLogger(__name__)


def _route_retrieval(state: RetrievalGraphState) -> Literal["retrieve", "__end__"]:
    if state.get("retrieval_enabled", True):
        return "retrieve"
    return "__end__"


def _detect_language_node(state: RetrievalGraphState) -> dict:
    """Detect query language with langdetect (en or ga)."""
    language = detect_query_language(state["query"])
    logger.info("Query language detected: %s", language)
    return {"query_language": language}


async def _retrieve_node(
    state: RetrievalGraphState,
    config: RunnableConfig,
) -> dict:
    """Embed query and run hybrid dense + sparse search in Qdrant."""
    configurable = config.get("configurable") or {}
    retriever: Retriever = configurable["retriever"]

    try:
        result = await retriever.retrieve(
            state["query"],
            top_k=state.get("top_k"),
        )
        return {
            "chunks": [chunk.model_dump() for chunk in result.chunks],
            "elapsed_seconds": result.elapsed_seconds,
            "error": None,
        }
    except Exception as exc:
        logger.exception("Retrieval graph node failed")
        return {
            "chunks": [],
            "elapsed_seconds": 0.0,
            "error": str(exc),
        }


def _format_context_node(
    state: RetrievalGraphState,
    config: RunnableConfig,
) -> dict:
    """Format retrieved chunks into LLM-ready context text."""
    configurable = config.get("configurable") or {}
    settings: Settings = configurable["settings"]

    chunks = [RetrievedChunk.model_validate(item) for item in state.get("chunks", [])]
    context = format_retrieval_context(
        chunks,
        max_chars=settings.retrieval_max_context_chars,
    )
    return {"context": context}


def build_retrieval_graph():
    """Build the LangGraph retrieval workflow."""
    graph = StateGraph(RetrievalGraphState)
    graph.add_node("detect_language", _detect_language_node)
    graph.add_node("retrieve", _retrieve_node)
    graph.add_node("format_context", _format_context_node)
    graph.add_edge(START, "detect_language")
    graph.add_conditional_edges(
        "detect_language",
        _route_retrieval,
        {"retrieve": "retrieve", "__end__": END},
    )
    graph.add_edge("retrieve", "format_context")
    graph.add_edge("format_context", END)
    return graph.compile()


@lru_cache
def get_retrieval_graph():
    return build_retrieval_graph()


class RetrievalGraphRunner:
    """Execute hybrid retrieval through a LangGraph workflow."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._graph = get_retrieval_graph()
        self._retriever = Retriever(self.settings)

    async def run(
        self,
        query: str,
        *,
        top_k: int | None = None,
        retrieval_enabled: bool | None = None,
    ) -> RetrievalResult:
        enabled = (
            self.settings.retrieval_enabled
            if retrieval_enabled is None
            else retrieval_enabled
        )

        final_state = await self._graph.ainvoke(
            {
                "query": query,
                "top_k": top_k,
                "retrieval_enabled": enabled,
                "query_language": "en",
                "chunks": [],
                "elapsed_seconds": 0.0,
                "error": None,
                "context": "",
            },
            config={
                "configurable": {
                    "settings": self.settings,
                    "retriever": self._retriever,
                }
            },
        )

        chunks = [RetrievedChunk.model_validate(item) for item in final_state.get("chunks", [])]
        if final_state.get("error"):
            logger.warning("Retrieval graph completed with error: %s", final_state["error"])

        return RetrievalResult(
            query=query,
            chunks=chunks,
            elapsed_seconds=final_state.get("elapsed_seconds", 0.0),
            query_language=final_state.get("query_language", "en"),
        )

    @property
    def retriever(self) -> Retriever:
        return self._retriever
