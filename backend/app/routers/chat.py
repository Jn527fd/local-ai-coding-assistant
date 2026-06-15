from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.api_key import require_api_key
from app.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.model_manager import (
    ModelManager,
    UnsupportedModelError,
)
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


def build_chat_prompt(chat_request: ChatRequest) -> str:
    """Build a prompt containing only the selected browser chat context."""

    if not chat_request.history:
        return chat_request.message

    conversation_lines = [
        "Continue the conversation below. Follow the latest user request.",
        "",
    ]
    for item in chat_request.history:
        role = "User" if item.role == "user" else "Assistant"
        conversation_lines.append(f"{role}: {item.content}")
    conversation_lines.extend(["", f"User: {chat_request.message}", "Assistant:"])
    return "\n".join(conversation_lines)


def get_ollama_service(request: Request) -> OllamaService:
    """Build an Ollama client from the active application settings."""

    settings: Settings = request.app.state.settings
    return OllamaService(
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    request: Request,
    ollama_service: Annotated[OllamaService, Depends(get_ollama_service)],
) -> ChatResponse:
    """Send an authenticated chat prompt to the configured Ollama server."""

    model_manager: ModelManager = request.app.state.model_manager
    if model_manager.is_switching:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model switching is in progress. Try again when it completes.",
        )

    active_model = model_manager.active_model

    if chat_request.model is not None:
        try:
            model_manager.validate_model(chat_request.model)
        except UnsupportedModelError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        if chat_request.model != active_model:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{chat_request.model} is not active. Switch models from "
                    "the account panel before using it."
                ),
            )

    try:
        answer = await ollama_service.generate(
            model=active_model,
            prompt=build_chat_prompt(chat_request),
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

    return ChatResponse(model=active_model, answer=answer)
