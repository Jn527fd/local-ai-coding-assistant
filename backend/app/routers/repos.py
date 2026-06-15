from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.auth.api_key import require_api_key
from app.config import Settings
from app.rag.retriever import build_rag_prompt, retrieve_relevant_chunks
from app.schemas.repos import (
    AskRepositoryRequest,
    AskRepositoryResponse,
    IndexLocalRepositoryRequest,
    IndexLocalRepositoryResponse,
)
from app.services.repo_service import (
    InvalidRepositoryPathError,
    RepositoryAccessError,
    RepositoryIndexNotFoundError,
    RepositoryIndexReadError,
    RepositoryIndexWriteError,
    RepositoryService,
)
from app.services.ollama_service import (
    OllamaResponseError,
    OllamaService,
    OllamaTimeoutError,
    OllamaUnavailableError,
)
from app.services.model_manager import ModelManager

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


def get_ollama_service(request: Request) -> OllamaService:
    """Build an Ollama client from the active application settings."""

    settings: Settings = request.app.state.settings
    return OllamaService(
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.ollama_timeout_seconds,
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
    http_request: Request,
    repository_service: Annotated[
        RepositoryService,
        Depends(get_repository_service),
    ],
    ollama_service: Annotated[
        OllamaService,
        Depends(get_ollama_service),
    ],
) -> AskRepositoryResponse:
    """Answer a question using relevant chunks from a repository index."""

    try:
        index_data = await run_in_threadpool(
            repository_service.load_index,
            request.repo_name,
        )
    except RepositoryIndexNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RepositoryIndexReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    settings: Settings = http_request.app.state.settings
    model_manager: ModelManager = http_request.app.state.model_manager
    if model_manager.is_switching:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model switching is in progress. Try again when it completes.",
        )

    retrieved_chunks = retrieve_relevant_chunks(
        index_data=index_data,
        question=request.question,
        limit=settings.rag_top_k,
    )
    prompt = build_rag_prompt(
        repo_name=request.repo_name,
        question=request.question,
        chunks=retrieved_chunks,
    )

    try:
        answer = await ollama_service.generate(
            model=model_manager.active_model,
            prompt=prompt,
        )
    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OllamaTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except OllamaResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    sources = list(dict.fromkeys(chunk.file_path for chunk in retrieved_chunks))
    return AskRepositoryResponse(answer=answer, sources=sources)
