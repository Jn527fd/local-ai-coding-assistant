from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.auth.api_key import require_api_key
from app.config import Settings
from app.schemas.repos import (
    AskRepositoryRequest,
    AskRepositoryResponse,
    IndexLocalRepositoryRequest,
    IndexLocalRepositoryResponse,
)
from app.services.repo_service import (
    InvalidRepositoryPathError,
    RepositoryAccessError,
    RepositoryIndexWriteError,
    RepositoryService,
)

router = APIRouter(
    prefix="/repos",
    tags=["repositories"],
    dependencies=[Depends(require_api_key)],
)


def get_repository_service(request: Request) -> RepositoryService:
    """Build a repository service from the active application settings."""

    settings: Settings = request.app.state.settings
    return RepositoryService(
        index_directory=settings.index_directory,
        chunk_size=settings.repo_chunk_size,
    )


@router.post("/index-local", response_model=IndexLocalRepositoryResponse)
async def index_local_repository(
    request: IndexLocalRepositoryRequest,
    repository_service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
) -> IndexLocalRepositoryResponse:
    """Index supported files from a local repository into JSON."""

    try:
        result = await run_in_threadpool(
            repository_service.index_local,
            request.path,
        )
    except InvalidRepositoryPathError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RepositoryAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except RepositoryIndexWriteError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return IndexLocalRepositoryResponse(
        repo_name=result.repo_name,
        indexed_files=result.indexed_files,
        indexed_chunks=result.indexed_chunks,
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
