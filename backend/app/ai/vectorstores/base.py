from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.ai.components import Chunk, RetrievedChunk


@dataclass(frozen=True)
class VectorStoreHealth:
    """Readiness metadata for one vector store backend adapter."""

    id: str
    label: str
    available: bool
    implemented: bool
    source: str
    mode: str
    description: str
    checks: list[dict[str, Any]]


@runtime_checkable
class VectorStoreBackend(Protocol):
    """Shared contract for vector store adapters used by documents and RAG."""

    backend_id: str
    label: str

    @staticmethod
    def collection_id(
        conversation_id: str,
        embedder_model: str,
        vector_database: str,
    ) -> str:
        """Return a deterministic collection id for this backend."""

    async def upsert(
        self,
        collection: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
        metadata: Mapping[str, Any],
    ) -> None:
        """Insert or replace vectors for a collection."""

    async def query(
        self,
        collection: str,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Return nearest chunks for one collection."""

    async def get_collection_metadata(
        self,
        collection: str,
    ) -> Mapping[str, Any]:
        """Return metadata for one collection."""

    async def list_collections(self, conversation_id: str) -> list[dict[str, Any]]:
        """List collections for one conversation."""

    async def delete_collection(
        self,
        conversation_id: str,
        collection_id: str,
    ) -> bool:
        """Delete one collection."""

    async def export_collection(
        self,
        conversation_id: str,
        collection_id: str,
    ) -> dict[str, Any]:
        """Return a portable collection payload including vectors."""

    async def import_collection(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Import a portable collection payload and return collection metadata."""

    def collection_ref(self, conversation_id: str, collection_id: str) -> str:
        """Return an adapter-specific collection reference."""

    def health(self) -> VectorStoreHealth:
        """Return local adapter availability metadata."""
