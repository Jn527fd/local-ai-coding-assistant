from __future__ import annotations

from pathlib import Path

from app.ai.vectorstores.base import VectorStoreBackend, VectorStoreHealth
from app.ai.vectorstores.chroma import ChromaVectorStore
from app.ai.vectorstores.json_store import JsonVectorStore


class VectorStoreManager:
    """Select and report health for vector store adapters."""

    def __init__(
        self,
        index_directory: Path,
        backend: str = "json",
    ) -> None:
        self.index_directory = index_directory.expanduser().resolve()
        self.backend = (backend or "json").strip().lower()
        self.json_store = JsonVectorStore(self.index_directory)
        self.chroma_store = ChromaVectorStore(self.index_directory / "chroma")

    def default_store(self) -> VectorStoreBackend:
        """Return the configured active backend, falling back to JSON."""

        if self.backend == "chroma" and self.chroma_store.health().available:
            return self.chroma_store
        return self.json_store

    def store_for_selection(self, vector_database: str | None) -> VectorStoreBackend:
        """Return an adapter for a selected vector database when available."""

        selected = (vector_database or "").strip().lower()
        if selected == "chroma" and self.backend == "chroma":
            return self.default_store()
        return self.json_store

    def health(self) -> list[VectorStoreHealth]:
        return [self.json_store.health(), self.chroma_store.health()]
