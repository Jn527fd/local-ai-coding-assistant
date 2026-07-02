from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.components import ComponentNotImplementedError, RetrievedChunk


class UnavailableReranker:
    """Explicit placeholder used when a reranker adapter has no implementation."""

    async def rerank(
        self,
        query: str,
        candidate_chunks: Sequence[RetrievedChunk],
        model: str,
        settings: Mapping[str, Any],
    ) -> list[RetrievedChunk]:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for this reranker."
        )

