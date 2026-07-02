from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import Any

from app.ai.components import ComponentUnavailableError, EmbedderProvider
from app.ai.execution_context import AIExecutionContext
from app.ai.vectorstores import JsonVectorStore, VectorStoreError
from app.services.ollama_service import (
    OllamaResponseError,
    OllamaServiceError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)

logger = logging.getLogger(__name__)

MAX_SOURCE_FIELD_CHARS = 160
MAX_SOURCE_PREVIEW_CHARS = 280


@dataclass(frozen=True)
class RetrievedSource:
    """A retrieved chunk prepared for prompt injection and response metadata."""

    source_number: int
    document_id: str
    document_name: str
    chunk_id: str
    chunk_index: int
    score: float
    vector_score: float
    text: str
    text_preview: str
    rerank_score: float | None = None
    final_rank: int = 0
    collection_id: str | None = None

    def response_payload(self) -> dict[str, Any]:
        return {
            "sourceNumber": self.source_number,
            "documentId": self.document_id,
            "documentName": self.document_name,
            "chunkId": self.chunk_id,
            "chunkIndex": self.chunk_index,
            "score": self.score,
            "vectorScore": self.vector_score,
            "rerankScore": self.rerank_score,
            "finalRank": self.final_rank or self.source_number,
            "textPreview": self.text_preview,
            "collectionId": self.collection_id,
        }


@dataclass(frozen=True)
class RetrievalResult:
    """Document retrieval result for one chat request."""

    rag_used: bool
    warnings: list[str]
    sources: list[RetrievedSource]


class DocumentRetrievalPipeline:
    """Retrieve indexed document chunks for retrieval-augmented chat."""

    def __init__(
        self,
        embedder_provider: EmbedderProvider,
        vector_store: JsonVectorStore,
    ) -> None:
        self.embedder_provider = embedder_provider
        self.vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        conversation_id: str | None,
        execution_context: AIExecutionContext,
        top_k: int = 5,
        document_ids: Sequence[str] | None = None,
    ) -> RetrievalResult:
        """Return ranked chunks, never raising for optional retrieval failures."""

        warnings: list[str] = []
        if not conversation_id:
            warnings.append(
                "Document context was not used because conversationId is missing."
            )
            return self._empty(warnings)

        embedder_component = execution_context.components["embedderModel"]
        embedder_model = execution_context.resolved_embedder_model
        if not embedder_model or not embedder_component.valid:
            warnings.append(
                "Document context was not used because no valid embedderModel "
                "is selected."
            )
            return self._empty(warnings)

        vector_database = execution_context.resolved_vector_database
        try:
            collections = await self.vector_store.list_collections(conversation_id)
        except VectorStoreError as exc:
            logger.warning("Vector collection listing failed: %s", exc)
            warnings.append(
                "Document context was not used because vector indexes could not "
                "be read."
            )
            return self._empty(warnings)

        matching_collections = [
            collection
            for collection in collections
            if collection.get("embedderModel") == embedder_model
            and collection.get("vectorDatabase") == vector_database
            and collection.get("collectionId")
        ]
        if not matching_collections:
            mismatched_embedders = sorted(
                {
                    str(collection.get("embedderModel"))
                    for collection in collections
                    if collection.get("embedderModel")
                    and collection.get("embedderModel") != embedder_model
                }
            )
            if mismatched_embedders:
                warnings.append(
                    "Document context was not used because the selected "
                    f"embedderModel '{embedder_model}' does not match indexed "
                    f"embedder(s): {', '.join(mismatched_embedders)}."
                )
            return self._empty(warnings)

        try:
            query_embedding = (
                await self.embedder_provider.embed_texts(
                    texts=[query],
                    model=embedder_model,
                )
            )[0]
        except (
            ComponentUnavailableError,
            OllamaServiceError,
            OllamaUnavailableError,
            OllamaTimeoutError,
            OllamaResponseError,
            IndexError,
        ) as exc:
            logger.warning("Query embedding failed: %s", exc)
            warnings.append(
                "Document context was not used because the selected embedder "
                "could not create a query embedding."
            )
            return self._empty(warnings)

        clean_document_ids = {
            document_id.strip()
            for document_id in (document_ids or [])
            if isinstance(document_id, str) and document_id.strip()
        }
        collection_refs = [
            self.vector_store.collection_ref(
                conversation_id,
                str(collection["collectionId"]),
            )
            for collection in matching_collections
        ]
        try:
            search_results = await self.vector_store.search(
                collection_refs=collection_refs,
                query_embedding=query_embedding,
                top_k=top_k,
                document_ids=clean_document_ids or None,
            )
        except VectorStoreError as exc:
            logger.warning("Vector search failed: %s", exc)
            warnings.append(
                "Document context was not used because vector search failed."
            )
            return self._empty(warnings)

        sources: list[RetrievedSource] = []
        skipped_results = 0
        for result in search_results:
            record = result.record
            metadata = (
                record.get("metadata")
                if isinstance(record.get("metadata"), dict)
                else {}
            )
            text = str(record.get("text") or "").strip()
            if not text:
                skipped_results += 1
                continue
            document_id = self._normalize_source_field(
                record.get("documentId") or metadata.get("documentId"),
                fallback="unknown-document",
            )
            document_name = self._normalize_source_field(
                metadata.get("documentName"),
                fallback="Document",
            )
            chunk_index = self._coerce_int(record.get("chunkIndex"))
            chunk_id = self._normalize_source_field(
                record.get("chunkId") or metadata.get("chunkId"),
                fallback=f"{document_id}:{chunk_index}",
            )
            source_number = len(sources) + 1
            sources.append(
                RetrievedSource(
                    source_number=source_number,
                    document_id=document_id,
                    document_name=document_name,
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    score=float(result.score),
                    vector_score=float(result.score),
                    text=text,
                    text_preview=self._preview(text),
                    final_rank=source_number,
                    collection_id=str(result.collection.get("collectionId") or ""),
                )
            )

        if skipped_results:
            warnings.append(
                "Skipped retrieved chunk(s) with empty text while building "
                "document context."
            )

        return RetrievalResult(
            rag_used=len(sources) > 0,
            warnings=warnings,
            sources=sources,
        )

    @staticmethod
    def _empty(warnings: list[str] | None = None) -> RetrievalResult:
        return RetrievalResult(
            rag_used=False,
            warnings=warnings or [],
            sources=[],
        )

    @staticmethod
    def _preview(text: str, max_chars: int = MAX_SOURCE_PREVIEW_CHARS) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[: max_chars - 14].rstrip()} [truncated]"

    @staticmethod
    def _normalize_source_field(
        value: object,
        fallback: str,
        max_chars: int = MAX_SOURCE_FIELD_CHARS,
    ) -> str:
        text = str(value or "")
        normalized = " ".join(text.split()).strip()
        if not normalized:
            return fallback
        if len(normalized) <= max_chars:
            return normalized
        return f"{normalized[: max(0, max_chars - 14)].rstrip()} [truncated]"

    @staticmethod
    def _coerce_int(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
