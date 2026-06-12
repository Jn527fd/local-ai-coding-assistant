from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.api_key import require_api_key
from app.schemas.repos import (
    AskRepositoryRequest,
    AskRepositoryResponse,
    IndexLocalRepositoryRequest,
    IndexLocalRepositoryResponse,
)

router = APIRouter(
    prefix="/repos",
    tags=["repositories"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/index-local", response_model=IndexLocalRepositoryResponse)
async def index_local_repository(
    request: IndexLocalRepositoryRequest,
) -> IndexLocalRepositoryResponse:
    """Accept an authenticated request for the upcoming repository indexer."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Local repository indexing will be implemented in Phase 5.",
    )


@router.post("/ask", response_model=AskRepositoryResponse)
async def ask_repository(
    request: AskRepositoryRequest,
) -> AskRepositoryResponse:
    """Accept an authenticated request for the upcoming repository RAG flow."""

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Repository questions will be implemented in Phase 6.",
    )
