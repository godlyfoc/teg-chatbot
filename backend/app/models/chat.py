"""API request/response models."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    model: str
    retrieval_enabled: bool = True
    retrieval_engine: str = "langgraph"
    langsmith_tracing: bool = False
    langsmith_project: str | None = None
