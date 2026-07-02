from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.components import Chunk, ComponentNotImplementedError, RetrievedChunk


class UnavailableVectorStore:
    """Vector store scaffold that fails explicitly until persistence is wired."""

    async def upsert(
        self,
        collection: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
        metadata: Mapping[str, Any],
    ) -> None:
        raise ComponentNotImplementedError(
            "Vector store persistence is not implemented in this phase."
        )

    async def query(
        self,
        collection: str,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        raise ComponentNotImplementedError(
            "Vector store queries are not implemented in this phase."
        )

    async def get_collection_metadata(
        self,
        collection: str,
    ) -> Mapping[str, Any]:
        raise ComponentNotImplementedError(
            "Vector store metadata is not implemented in this phase."
        )

