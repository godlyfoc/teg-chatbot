"""End-to-end RAG pipeline: retrieve, rerank, generate, validate, fallback."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from langsmith import traceable

from app.config import Settings
from app.models.chat import ChatMessage
from app.models.rag import RAGPipelineResult, RAGRequestLog
from app.models.retrieval import RetrievedChunk
from app.services.language import LanguageCode, detect_query_language
from app.services.llm.openai_provider import OpenAIChat
from app.services.observability.rag_logger import log_rag_request
from app.services.rag.conversational import (
    build_conversational_system_message,
    is_conversational_query,
)
from app.services.rag.formatting import format_response_for_display
from app.services.rag.messages import fallback_message
from app.services.rag.prompts import build_rag_system_message, build_regeneration_message
from app.services.rag.response_language import ensure_response_language
from app.services.retrieval.context import format_retrieval_context
from app.services.retrieval.graph import RetrievalGraphRunner
from app.services.validation.validator import ResponseValidator, extract_citations

logger = logging.getLogger(__name__)


async def _yield_text_stream(text: str) -> AsyncGenerator[dict[str, Any], None]:
    """Stream pre-built text to the client in small chunks."""
    if not text:
        return
    words = text.split(" ")
    for index, word in enumerate(words):
        chunk = word if index == len(words) - 1 else f"{word} "
        yield {"content": chunk}
        await asyncio.sleep(0)


def _chunk_summary(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "title": chunk.title,
            "source_url": chunk.source_url,
            "score": chunk.score,
            "language": chunk.language,
        }
        for chunk in chunks
    ]


class RAGPipeline:
    """Orchestrate retrieval, generation, validation, and fallback behaviour."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = OpenAIChat(settings)
        self.retrieval_graph = RetrievalGraphRunner(settings)
        self.validator = ResponseValidator(settings)

    async def _apply_response_language(
        self,
        text: str,
        query_language: LanguageCode,
    ) -> str:
        return await ensure_response_language(
            text,
            query_language,
            translate=self.llm.translate,
        )

    @traceable(name="teg_rag_pipeline", run_type="chain")
    async def execute(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> RAGPipelineResult:
        history = history or []
        query_language: LanguageCode = detect_query_language(message)
        log_record = RAGRequestLog(
            query=message,
            detected_language=query_language,
        )

        if is_conversational_query(message):
            return await self._execute_conversational(message, history, query_language, log_record)

        if not self.settings.retrieval_enabled:
            return self._finalize_fallback(query_language, log_record, reason="retrieval_disabled")

        try:
            retrieval = await self.retrieval_graph.run(message)
            log_record.retrieved_documents = _chunk_summary(retrieval.candidate_chunks)
            log_record.reranked_documents = _chunk_summary(retrieval.chunks)
        except Exception:
            logger.exception("Retrieval pipeline failed")
            return self._finalize_fallback(query_language, log_record, reason="retrieval_error")

        if not retrieval.chunks:
            return self._finalize_fallback(query_language, log_record, reason="no_relevant_chunks")

        context_chunks = retrieval.chunks
        context_text = retrieval.context or format_retrieval_context(
            context_chunks,
            max_chars=self.settings.retrieval_max_context_chars,
        )
        log_record.final_context = context_text

        system_message = build_rag_system_message(
            context_chunks=context_chunks,
            max_context_chars=self.settings.retrieval_max_context_chars,
            query_language=query_language,  # type: ignore[arg-type]
        )

        extra_messages: list[dict] = []
        attempts = 0
        max_attempts = self.settings.validation_max_retries + 1
        last_response = ""
        last_validation_errors: list[str] = []

        while attempts < max_attempts:
            response = await self.llm.generate(
                message,
                history,
                system_message=system_message,
                extra_messages=extra_messages or None,
            )
            last_response = response
            validation = await self.validator.validate(
                response=response,
                context_chunks=context_chunks,
                context_text=context_text,
                query_language=query_language,  # type: ignore[arg-type]
            )

            if validation.passed:
                display_response = format_response_for_display(
                    response,
                    query_language,  # type: ignore[arg-type]
                )
                display_response = await self._apply_response_language(
                    display_response,
                    query_language,  # type: ignore[arg-type]
                )
                log_record.generated_response = display_response
                log_record.validation_result = "pass"
                log_record.regeneration_attempts = attempts
                log_record.fallback_returned = False
                log_rag_request(log_record, self.settings)
                return RAGPipelineResult(
                    response=display_response,
                    citations=extract_citations(response),
                    is_fallback=False,
                    validation_passed=True,
                    regeneration_attempts=attempts,
                    context_chunks=context_chunks,
                    log=log_record,
                )

            last_validation_errors = validation.errors
            attempts += 1
            logger.warning(
                "Validation failed (attempt %d/%d): %s",
                attempts,
                max_attempts,
                "; ".join(validation.errors),
            )
            if attempts < max_attempts:
                extra_messages = [
                    {"role": "assistant", "content": response},
                    {
                        "role": "user",
                        "content": build_regeneration_message(
                            validation.errors,
                            query_language,  # type: ignore[arg-type]
                        ),
                    },
                ]

        log_record.generated_response = last_response
        log_record.validation_result = "fail"
        log_record.validation_errors = last_validation_errors
        log_record.regeneration_attempts = attempts
        return self._finalize_fallback(
            query_language,
            log_record,
            reason="validation_failed",
            attempted_response=last_response,
        )

    async def stream_execute(
        self,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream generation tokens live, then validate and finalize."""
        history = history or []
        query_language: LanguageCode = detect_query_language(message)
        log_record = RAGRequestLog(
            query=message,
            detected_language=query_language,
        )

        if is_conversational_query(message):
            async for event in self._stream_conversational(message, history, query_language, log_record):
                yield event
            return

        if not self.settings.retrieval_enabled:
            async for event in self._stream_fallback(query_language, log_record, reason="retrieval_disabled"):
                yield event
            return

        try:
            retrieval = await self.retrieval_graph.run(message)
            log_record.retrieved_documents = _chunk_summary(retrieval.candidate_chunks)
            log_record.reranked_documents = _chunk_summary(retrieval.chunks)
        except Exception:
            logger.exception("Retrieval pipeline failed")
            async for event in self._stream_fallback(query_language, log_record, reason="retrieval_error"):
                yield event
            return

        if not retrieval.chunks:
            async for event in self._stream_fallback(query_language, log_record, reason="no_relevant_chunks"):
                yield event
            return

        context_chunks = retrieval.chunks
        context_text = retrieval.context or format_retrieval_context(
            context_chunks,
            max_chars=self.settings.retrieval_max_context_chars,
        )
        log_record.final_context = context_text

        system_message = build_rag_system_message(
            context_chunks=context_chunks,
            max_context_chars=self.settings.retrieval_max_context_chars,
            query_language=query_language,  # type: ignore[arg-type]
        )

        extra_messages: list[dict] = []
        attempts = 0
        max_attempts = self.settings.validation_max_retries + 1
        last_response = ""
        last_validation_errors: list[str] = []

        while attempts < max_attempts:
            accumulated = ""
            async for token in self.llm.generate_stream(
                message,
                history,
                system_message=system_message,
                extra_messages=extra_messages or None,
            ):
                accumulated += token

            last_response = accumulated
            validation = await self.validator.validate(
                response=accumulated,
                context_chunks=context_chunks,
                context_text=context_text,
                query_language=query_language,  # type: ignore[arg-type]
            )

            if validation.passed:
                display_response = format_response_for_display(
                    accumulated,
                    query_language,  # type: ignore[arg-type]
                )
                display_response = await self._apply_response_language(
                    display_response,
                    query_language,  # type: ignore[arg-type]
                )
                async for event in _yield_text_stream(display_response):
                    yield event
                log_record.generated_response = display_response
                log_record.validation_result = "pass"
                log_record.regeneration_attempts = attempts
                log_record.fallback_returned = False
                log_rag_request(log_record, self.settings)
                return

            last_validation_errors = validation.errors
            attempts += 1
            logger.warning(
                "Validation failed during stream (attempt %d/%d): %s",
                attempts,
                max_attempts,
                "; ".join(validation.errors),
            )
            if attempts < max_attempts:
                extra_messages = [
                    {"role": "assistant", "content": accumulated},
                    {
                        "role": "user",
                        "content": build_regeneration_message(
                            validation.errors,
                            query_language,  # type: ignore[arg-type]
                        ),
                    },
                ]
                continue

        log_record.generated_response = last_response
        log_record.validation_result = "fail"
        log_record.validation_errors = last_validation_errors
        log_record.regeneration_attempts = attempts
        async for event in self._stream_fallback(
            query_language,
            log_record,
            reason="validation_failed",
            attempted_response=last_response,
        ):
            yield event

    async def _execute_conversational(
        self,
        message: str,
        history: list[ChatMessage],
        query_language: LanguageCode,
        log_record: RAGRequestLog,
    ) -> RAGPipelineResult:
        system_message = build_conversational_system_message(query_language)
        response = await self.llm.generate(
            message,
            history,
            system_message=system_message,
            temperature=self.settings.temperature,
        )
        response = await self._apply_response_language(response, query_language)
        log_record.generated_response = response
        log_record.validation_result = "skipped"
        log_record.regeneration_attempts = 0
        log_record.fallback_returned = False
        log_rag_request(log_record, self.settings)
        logger.info("Conversational response (no RAG) for: %s", message[:40])
        return RAGPipelineResult(
            response=response,
            citations=[],
            is_fallback=False,
            validation_passed=True,
            regeneration_attempts=0,
            context_chunks=[],
            log=log_record,
        )

    async def _stream_conversational(
        self,
        message: str,
        history: list[ChatMessage],
        query_language: LanguageCode,
        log_record: RAGRequestLog,
    ) -> AsyncGenerator[dict[str, Any], None]:
        system_message = build_conversational_system_message(query_language)
        accumulated = ""
        async for token in self.llm.generate_stream(
            message,
            history,
            system_message=system_message,
            temperature=self.settings.temperature,
        ):
            accumulated += token
        final_response = await self._apply_response_language(accumulated, query_language)
        async for event in _yield_text_stream(final_response):
            yield event
        log_record.generated_response = final_response
        log_record.validation_result = "skipped"
        log_record.regeneration_attempts = 0
        log_record.fallback_returned = False
        log_rag_request(log_record, self.settings)
        logger.info("Conversational stream (no RAG) for: %s", message[:40])

    async def _stream_fallback(
        self,
        query_language: LanguageCode,
        log_record: RAGRequestLog,
        *,
        reason: str,
        attempted_response: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        self._finalize_fallback(
            query_language,
            log_record,
            reason=reason,
            attempted_response=attempted_response,
        )
        response = fallback_message(query_language)
        for token in response.split(" "):
            yield {"content": f"{token} "}
            await asyncio.sleep(0)

    def _finalize_fallback(
        self,
        query_language: LanguageCode,
        log_record: RAGRequestLog,
        *,
        reason: str,
        attempted_response: str = "",
    ) -> RAGPipelineResult:
        response = fallback_message(query_language)
        log_record.generated_response = attempted_response or response
        log_record.validation_result = "fail" if reason == "validation_failed" else "skipped"
        log_record.fallback_returned = True
        log_record.regeneration_attempts = log_record.regeneration_attempts or 0
        logger.info("Returning fallback response (%s)", reason)
        log_rag_request(log_record, self.settings)
        return RAGPipelineResult(
            response=response,
            citations=[],
            is_fallback=True,
            validation_passed=False,
            regeneration_attempts=log_record.regeneration_attempts,
            context_chunks=[],
            log=log_record,
        )
