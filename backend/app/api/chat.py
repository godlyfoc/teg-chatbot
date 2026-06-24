"""Chat API — health check and streaming chat."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.models.chat import ChatRequest, HealthResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api", tags=["chat"])


def get_chat_service(settings: Settings = Depends(get_settings)) -> ChatService:
    return ChatService(settings)


@router.get("/health", response_model=HealthResponse)
async def health_check(chat_service: ChatService = Depends(get_chat_service)):
    info = chat_service.model_info
    return HealthResponse(
        status="ok",
        model=info["model"],
        retrieval_enabled=info.get("retrieval_enabled", True),
        retrieval_engine=info.get("retrieval_engine", "langgraph"),
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    async def event_generator():
        try:
            async for chunk in chat_service.stream(request.message, request.history):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
