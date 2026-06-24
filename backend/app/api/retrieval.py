"""Retrieval API — LangGraph hybrid search over indexed chunks."""

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.retrieval import RetrievalResult, RetrievalSearchRequest
from app.services.retrieval.graph import RetrievalGraphRunner

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


def get_retrieval_runner(settings: Settings = Depends(get_settings)) -> RetrievalGraphRunner:
    return RetrievalGraphRunner(settings)


@router.post("/search", response_model=RetrievalResult)
async def search_chunks(
    request: RetrievalSearchRequest,
    runner: RetrievalGraphRunner = Depends(get_retrieval_runner),
):
    """Hybrid search via LangGraph (dense + BM25 sparse → Qdrant RRF)."""
    try:
        return await runner.run(request.query, top_k=request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
