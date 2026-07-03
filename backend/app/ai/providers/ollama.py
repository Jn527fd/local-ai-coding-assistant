from collections.abc import AsyncIterator, Mapping, Sequence
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
        images = settings.get("images")
        image_payloads = images if isinstance(images, list) else None
        if not image_payloads:
            return await self.ollama_service.generate(
                model=model.strip(),
                prompt=prompt,
            )
        return await self.ollama_service.generate(
            model=model.strip(),
            prompt=prompt,
            images=image_payloads,
        )

    async def stream_generate(
        self,
        prompt: str,
        history: Sequence[Mapping[str, str]],
        settings: Mapping[str, Any],
    ) -> AsyncIterator[str]:
        """Stream text chunks when the underlying Ollama service supports it."""

        model = settings.get("model") or settings.get("llmModel")
        if not isinstance(model, str) or not model.strip():
            raise ComponentUnavailableError(
                "Ollama streaming requires a resolved model."
            )
        images = settings.get("images")
        image_payloads = images if isinstance(images, list) else None
        stream_generate = getattr(self.ollama_service, "stream_generate", None)
        if callable(stream_generate):
            async for chunk in stream_generate(
                model=model.strip(),
                prompt=prompt,
                images=image_payloads if image_payloads else None,
            ):
                yield chunk
            return

        answer = await self.generate(prompt, history, settings)
        if answer:
            yield answer
