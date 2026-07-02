from collections.abc import Sequence

from app.ai.components import ComponentUnavailableError
from app.services.ollama_service import OllamaService


class OllamaEmbedderProvider:
    """Embedder provider adapter backed by Ollama's local embedding API."""

    def __init__(self, ollama_service: OllamaService) -> None:
        self.ollama_service = ollama_service

    async def embed_texts(
        self,
        texts: Sequence[str],
        model: str,
    ) -> list[list[float]]:
        if not model.strip():
            raise ComponentUnavailableError(
                "Ollama embeddings require a resolved embedding model."
            )
        return await self.ollama_service.embed_texts(
            texts=list(texts),
            model=model.strip(),
        )

