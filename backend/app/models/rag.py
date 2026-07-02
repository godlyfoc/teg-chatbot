"""RAG pipeline models."""

from pydantic import BaseModel, Field

from app.models.retrieval import RetrievedChunk


class Citation(BaseModel):
    title: str
    url: str


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)


class RAGRequestLog(BaseModel):
    query: str
    detected_language: str
    retrieved_documents: list[dict] = Field(default_factory=list)
    reranked_documents: list[dict] = Field(default_factory=list)
    final_context: str = ""
    generated_response: str = ""
    validation_result: str = "skipped"
    validation_errors: list[str] = Field(default_factory=list)
    regeneration_attempts: int = 0
    fallback_returned: bool = False


class RAGPipelineResult(BaseModel):
    response: str
    citations: list[Citation] = Field(default_factory=list)
    is_fallback: bool = False
    validation_passed: bool = True
    regeneration_attempts: int = 0
    context_chunks: list[RetrievedChunk] = Field(default_factory=list)
    log: RAGRequestLog
