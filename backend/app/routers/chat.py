from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.api_key import require_api_key
from app.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ollama_service import (
    OllamaResponseError,
    OllamaService,
    OllamaTimeoutError,
    OllamaUnavailableError,
)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_api_key)],
)


def get_ollama_service(request: Request) -> OllamaService:
    """Build an Ollama client from the active application settings."""

    settings: Settings = request.app.state.settings
    return OllamaService(
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> ChatResponse:
    """Send an authenticated chat prompt to the configured Ollama server."""

    try:
        answer = await ollama_service.generate(
            model=request.model,
            prompt=request.message,
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

    return ChatResponse(answer=answer)
