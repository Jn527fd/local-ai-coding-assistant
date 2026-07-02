from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.components import ComponentNotImplementedError, RetrievedChunk


class UnavailableReranker:
    """Reranker scaffold that fails explicitly until reranking is wired."""

    async def rerank(
        self,
        query: str,
        candidate_chunks: Sequence[RetrievedChunk],
        model: str,
        settings: Mapping[str, Any],
    ) -> list[RetrievedChunk]:
        raise ComponentNotImplementedError(
            "Reranking execution is not implemented in this phase."
        )
