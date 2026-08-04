from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.ai.components import ComponentUnavailableError, EmbedderProvider
from app.ai.vectorstores.qdrant import QdrantVectorStore
from app.schemas.memories import MemoryRecord, MemoryType

MEMORY_TYPES: tuple[MemoryType, ...] = (
    "preference",
    "decision",
    "constraint",
    "task",
    "project_fact",
)


class ConversationMemoryError(RuntimeError):
    """Raised when conversational memory cannot be stored or retrieved."""


@dataclass(frozen=True)
class MemoryOperationResult:
    memories: list[MemoryRecord]
    warnings: list[str]


class ConversationMemoryService:
    """Separate Qdrant-backed store for durable conversational memories."""

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        embedder_provider: EmbedderProvider,
        collection_name: str = "local_ai_conversation_memory_v1",
        min_importance: float = 0.35,
    ) -> None:
        self.vector_store = vector_store
        self.embedder_provider = embedder_provider
        self.collection_name = collection_name
        self.min_importance = min_importance

    async def store(
        self,
        workspace_id: str,
        conversation_id: str | None,
        text: str,
        memory_type: MemoryType,
        importance: float,
        source_message_id: str | None,
        source_role: str | None,
        embedder_model: str,
    ) -> MemoryOperationResult:
        memory_text = self._normalize_text(text)
        if not memory_text:
            return MemoryOperationResult([], ["Memory text was empty."])
        if importance < self.min_importance:
            return MemoryOperationResult(
                [],
                ["Memory was not stored because its importance is below the threshold."],
            )

        workspace_id = self._clean_scope(workspace_id, "default")
        conversation_id = self._clean_optional_scope(conversation_id)
        source_hash = self._source_hash(
            workspace_id,
            conversation_id,
            memory_type,
            memory_text,
        )
        try:
            existing = await self._find_by_hash(source_hash)
        except Exception as exc:
            return MemoryOperationResult(
                [],
                [f"Memory was not stored because Qdrant is unavailable: {exc}"],
            )
        if existing is not None:
            return MemoryOperationResult([existing], [])

        try:
            embedding = (
                await self.embedder_provider.embed_texts(
                    texts=[memory_text],
                    model=embedder_model,
                )
            )[0]
        except (ComponentUnavailableError, AttributeError, IndexError, ValueError) as exc:
            return MemoryOperationResult(
                [],
                [f"Memory was not stored because embedding failed: {exc}"],
            )

        now = datetime.now(timezone.utc)
        record = MemoryRecord(
            id=str(uuid5(NAMESPACE_URL, f"{self.collection_name}:{source_hash}")),
            workspaceId=workspace_id,
            conversationId=conversation_id,
            text=memory_text,
            type=memory_type,
            importance=max(0.0, min(float(importance), 1.0)),
            createdAt=now,
            updatedAt=now,
            sourceMessageId=source_message_id,
            sourceRole=source_role,
            sourceHash=source_hash,
        )
        try:
            self._upsert_record(record, embedding)
        except Exception as exc:
            return MemoryOperationResult(
                [],
                [f"Memory was not stored because Qdrant is unavailable: {exc}"],
            )
        return MemoryOperationResult([record], [])

    async def store_from_message(
        self,
        workspace_id: str,
        conversation_id: str | None,
        message: str,
        source_message_id: str | None,
        source_role: str,
        embedder_model: str | None,
        enabled: bool = True,
    ) -> MemoryOperationResult:
        if not enabled or not embedder_model:
            return MemoryOperationResult([], [])
        candidates = self.extract_durable_memories(message)
        memories: list[MemoryRecord] = []
        warnings: list[str] = []
        for memory_type, text, importance in candidates:
            result = await self.store(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                text=text,
                memory_type=memory_type,
                importance=importance,
                source_message_id=source_message_id,
                source_role=source_role,
                embedder_model=embedder_model,
            )
            memories.extend(result.memories)
            warnings.extend(result.warnings)
        return MemoryOperationResult(memories, warnings)

    async def retrieve(
        self,
        workspace_id: str,
        conversation_id: str | None,
        query: str,
        embedder_model: str | None,
        top_k: int = 5,
        memory_types: Sequence[MemoryType] | None = None,
        min_importance: float = 0.0,
        include_workspace_wide: bool = True,
    ) -> MemoryOperationResult:
        if not embedder_model:
            return MemoryOperationResult(
                [],
                ["Long-term memory was not used because no embedder model is selected."],
            )
        try:
            query_embedding = (
                await self.embedder_provider.embed_texts(
                    texts=[query],
                    model=embedder_model,
                )
            )[0]
        except (ComponentUnavailableError, AttributeError, IndexError, ValueError) as exc:
            return MemoryOperationResult(
                [],
                [f"Long-term memory retrieval failed because embedding failed: {exc}"],
            )

        try:
            client, models = self.vector_store._client_and_models()
            query_filter = self._memory_filter(
                models=models,
                workspace_id=self._clean_scope(workspace_id, "default"),
                conversation_id=self._clean_optional_scope(conversation_id),
                memory_types=memory_types or (),
                min_importance=min_importance,
                include_workspace_wide=include_workspace_wide,
            )
            hits = client.query_points(
                collection_name=self.collection_name,
                query=[float(value) for value in query_embedding],
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            ).points
        except Exception as exc:
            return MemoryOperationResult(
                [],
                [f"Long-term memory retrieval skipped because Qdrant is unavailable: {exc}"],
            )

        memories = [
            self._record_from_payload(dict(hit.payload or {}), score=float(hit.score))
            for hit in hits
            if getattr(hit, "payload", None)
        ]
        memories = [memory for memory in memories if memory is not None]
        memories.sort(
            key=lambda memory: (
                memory.score or 0.0,
                memory.importance,
                memory.createdAt,
            ),
            reverse=True,
        )
        return MemoryOperationResult(memories, [])

    def list(
        self,
        workspace_id: str,
        conversation_id: str | None = None,
        memory_types: Sequence[MemoryType] | None = None,
        include_workspace_wide: bool = True,
        limit: int = 100,
    ) -> MemoryOperationResult:
        try:
            client, models = self.vector_store._client_and_models()
            query_filter = self._memory_filter(
                models=models,
                workspace_id=self._clean_scope(workspace_id, "default"),
                conversation_id=self._clean_optional_scope(conversation_id),
                memory_types=memory_types or (),
                min_importance=0.0,
                include_workspace_wide=include_workspace_wide,
            )
            points, _next_page = client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            return MemoryOperationResult(
                [],
                [f"Long-term memory listing skipped because Qdrant is unavailable: {exc}"],
            )
        memories = [
            self._record_from_payload(dict(point.payload or {}))
            for point in points
            if getattr(point, "payload", None)
        ]
        memories = [memory for memory in memories if memory is not None]
        memories.sort(key=lambda memory: memory.createdAt, reverse=True)
        return MemoryOperationResult(memories, [])

    def delete(
        self,
        memory_id: str,
        workspace_id: str | None = None,
    ) -> bool:
        try:
            client, models = self.vector_store._client_and_models()
            must: list[Any] = [
                models.FieldCondition(
                    key="id",
                    match=models.MatchValue(value=memory_id),
                )
            ]
            if workspace_id:
                must.append(
                    models.FieldCondition(
                        key="workspaceId",
                        match=models.MatchValue(
                            value=self._clean_scope(workspace_id, "default")
                        ),
                    )
                )
            client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=must)
                ),
                wait=True,
            )
        except Exception as exc:
            raise ConversationMemoryError(
                f"Unable to delete memory because Qdrant is unavailable: {exc}"
            ) from exc
        return True

    @staticmethod
    def extract_durable_memories(message: str) -> list[tuple[MemoryType, str, float]]:
        text = " ".join(message.split()).strip()
        if not text:
            return []
        lowered = text.lower()
        candidates: list[tuple[MemoryType, str, float]] = []
        rules: list[tuple[MemoryType, tuple[str, ...], float]] = [
            ("preference", ("i prefer", "my preference", "remember that i like"), 0.65),
            ("decision", ("we decided", "decision:", "the decision is"), 0.75),
            ("constraint", ("constraint:", "must ", "do not ", "never "), 0.7),
            ("task", ("todo:", "unresolved", "follow up", "need to"), 0.55),
            ("project_fact", ("project fact:", "important project fact", "remember that"), 0.6),
        ]
        for memory_type, markers, importance in rules:
            if any(marker in lowered for marker in markers):
                candidates.append((memory_type, text[:2_000], importance))
                break
        return candidates

    def format_memory_context(self, memories: Sequence[MemoryRecord]) -> str:
        if not memories:
            return ""
        lines = [
            "Long-term project memory from Qdrant:",
            "Use these durable memories only when relevant; the latest user message remains authoritative.",
        ]
        for index, memory in enumerate(memories, start=1):
            scope = (
                f"conversation={memory.conversationId}"
                if memory.conversationId
                else "workspace-wide"
            )
            lines.append(
                (
                    f"{index}. [{memory.type}; importance={memory.importance:.2f}; "
                    f"{scope}; created={memory.createdAt.isoformat()}] "
                    f"{memory.text}"
                )
            )
        return "\n".join(lines)

    def _upsert_record(self, record: MemoryRecord, embedding: Sequence[float]) -> None:
        client, models = self.vector_store._client_and_models()
        if not embedding:
            raise ConversationMemoryError("Memory embedding must not be empty.")
        self.vector_store._ensure_collection(
            client,
            models,
            self.collection_name,
            len(embedding),
        )
        client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=record.id,
                    vector=[float(value) for value in embedding],
                    payload={
                        **record.model_dump(mode="json"),
                        "sourceType": "conversation_memory",
                    },
                )
            ],
            wait=True,
        )

    async def _find_by_hash(self, source_hash: str) -> MemoryRecord | None:
        try:
            client, models = self.vector_store._client_and_models()
            points, _next_page = client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="sourceHash",
                            match=models.MatchValue(value=source_hash),
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            return None
        if not points:
            return None
        return self._record_from_payload(dict(points[0].payload or {}))

    @staticmethod
    def _memory_filter(
        models: Any,
        workspace_id: str,
        conversation_id: str | None,
        memory_types: Sequence[MemoryType],
        min_importance: float,
        include_workspace_wide: bool,
    ) -> Any:
        must: list[Any] = [
            models.FieldCondition(
                key="workspaceId",
                match=models.MatchValue(value=workspace_id),
            ),
            models.FieldCondition(
                key="importance",
                range=models.Range(gte=float(min_importance)),
            ),
        ]
        if memory_types:
            must.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchAny(any=list(memory_types)),
                )
            )
        should: list[Any] = []
        if conversation_id:
            should.append(
                models.FieldCondition(
                    key="conversationId",
                    match=models.MatchValue(value=conversation_id),
                )
            )
        if include_workspace_wide:
            should.append(
                models.IsNullCondition(
                    is_null=models.PayloadField(key="conversationId")
                )
            )
        if should:
            return models.Filter(must=must, should=should)
        return models.Filter(must=must)

    @staticmethod
    def _record_from_payload(
        payload: dict[str, Any],
        score: float | None = None,
    ) -> MemoryRecord | None:
        try:
            return MemoryRecord.model_validate({**payload, "score": score})
        except Exception:
            return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _clean_scope(value: str | None, fallback: str) -> str:
        text = re.sub(r"[^A-Za-z0-9_.:-]+", "-", (value or "").strip())
        return text[:120] or fallback

    @classmethod
    def _clean_optional_scope(cls, value: str | None) -> str | None:
        cleaned = cls._clean_scope(value, "")
        return cleaned or None

    @staticmethod
    def _source_hash(
        workspace_id: str,
        conversation_id: str | None,
        memory_type: str,
        text: str,
    ) -> str:
        return hashlib.sha256(
            "\0".join(
                [
                    workspace_id,
                    conversation_id or "",
                    memory_type,
                    text.lower(),
                ]
            ).encode("utf-8")
        ).hexdigest()
