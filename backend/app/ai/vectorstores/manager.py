from __future__ import annotations

from pathlib import Path
from typing import Any

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

    def store_by_id(self, backend_id: str | None) -> VectorStoreBackend:
        selected = (backend_id or self.default_store().backend_id).strip().lower()
        if selected == "json":
            return self.json_store
        if selected == "chroma" and self.chroma_store.health().available:
            return self.chroma_store
        return self.json_store

    def health(self) -> list[VectorStoreHealth]:
        return [
            self.json_store.health(),
            self.chroma_store.health(),
            self._deferred_health("qdrant", "Qdrant", "externalService"),
            self._deferred_health("lancedb", "LanceDB", "pythonPackage"),
        ]

    def diagnostics(self) -> dict[str, Any]:
        active_store = self.default_store()
        return {
            "configuredBackend": self.backend,
            "activeBackend": active_store.backend_id,
            "fallbackUsed": active_store.backend_id != self.backend,
            "indexDirectory": str(self.index_directory),
            "backends": [item.__dict__ for item in self.health()],
        }

    async def migrate_collection(
        self,
        conversation_id: str,
        collection_id: str,
        source_backend: str = "json",
        target_backend: str | None = None,
    ) -> dict[str, Any]:
        source_store = self.store_by_id(source_backend)
        target_store = self.store_by_id(target_backend or self.default_store().backend_id)
        payload = await source_store.export_collection(conversation_id, collection_id)
        imported = await target_store.import_collection(payload)
        return {
            "conversationId": conversation_id,
            "collectionId": imported.get("collectionId", collection_id),
            "sourceBackend": source_store.backend_id,
            "targetBackend": target_store.backend_id,
            "fallbackUsed": target_store.backend_id != (target_backend or target_store.backend_id),
            "collection": imported,
        }

    @staticmethod
    def _deferred_health(
        backend_id: str,
        label: str,
        source: str,
    ) -> VectorStoreHealth:
        return VectorStoreHealth(
            id=backend_id,
            label=label,
            available=False,
            implemented=False,
            source=source,
            mode="deferred",
            description=(
                f"{label} is intentionally deferred; no executable adapter is "
                "registered in this release."
            ),
            checks=[
                {
                    "type": "adapter",
                    "name": backend_id,
                    "available": False,
                    "reason": "deferred",
                }
            ],
        )
