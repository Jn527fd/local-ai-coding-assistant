from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from importlib.util import find_spec
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.ai.components import Chunk, RetrievedChunk
from app.ai.vectorstores.base import VectorStoreHealth
from app.ai.vectorstores.json_store import (
    JsonVectorStore,
    VectorCollectionNotFoundError,
    VectorSearchResult,
    VectorStoreError,
    VectorStoreValidationError,
)


class QdrantVectorStore:
    """Qdrant adapter matching the app vector store contract."""

    backend_id = "qdrant"
    label = "Qdrant"

    def __init__(
        self,
        storage_path: Path,
        url: str = "",
        api_key: str = "",
    ) -> None:
        self.storage_path = storage_path.expanduser().resolve()
        self.url = (url or "").strip()
        self.api_key = api_key
        self._client_instance: Any | None = None

    @classmethod
    def package_available(cls) -> bool:
        try:
            return find_spec("qdrant_client") is not None
        except (ImportError, AttributeError, ValueError):
            return False

    @staticmethod
    def collection_id(
        conversation_id: str,
        embedder_model: str,
        vector_database: str,
    ) -> str:
        digest = hashlib.sha256(
            f"{conversation_id}\0{embedder_model}\0{vector_database}".encode(
                "utf-8"
            )
        ).hexdigest()[:16]
        return f"qdrant-{digest}"

    async def upsert(
        self,
        collection: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
        metadata: Mapping[str, Any],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise VectorStoreValidationError(
                "Chunks and embeddings must have the same length."
            )
        if not chunks:
            return

        client, models = self._client_and_models()
        conversation_id, collection_id = self._split_collection_ref(collection)
        vector_size = len(embeddings[0])
        if vector_size <= 0:
            raise VectorStoreValidationError("Embeddings must not be empty.")
        self._ensure_collection(client, models, collection_id, vector_size)

        document_ids = {
            str(document_id)
            for document_id in metadata.get("documentIds", [])
            if isinstance(document_id, str) and document_id
        }
        if document_ids:
            client.delete(
                collection_name=collection_id,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="documentId",
                                match=models.MatchAny(any=list(document_ids)),
                            )
                        ]
                    )
                ),
                wait=True,
            )

        points = []
        collection_payload = {
            **metadata,
            "collectionId": collection_id,
            "conversationId": conversation_id,
            "vectorDatabase": str(metadata.get("vectorDatabase") or "qdrant"),
            "source": self.backend_id,
            "internalStore": self.backend_id,
        }
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk_metadata = dict(chunk.metadata)
            document_id = str(chunk_metadata.get("documentId") or "")
            chunk_id = str(chunk_metadata.get("chunkId") or chunk.id)
            chunk_index = int(chunk_metadata.get("chunkIndex") or 0)
            vector_id = f"{document_id}:{chunk.id}"
            payload = {
                **self._qdrant_payload(collection_payload),
                **self._qdrant_payload(chunk_metadata),
                "vectorId": vector_id,
                "documentId": document_id,
                "chunkId": chunk_id,
                "chunkIndex": chunk_index,
                "text": chunk.text,
                "metadata": self._qdrant_payload(chunk_metadata),
            }
            points.append(
                models.PointStruct(
                    id=str(uuid5(NAMESPACE_URL, f"{collection_id}:{vector_id}")),
                    vector=[float(value) for value in embedding],
                    payload=payload,
                )
            )
        client.upsert(collection_name=collection_id, points=points, wait=True)

    async def query(
        self,
        collection: str,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        results = await self.search([collection], query_embedding, top_k)
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
        client, _models = self._client_and_models()
        conversation_id, collection_id = self._split_collection_ref(collection)
        try:
            info = client.get_collection(collection_id)
        except Exception as exc:
            raise VectorCollectionNotFoundError(
                "Vector collection was not found."
            ) from exc
        first_payload = self._first_payload(client, collection_id)
        return self._collection_metadata(
            client,
            conversation_id,
            collection_id,
            info,
            first_payload=first_payload,
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

        client, models = self._client_and_models()
        results: list[VectorSearchResult] = []
        query_filter = None
        if document_ids:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="documentId",
                        match=models.MatchAny(any=sorted(document_ids)),
                    )
                ]
            )
        for collection_ref in collection_refs:
            conversation_id, collection_id = self._split_collection_ref(
                collection_ref
            )
            try:
                hits = client.query_points(
                    collection_name=collection_id,
                    query=[float(value) for value in query_embedding],
                    query_filter=query_filter,
                    limit=top_k,
                    with_payload=True,
                ).points
            except Exception as exc:
                raise VectorCollectionNotFoundError(
                    "Vector collection was not found."
                ) from exc
            collection = dict(
                await self.get_collection_metadata(
                    self.collection_ref(conversation_id, collection_id)
                )
            )
            for hit in hits:
                payload = dict(getattr(hit, "payload", None) or {})
                record = {
                    "documentId": str(payload.get("documentId") or ""),
                    "chunkId": str(payload.get("chunkId") or ""),
                    "chunkIndex": payload.get("chunkIndex", 0),
                    "text": str(payload.get("text") or ""),
                    "metadata": dict(payload.get("metadata") or {}),
                }
                results.append(
                    VectorSearchResult(
                        score=float(getattr(hit, "score", 0.0) or 0.0),
                        record=record,
                        collection=collection,
                    )
                )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    async def list_collections(self, conversation_id: str) -> list[dict[str, Any]]:
        client, models = self._client_and_models()
        safe_conversation_id = JsonVectorStore._validate_conversation_id(
            conversation_id
        )
        collections: list[dict[str, Any]] = []
        for collection in client.get_collections().collections:
            collection_id = str(collection.name)
            try:
                points, _next_page = client.scroll(
                    collection_name=collection_id,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="conversationId",
                                match=models.MatchValue(value=safe_conversation_id),
                            )
                        ]
                    ),
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )
            except Exception:
                continue
            if not points:
                continue
            info = client.get_collection(collection_id)
            collections.append(
                self._collection_metadata(
                    client,
                    safe_conversation_id,
                    collection_id,
                    info,
                    first_payload=dict(points[0].payload or {}),
                )
            )
        return collections

    async def delete_collection(
        self,
        conversation_id: str,
        collection_id: str,
    ) -> bool:
        client, _models = self._client_and_models()
        JsonVectorStore._validate_conversation_id(conversation_id)
        safe_collection_id = JsonVectorStore._validate_collection_id(collection_id)
        try:
            client.delete_collection(safe_collection_id)
        except Exception as exc:
            raise VectorCollectionNotFoundError(
                "Vector collection was not found."
            ) from exc
        return True

    async def export_collection(
        self,
        conversation_id: str,
        collection_id: str,
    ) -> dict[str, Any]:
        client, _models = self._client_and_models()
        safe_conversation_id = JsonVectorStore._validate_conversation_id(
            conversation_id
        )
        safe_collection_id = JsonVectorStore._validate_collection_id(collection_id)
        try:
            points, _next_page = client.scroll(
                collection_name=safe_collection_id,
                limit=10_000,
                with_payload=True,
                with_vectors=True,
            )
        except Exception as exc:
            raise VectorCollectionNotFoundError(
                "Vector collection was not found."
            ) from exc
        vectors: list[dict[str, Any]] = []
        for point in points:
            payload = dict(point.payload or {})
            vectors.append(
                {
                    "vectorId": str(payload.get("vectorId") or point.id),
                    "conversationId": safe_conversation_id,
                    "documentId": str(payload.get("documentId") or ""),
                    "chunkId": str(payload.get("chunkId") or ""),
                    "chunkIndex": payload.get("chunkIndex", 0),
                    "text": str(payload.get("text") or ""),
                    "embedding": [float(value) for value in point.vector],
                    "metadata": dict(payload.get("metadata") or {}),
                }
            )
        metadata = await self.get_collection_metadata(
            self.collection_ref(safe_conversation_id, safe_collection_id)
        )
        return {
            "format": "local-ai-vector-collection-v1",
            "backend": self.backend_id,
            "collectionId": safe_collection_id,
            "conversationId": safe_conversation_id,
            "metadata": dict(metadata),
            "vectors": vectors,
        }

    async def import_collection(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if payload.get("format") != "local-ai-vector-collection-v1":
            raise VectorStoreValidationError("Unsupported vector collection export.")
        metadata = payload.get("metadata")
        vectors = payload.get("vectors")
        if not isinstance(metadata, Mapping) or not isinstance(vectors, list):
            raise VectorStoreValidationError("Vector collection payload is invalid.")
        conversation_id = JsonVectorStore._validate_conversation_id(
            str(payload.get("conversationId") or metadata.get("conversationId") or "")
        )
        collection_id = JsonVectorStore._validate_collection_id(
            str(payload.get("collectionId") or metadata.get("collectionId") or "")
        )
        chunks: list[Chunk] = []
        embeddings: list[list[float]] = []
        for record in vectors:
            if not isinstance(record, Mapping):
                continue
            embedding = record.get("embedding")
            if not isinstance(embedding, list):
                continue
            record_metadata = (
                dict(record.get("metadata"))
                if isinstance(record.get("metadata"), Mapping)
                else {}
            )
            chunk_id = str(record.get("chunkId") or record_metadata.get("chunkId") or "")
            if not chunk_id:
                continue
            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=str(record.get("text") or ""),
                    metadata={
                        **record_metadata,
                        "documentId": str(
                            record.get("documentId")
                            or record_metadata.get("documentId")
                            or ""
                        ),
                        "chunkId": chunk_id,
                        "chunkIndex": record.get(
                            "chunkIndex",
                            record_metadata.get("chunkIndex", 0),
                        ),
                    },
                )
            )
            embeddings.append([float(value) for value in embedding])
        await self.upsert(
            collection=self.collection_ref(conversation_id, collection_id),
            chunks=chunks,
            embeddings=embeddings,
            metadata={
                **dict(metadata),
                "collectionId": collection_id,
                "conversationId": conversation_id,
                "source": self.backend_id,
                "internalStore": self.backend_id,
            },
        )
        return dict(
            await self.get_collection_metadata(
                self.collection_ref(conversation_id, collection_id)
            )
        )

    def collection_ref(self, conversation_id: str, collection_id: str) -> str:
        return (
            f"{JsonVectorStore._validate_conversation_id(conversation_id)}/"
            f"{JsonVectorStore._validate_collection_id(collection_id)}"
        )

    def health(self) -> VectorStoreHealth:
        package_available = self.package_available()
        service_available = False
        service_reason = "qdrant-client is not installed"
        if package_available:
            try:
                self._client().get_collections()
                service_available = True
                service_reason = "reachable"
            except Exception as exc:
                service_reason = str(exc)
        return VectorStoreHealth(
            id=self.backend_id,
            label=self.label,
            available=package_available and service_available,
            implemented=package_available,
            source="qdrant",
            mode="direct" if package_available and service_available else "unavailable",
            description=(
                "Qdrant vector store is available and persists indexes."
                if package_available and service_available
                else "Qdrant is the standard vector store; start the service and install qdrant-client."
            ),
            checks=[
                {
                    "type": "pythonPackage",
                    "name": "qdrant_client",
                    "available": package_available,
                },
                {
                    "type": "service",
                    "name": self.url or str(self.storage_path),
                    "available": service_available,
                    "reason": service_reason,
                },
            ],
        )

    def close(self) -> None:
        if self._client_instance is None:
            return
        close = getattr(self._client_instance, "close", None)
        if callable(close):
            close()
        self._client_instance = None

    def _ensure_collection(self, client: Any, models: Any, collection_id: str, size: int) -> None:
        try:
            info = client.get_collection(collection_id)
            existing_size = self._vector_size(info)
            if existing_size and existing_size != size:
                raise VectorStoreValidationError(
                    "Existing Qdrant collection vector size does not match embeddings."
                )
            return
        except VectorStoreValidationError:
            raise
        except Exception:
            client.create_collection(
                collection_name=collection_id,
                vectors_config=models.VectorParams(
                    size=size,
                    distance=models.Distance.COSINE,
                ),
            )

    @staticmethod
    def _vector_size(info: object) -> int | None:
        vectors = getattr(getattr(info, "config", None), "params", None)
        vectors = getattr(vectors, "vectors", None)
        size = getattr(vectors, "size", None)
        try:
            return int(size) if size is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _first_payload(client: Any, collection_id: str) -> dict[str, Any]:
        try:
            points, _next_page = client.scroll(
                collection_name=collection_id,
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            return {}
        if not points:
            return {}
        return dict(points[0].payload or {})

    @staticmethod
    def _collection_metadata(
        client: Any,
        conversation_id: str,
        collection_id: str,
        info: object,
        first_payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(first_payload or {})
        count = getattr(client.count(collection_id, exact=True), "count", 0)
        return {
            **{
                key: value
                for key, value in payload.items()
                if key
                in {
                    "embedderModel",
                    "vectorDatabase",
                    "chunker",
                    "ragPipeline",
                    "sourceType",
                    "repositoryName",
                    "repositoryId",
                    "repositoryPath",
                }
            },
            "collectionId": collection_id,
            "conversationId": conversation_id,
            "documentIds": payload.get("documentIds", []),
            "recordCount": int(count or 0),
            "source": "qdrant",
            "internalStore": "qdrant",
        }

    @staticmethod
    def _qdrant_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, str | int | float | bool) or value is None:
                cleaned[str(key)] = value
            elif isinstance(value, list):
                cleaned[str(key)] = [
                    item
                    for item in value
                    if isinstance(item, str | int | float | bool) or item is None
                ]
            elif isinstance(value, Mapping):
                nested = QdrantVectorStore._qdrant_payload(value)
                if nested:
                    cleaned[str(key)] = nested
        return cleaned

    @staticmethod
    def _split_collection_ref(collection: str) -> tuple[str, str]:
        return JsonVectorStore(Path("."))._split_collection_ref(collection)

    def _client_and_models(self) -> tuple[Any, Any]:
        client = self._client()
        from qdrant_client import models

        return client, models

    def _client(self) -> Any:
        if not self.package_available():
            raise VectorStoreError(
                "Qdrant vector store is unavailable because qdrant-client is not installed."
            )
        from qdrant_client import QdrantClient

        if self._client_instance is not None:
            return self._client_instance
        if self.url:
            self._client_instance = QdrantClient(
                url=self.url,
                api_key=self.api_key or None,
                timeout=5,
            )
            return self._client_instance
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._client_instance = QdrantClient(path=str(self.storage_path))
        return self._client_instance
