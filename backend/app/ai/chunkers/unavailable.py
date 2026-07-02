from collections.abc import Mapping
from typing import Any

from app.ai.components import Chunk, ComponentNotImplementedError


class UnavailableChunker:
    """Explicit placeholder used when a chunker adapter has no implementation."""

    async def chunk_text(
        self,
        text: str,
        settings: Mapping[str, Any],
    ) -> list[Chunk]:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for this chunker."
        )

