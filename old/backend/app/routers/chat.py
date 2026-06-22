from dataclasses import dataclass
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.api_key import require_api_key
from app.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.model_manager import (
    ModelManager,
)
from app.services.ollama_service import (
    OllamaResponseError,
    OllamaService,
    OllamaTimeoutError,
    OllamaUnavailableError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_api_key)],
)


@dataclass(frozen=True)
class ChatPrompt:
    text: str
    included_history_messages: int


def build_chat_prompt(
    chat_request: ChatRequest,
    max_chars: int,
) -> ChatPrompt:
    """Build a recent-context prompt that stays within a bounded size."""

    if not chat_request.history:
        return ChatPrompt(
            text=chat_request.message,
            included_history_messages=0,
        )

    prefix = (
        "Continue the conversation below. Follow the latest user request.\n\n"
    )
    suffix = f"\n\nUser: {chat_request.message}\nAssistant:"
    available_chars = max(0, max_chars - len(prefix) - len(suffix))
    selected_lines: list[str] = []

    for item in reversed(chat_request.history):
        role = "User" if item.role == "user" else "Assistant"
        line = f"{role}: {item.content}"
        line_cost = len(line) + (1 if selected_lines else 0)

        if line_cost <= available_chars:
            selected_lines.append(line)
            available_chars -= line_cost
            continue

        if not selected_lines and available_chars > len(role) + 20:
            marker = "\n[message truncated]"
            content_chars = available_chars - len(role) - 2 - len(marker)
            selected_lines.append(
                f"{role}: {item.content[:content_chars]}{marker}"
            )
        break

    selected_lines.reverse()
    text = prefix + "\n".join(selected_lines) + suffix
    return ChatPrompt(
        text=text,
        included_history_messages=len(selected_lines),
    )


def get_ollama_service(request: Request) -> OllamaService:
    """Build an Ollama client from the active application settings."""

    settings: Settings = request.app.state.settings
    return OllamaService(
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.ollama_timeout_seconds,
        num_predict=settings.ollama_num_predict,
        think=settings.ollama_think,
        keep_alive=settings.ollama_keep_alive,
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
        if chat_request.model != active_model:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{chat_request.model} is not active. Switch models from "
                    "the account panel before using it."
                ),
            )

    settings: Settings = request.app.state.settings
    prompt = build_chat_prompt(
        chat_request,
        max_chars=settings.chat_context_max_chars,
    )
    logger.info(
        "Sending chat to Ollama model=%s prompt_chars=%d history_messages=%d/%d",
        active_model,
        len(prompt.text),
        prompt.included_history_messages,
        len(chat_request.history),
    )

    try:
        answer = await ollama_service.generate(
            model=active_model,
            prompt=prompt.text,
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
