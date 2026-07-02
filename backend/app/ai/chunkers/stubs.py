from collections.abc import Mapping
from typing import Any

from app.ai.components import Chunk, ComponentNotImplementedError


class UnavailableChunker:
    """Chunker scaffold that fails explicitly until document chunking is wired."""

    async def chunk_text(
        self,
        text: str,
        settings: Mapping[str, Any],
    ) -> list[Chunk]:
        raise ComponentNotImplementedError(
            "Document chunking execution is not implemented in this phase."
        )

