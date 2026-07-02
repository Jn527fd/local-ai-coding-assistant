from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from app.ai.components import Chunk, RetrievedChunk
from app.ai.vectorstores.base import VectorStoreHealth
from app.ai.vectorstores.json_store import (
    JsonVectorStore,
    VectorCollectionNotFoundError,
    VectorSearchResult,
    VectorStoreError,
    VectorStoreValidationError,
)


class ChromaVectorStore:
    """Optional Chroma adapter matching the local vector store contract."""

    backend_id = "chroma"
    label = "Chroma"

    def __init__(self, persist_directory: Path) -> None:
        self.persist_directory = persist_directory.expanduser().resolve()

    @classmethod
    def package_available(cls) -> bool:
        try:
            return find_spec("chromadb") is not None
        except (ImportError, AttributeError, ValueError):
            return False

    @staticmethod
    def collection_id(
        conversation_id: str,
        embedder_model: str,
        vector_database: str,
    ) -> str:
        return JsonVectorStore.collection_id(
            conversation_id=conversation_id,
            embedder_model=embedder_model,
            vector_database=vector_database,
        ).replace("json-", "chroma-", 1)

    async def upsert(
        self,
        collection: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
        metadata: Mapping[str, Any],
    ) -> None:
        chromadb = self._chromadb()
        conversation_id, collection_id = self._split_collection_ref(collection)
        client = chromadb.PersistentClient(
            path=str(self.persist_directory / conversation_id)
        )
        chroma_collection = client.get_or_create_collection(
            name=collection_id,
            metadata={
                key: value
                for key, value in metadata.items()
                if isinstance(value, str | int | float | bool)
            },
        )
        ids: list[str] = []
        documents: list[str] = []
        vectors: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk_metadata = dict(chunk.metadata)
            document_id = str(chunk_metadata.get("documentId") or "")
            ids.append(f"{document_id}:{chunk.id}")
            documents.append(chunk.text)
            vectors.append([float(value) for value in embedding])
            metadatas.append(
                {
                    key: value
                    for key, value in chunk_metadata.items()
                    if isinstance(value, str | int | float | bool)
                }
            )
        if not ids:
            return
        chroma_collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=vectors,
            metadatas=metadatas,
        )

    async def query(
        self,
        collection: str,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        results = await self.search(
            collection_refs=[collection],
            query_embedding=list(query_embedding),
            top_k=top_k,
        )
        return [
            RetrievedChunk(
                chunk=Chunk(
                    id=str(result.record.get("chunkId")),
                    text=str(result.record.get("text") or ""),
                    metadata=dict(result.record.get("metadata") or {}),
                ),
                score=result.score,
                metadata={"collection": result.collection, "record": result.record},
            )
            for result in results
        ]

    async def get_collection_metadata(self, collection: str) -> Mapping[str, Any]:
        chromadb = self._chromadb()
        conversation_id, collection_id = self._split_collection_ref(collection)
        client = chromadb.PersistentClient(
            path=str(self.persist_directory / conversation_id)
        )
        try:
            chroma_collection = client.get_collection(collection_id)
        except Exception as exc:
            raise VectorCollectionNotFoundError(
                "Vector collection was not found."
            ) from exc
        return self._collection_metadata(
            conversation_id,
            collection_id,
            chroma_collection,
        )

    async def search(
        self,
        collection_refs: list[str],
        query_embedding: Sequence[float],
        top_k: int,
        document_ids: set[str] | None = None,
    ) -> list[VectorSearchResult]:
        if top_k <= 0:
            raise VectorStoreValidationError("topK must be greater than zero.")

        chromadb = self._chromadb()
        results: list[VectorSearchResult] = []
        for collection_ref in collection_refs:
            conversation_id, collection_id = self._split_collection_ref(
                collection_ref
            )
            client = chromadb.PersistentClient(
                path=str(self.persist_directory / conversation_id)
            )
            try:
                chroma_collection = client.get_collection(collection_id)
            except Exception as exc:
                raise VectorCollectionNotFoundError(
                    "Vector collection was not found."
                ) from exc
            query_result = chroma_collection.query(
                query_embeddings=[[float(value) for value in query_embedding]],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
            ids = (query_result.get("ids") or [[]])[0]
            documents = (query_result.get("documents") or [[]])[0]
            metadatas = (query_result.get("metadatas") or [[]])[0]
            distances = (query_result.get("distances") or [[]])[0]
            collection_metadata = self._collection_metadata(
                conversation_id,
                collection_id,
                chroma_collection,
            )
            for index, vector_id in enumerate(ids):
                metadata = metadatas[index] if index < len(metadatas) else {}
                if document_ids and str(metadata.get("documentId")) not in document_ids:
                    continue
                distance = float(distances[index]) if index < len(distances) else 1.0
                score = max(0.0, 1.0 - distance)
                chunk_id = str(metadata.get("chunkId") or vector_id)
                record = {
                    "documentId": str(metadata.get("documentId") or ""),
                    "chunkId": chunk_id,
                    "chunkIndex": metadata.get("chunkIndex", 0),
                    "text": documents[index] if index < len(documents) else "",
                    "metadata": dict(metadata),
                }
                results.append(
                    VectorSearchResult(
                        score=score,
                        record=record,
                        collection=collection_metadata,
                    )
                )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    async def list_collections(self, conversation_id: str) -> list[dict[str, Any]]:
        chromadb = self._chromadb()
        safe_conversation_id = JsonVectorStore._validate_conversation_id(
            conversation_id
        )
        client = chromadb.PersistentClient(
            path=str(self.persist_directory / safe_conversation_id)
        )
        return [
            self._collection_metadata(safe_conversation_id, collection.name, collection)
            for collection in client.list_collections()
        ]

    async def delete_collection(
        self,
        conversation_id: str,
        collection_id: str,
    ) -> bool:
        chromadb = self._chromadb()
        safe_conversation_id = JsonVectorStore._validate_conversation_id(
            conversation_id
        )
        safe_collection_id = JsonVectorStore._validate_collection_id(collection_id)
        client = chromadb.PersistentClient(
            path=str(self.persist_directory / safe_conversation_id)
        )
        try:
            client.delete_collection(safe_collection_id)
        except Exception as exc:
            raise VectorCollectionNotFoundError(
                "Vector collection was not found."
            ) from exc
        return True

    def collection_ref(self, conversation_id: str, collection_id: str) -> str:
        return (
            f"{JsonVectorStore._validate_conversation_id(conversation_id)}/"
            f"{JsonVectorStore._validate_collection_id(collection_id)}"
        )

    def health(self) -> VectorStoreHealth:
        available = self.package_available()
        return VectorStoreHealth(
            id=self.backend_id,
            label=self.label,
            available=available,
            implemented=available,
            source="pythonPackage",
            mode="direct" if available else "unavailable",
            description=(
                "Chroma adapter is available and can persist vectors locally."
                if available
                else "Install the chromadb Python package to enable the Chroma adapter."
            ),
            checks=[
                {
                    "type": "pythonPackage",
                    "name": "chromadb",
                    "available": available,
                }
            ],
        )

    @staticmethod
    def _collection_metadata(
        conversation_id: str,
        collection_id: str,
        collection: object,
    ) -> dict[str, Any]:
        metadata = dict(getattr(collection, "metadata", None) or {})
        return {
            **metadata,
            "collectionId": collection_id,
            "conversationId": conversation_id,
            "recordCount": getattr(collection, "count", lambda: 0)(),
            "source": "chroma",
            "internalStore": "chroma",
        }

    @staticmethod
    def _split_collection_ref(collection: str) -> tuple[str, str]:
        return JsonVectorStore(Path("."))._split_collection_ref(collection)

    @staticmethod
    def _chromadb() -> Any:
        if not ChromaVectorStore.package_available():
            raise VectorStoreError(
                "Chroma vector store is unavailable because chromadb is not installed."
            )
        import chromadb

        return chromadb

