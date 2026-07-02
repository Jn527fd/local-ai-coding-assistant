from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.components import ComponentUnavailableError
from app.services.ollama_service import OllamaService


class OllamaLLMProvider:
    """LLM provider adapter backed by the existing Ollama service."""

    def __init__(self, ollama_service: OllamaService) -> None:
        self.ollama_service = ollama_service

    async def generate(
        self,
        prompt: str,
        history: Sequence[Mapping[str, str]],
        settings: Mapping[str, Any],
    ) -> str:
        model = settings.get("model") or settings.get("llmModel")
        if not isinstance(model, str) or not model.strip():
            raise ComponentUnavailableError(
                "Ollama LLM generation requires a resolved model."
            )
        return await self.ollama_service.generate(
            model=model.strip(),
            prompt=prompt,
        )

