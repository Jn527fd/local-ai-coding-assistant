from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any

from app.ai.components import Chunk, RetrievedChunk
from app.ai.vectorstores.base import VectorStoreHealth

CONVERSATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
COLLECTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


class VectorStoreError(Exception):
    """Base error for local vector index persistence."""


class VectorStoreValidationError(VectorStoreError):
    """Raised when vector store input is invalid."""


class VectorCollectionNotFoundError(VectorStoreError):
    """Raised when a vector collection is absent."""


class VectorCollectionMismatchError(VectorStoreError):
    """Raised when query settings do not match collection metadata."""


@dataclass(frozen=True)
class VectorSearchResult:
    """A ranked vector search hit."""

    score: float
    record: dict[str, Any]
    collection: dict[str, Any]


class JsonVectorStore:
    """Small local JSON vector store for retrieval-only document search."""

    backend_id = "json"
    label = "Local JSON"

    def __init__(self, index_directory: Path) -> None:
        self.index_directory = index_directory.expanduser().resolve()

    def health(self) -> VectorStoreHealth:
        return VectorStoreHealth(
            id=self.backend_id,
            label=self.label,
            available=True,
            implemented=True,
            source="builtin",
            mode="direct",
            description="Default local JSON vector store used by this app.",
            checks=[],
        )

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
        return f"json-{digest}"

    async def upsert(
        self,
        collection: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        metadata: dict[str, Any],
    ) -> None:
        conversation_id, collection_id = self._split_collection_ref(collection)
        if len(chunks) != len(embeddings):
            raise VectorStoreValidationError(
                "Chunks and embeddings must have the same length."
            )

        collection_directory = self._collection_directory(
            conversation_id,
            collection_id,
        )
        existing_metadata = self._read_metadata(
            collection_directory,
            collection_id,
            conversation_id,
        )
        existing_index = self._read_index(collection_directory)
        now = self._now()
        document_ids = {
            str(document_id)
            for document_id in metadata.get("documentIds", [])
            if isinstance(document_id, str) and document_id
        }
        existing_records = [
            record
            for record in existing_index.get("vectors", [])
            if str(record.get("documentId")) not in document_ids
        ]

        new_records: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk_metadata = dict(chunk.metadata)
            document_id = str(chunk_metadata.get("documentId") or "")
            chunk_index = int(chunk_metadata.get("chunkIndex") or 0)
            vector_id = f"{document_id}:{chunk.id}"
            new_records.append(
                {
                    "vectorId": vector_id,
                    "conversationId": conversation_id,
                    "documentId": document_id,
                    "chunkId": chunk.id,
                    "chunkIndex": chunk_index,
                    "text": chunk.text,
                    "embedding": [float(value) for value in embedding],
                    "metadata": chunk_metadata,
                }
            )

        merged_document_ids = sorted(
            {
                *[
                    str(record.get("documentId"))
                    for record in existing_records
                    if record.get("documentId")
                ],
                *document_ids,
            }
        )
        created_at = existing_metadata.get("createdAt") or now
        collection_metadata = {
            **existing_metadata,
            **metadata,
            "collectionId": collection_id,
            "conversationId": conversation_id,
            "documentIds": merged_document_ids,
            "createdAt": created_at,
            "updatedAt": now,
            "recordCount": len(existing_records) + len(new_records),
            "source": "json",
        }
        index = {
            "collectionId": collection_id,
            "conversationId": conversation_id,
            "vectors": existing_records + new_records,
            "updatedAt": now,
        }
        self._write_json(collection_directory / "metadata.json", collection_metadata)
        self._write_json(collection_directory / "index.json", index)

    async def query(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        results = await self.search(
            collection_refs=[collection],
            query_embedding=query_embedding,
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
                metadata={
                    "collection": result.collection,
                    "record": result.record,
                },
            )
            for result in results
        ]

    async def get_collection_metadata(self, collection: str) -> dict[str, Any]:
        conversation_id, collection_id = self._split_collection_ref(collection)
        collection_directory = self._collection_directory(
            conversation_id,
            collection_id,
        )
        if not collection_directory.exists():
            raise VectorCollectionNotFoundError("Vector collection was not found.")
        return self._read_metadata(
            collection_directory,
            collection_id,
            conversation_id,
        )

    async def search(
        self,
        collection_refs: list[str],
        query_embedding: list[float],
        top_k: int,
        document_ids: set[str] | None = None,
    ) -> list[VectorSearchResult]:
        if top_k <= 0:
            raise VectorStoreValidationError("topK must be greater than zero.")

        results: list[VectorSearchResult] = []
        for collection_ref in collection_refs:
            conversation_id, collection_id = self._split_collection_ref(
                collection_ref
            )
            collection_directory = self._collection_directory(
                conversation_id,
                collection_id,
            )
            metadata = self._read_metadata(
                collection_directory,
                collection_id,
                conversation_id,
            )
            index = self._read_index(collection_directory)
            for record in index.get("vectors", []):
                if document_ids and str(record.get("documentId")) not in document_ids:
                    continue
                embedding = record.get("embedding")
                if not isinstance(embedding, list):
                    continue
                score = cosine_similarity(
                    query_embedding,
                    [float(value) for value in embedding],
                )
                results.append(
                    VectorSearchResult(
                        score=score,
                        record=record,
                        collection=metadata,
                    )
                )

        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    async def list_collections(self, conversation_id: str) -> list[dict[str, Any]]:
        safe_conversation_id = self._validate_conversation_id(conversation_id)
        conversation_directory = self._conversation_directory(safe_conversation_id)
        if not conversation_directory.exists():
            return []

        collections: list[dict[str, Any]] = []
        for collection_directory in sorted(conversation_directory.iterdir()):
            if not collection_directory.is_dir():
                continue
            try:
                collections.append(
                    self._read_metadata(
                        collection_directory,
                        collection_directory.name,
                        safe_conversation_id,
                    )
                )
            except VectorStoreError:
                collections.append(
                    {
                        "collectionId": collection_directory.name,
                        "conversationId": safe_conversation_id,
                        "status": "failed",
                        "error": "Collection metadata could not be read.",
                    }
                )
        collections.sort(
            key=lambda item: str(item.get("updatedAt") or item.get("createdAt") or ""),
            reverse=True,
        )
        return collections

    async def delete_collection(
        self,
        conversation_id: str,
        collection_id: str,
    ) -> bool:
        safe_conversation_id = self._validate_conversation_id(conversation_id)
        safe_collection_id = self._validate_collection_id(collection_id)
        collection_directory = self._collection_directory(
            safe_conversation_id,
            safe_collection_id,
        )
        if not collection_directory.exists():
            raise VectorCollectionNotFoundError("Vector collection was not found.")
        shutil.rmtree(collection_directory)
        return True

    def collection_ref(self, conversation_id: str, collection_id: str) -> str:
        return (
            f"{self._validate_conversation_id(conversation_id)}/"
            f"{self._validate_collection_id(collection_id)}"
        )

    def _split_collection_ref(self, collection: str) -> tuple[str, str]:
        parts = collection.split("/", maxsplit=1)
        if len(parts) != 2:
            raise VectorStoreValidationError("Invalid vector collection reference.")
        return (
            self._validate_conversation_id(parts[0]),
            self._validate_collection_id(parts[1]),
        )

    def _read_metadata(
        self,
        collection_directory: Path,
        collection_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        metadata_path = collection_directory / "metadata.json"
        if not metadata_path.exists():
            return {
                "collectionId": collection_id,
                "conversationId": conversation_id,
                "documentIds": [],
                "recordCount": 0,
                "createdAt": None,
                "updatedAt": None,
                "source": "json",
            }
        data = self._read_json(metadata_path)
        if not isinstance(data, dict):
            raise VectorStoreValidationError("Collection metadata is invalid.")
        data.setdefault("collectionId", collection_id)
        data.setdefault("conversationId", conversation_id)
        return data

    def _read_index(self, collection_directory: Path) -> dict[str, Any]:
        index_path = collection_directory / "index.json"
        if not index_path.exists():
            return {"vectors": []}
        data = self._read_json(index_path)
        if not isinstance(data, dict):
            raise VectorStoreValidationError("Vector index is invalid.")
        vectors = data.get("vectors")
        if not isinstance(vectors, list):
            data["vectors"] = []
        return data

    def _read_json(self, path: Path) -> Any:
        self._ensure_within(self.index_directory, path.resolve())
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VectorStoreValidationError(
                f"Could not read vector artifact {path.name}."
            ) from exc

    def _write_json(self, path: Path, data: Any) -> None:
        self._ensure_within(self.index_directory, path.resolve())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            raise VectorStoreError(
                f"Could not write vector artifact {path.name}."
            ) from exc

    def _collection_directory(
        self,
        conversation_id: str,
        collection_id: str,
    ) -> Path:
        collection_directory = (
            self._conversation_directory(conversation_id) / collection_id
        ).resolve()
        self._ensure_within(self.index_directory, collection_directory)
        return collection_directory

    def _conversation_directory(self, conversation_id: str) -> Path:
        conversation_directory = (
            self.index_directory / self._validate_conversation_id(conversation_id)
        ).resolve()
        self._ensure_within(self.index_directory, conversation_directory)
        return conversation_directory

    @staticmethod
    def _validate_conversation_id(conversation_id: str) -> str:
        if not CONVERSATION_ID_PATTERN.fullmatch(conversation_id):
            raise VectorStoreValidationError("Invalid conversationId.")
        if conversation_id in {".", ".."}:
            raise VectorStoreValidationError("Invalid conversationId.")
        return conversation_id

    @staticmethod
    def _validate_collection_id(collection_id: str) -> str:
        if not COLLECTION_ID_PATTERN.fullmatch(collection_id):
            raise VectorStoreValidationError("Invalid collectionId.")
        if collection_id in {".", ".."}:
            raise VectorStoreValidationError("Invalid collectionId.")
        return collection_id

    @staticmethod
    def _ensure_within(root: Path, path: Path) -> None:
        resolved_root = root.resolve()
        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(resolved_root)
        except ValueError as exc:
            raise VectorStoreValidationError("Invalid vector path.") from exc

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    return dot_product / (left_norm * right_norm)
