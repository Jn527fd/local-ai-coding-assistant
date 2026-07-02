from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.components import Chunk, ComponentNotImplementedError, RetrievedChunk


class UnavailableVectorStore:
    """Explicit placeholder used when a vector store adapter has no implementation."""

    async def upsert(
        self,
        collection: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
        metadata: Mapping[str, Any],
    ) -> None:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for vector store persistence."
        )

    async def query(
        self,
        collection: str,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for vector store queries."
        )

    async def get_collection_metadata(
        self,
        collection: str,
    ) -> Mapping[str, Any]:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for vector store metadata."
        )

