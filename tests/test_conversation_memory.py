from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.ai.vectorstores.qdrant import QdrantVectorStore
from app.schemas.memories import MemoryRecord
from app.services.conversation_memory import (
    ConversationMemoryError,
    ConversationMemoryService,
    MemoryOperationResult,
)


class FakeMemoryEmbedder:
    async def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    @staticmethod
    def embed(text: str) -> list[float]:
        normalized = text.lower()
        return [
            1.0 if "typescript" in normalized else 0.0,
            1.0 if "qdrant" in normalized else 0.0,
            1.0 if "dark mode" in normalized else 0.0,
            1.0 if "docker" in normalized else 0.0,
        ]


def _service(tmp_path: Path) -> ConversationMemoryService:
    return ConversationMemoryService(
        vector_store=QdrantVectorStore(tmp_path / "qdrant-memory"),
        embedder_provider=FakeMemoryEmbedder(),
        collection_name="test_conversation_memory",
        min_importance=0.2,
    )


@pytest.mark.asyncio
async def test_memory_store_prevents_duplicates_and_keeps_metadata(tmp_path: Path):
    service = _service(tmp_path)

    first = await service.store(
        workspace_id="workspace-a",
        conversation_id="conversation-a",
        text="I prefer TypeScript examples.",
        memory_type="preference",
        importance=0.8,
        source_message_id="message-1",
        source_role="user",
        embedder_model="all-minilm",
    )
    second = await service.store(
        workspace_id="workspace-a",
        conversation_id="conversation-a",
        text="I prefer TypeScript examples.",
        memory_type="preference",
        importance=0.8,
        source_message_id="message-1",
        source_role="user",
        embedder_model="all-minilm",
    )

    assert len(first.memories) == 1
    assert second.memories[0].id == first.memories[0].id
    listed = service.list("workspace-a", "conversation-a")
    assert len(listed.memories) == 1
    assert listed.memories[0].workspaceId == "workspace-a"
    assert listed.memories[0].conversationId == "conversation-a"
    assert listed.memories[0].type == "preference"
    assert listed.memories[0].sourceMessageId == "message-1"


@pytest.mark.asyncio
async def test_memory_retrieval_filters_by_workspace_conversation_and_type(
    tmp_path: Path,
):
    service = _service(tmp_path)
    await service.store(
        "workspace-a",
        "conversation-a",
        "Decision: use Qdrant for durable memory.",
        "decision",
        0.9,
        "message-a",
        "user",
        "all-minilm",
    )
    await service.store(
        "workspace-a",
        "conversation-b",
        "I prefer dark mode.",
        "preference",
        0.9,
        "message-b",
        "user",
        "all-minilm",
    )
    await service.store(
        "workspace-b",
        "conversation-a",
        "Decision: use Docker bind mounts.",
        "decision",
        0.9,
        "message-c",
        "user",
        "all-minilm",
    )

    result = await service.retrieve(
        workspace_id="workspace-a",
        conversation_id="conversation-a",
        query="What did we decide about Qdrant?",
        embedder_model="all-minilm",
        top_k=5,
        memory_types=["decision"],
        include_workspace_wide=False,
    )

    assert [memory.text for memory in result.memories] == [
        "Decision: use Qdrant for durable memory."
    ]


@pytest.mark.asyncio
async def test_memory_collection_is_separate_from_document_indexes(tmp_path: Path):
    service = _service(tmp_path)
    await service.store(
        "workspace-a",
        "conversation-a",
        "Decision: use Qdrant for durable memory.",
        "decision",
        0.9,
        "message-a",
        "user",
        "all-minilm",
    )

    collections = await service.vector_store.list_collections("conversation-a")

    assert collections[0]["sourceType"] == "conversation_memory"
    assert all(
        collection.get("sourceType") != "document"
        for collection in collections
    )


@pytest.mark.asyncio
async def test_memory_retrieval_orders_by_embedding_relevance(tmp_path: Path):
    service = _service(tmp_path)
    await service.store(
        "workspace-a",
        None,
        "Decision: use Docker for local deployment.",
        "decision",
        0.9,
        "message-a",
        "user",
        "all-minilm",
    )
    await service.store(
        "workspace-a",
        None,
        "Decision: use Qdrant for long-term memory.",
        "decision",
        0.9,
        "message-b",
        "user",
        "all-minilm",
    )

    result = await service.retrieve(
        workspace_id="workspace-a",
        conversation_id="conversation-a",
        query="How is Qdrant used?",
        embedder_model="all-minilm",
        top_k=2,
    )

    assert result.memories[0].text == "Decision: use Qdrant for long-term memory."


@pytest.mark.asyncio
async def test_memory_delete_removes_record(tmp_path: Path):
    service = _service(tmp_path)
    stored = await service.store(
        "workspace-a",
        "conversation-a",
        "Constraint: preserve identifiers exactly.",
        "constraint",
        0.9,
        "message-a",
        "user",
        "all-minilm",
    )

    assert service.delete(stored.memories[0].id, workspace_id="workspace-a") is True
    assert service.list("workspace-a", "conversation-a").memories == []


@pytest.mark.asyncio
async def test_memory_persists_across_service_recreation(tmp_path: Path):
    first_service = _service(tmp_path)
    await first_service.store(
        "workspace-a",
        "conversation-a",
        "Project fact: Qdrant memory uses a separate collection.",
        "project_fact",
        0.9,
        "message-a",
        "user",
        "all-minilm",
    )
    first_service.vector_store.close()

    second_service = _service(tmp_path)
    listed = second_service.list("workspace-a", "conversation-a")

    assert len(listed.memories) == 1
    assert "separate collection" in listed.memories[0].text


def test_extract_durable_memories_skips_ordinary_chat(tmp_path: Path):
    service = _service(tmp_path)

    assert service.extract_durable_memories("Hi, how are you?") == []
    assert service.extract_durable_memories(
        "Remember that I prefer TypeScript examples."
    )[0][0] == "preference"


@pytest.mark.asyncio
async def test_auto_memory_storage_filters_ordinary_chat(tmp_path: Path):
    service = _service(tmp_path)

    result = await service.store_from_message(
        workspace_id="workspace-a",
        conversation_id="conversation-a",
        message="Hi, can you explain this file?",
        source_message_id="message-a",
        source_role="user",
        embedder_model="all-minilm",
    )

    assert result.memories == []
    assert result.warnings == []
    assert service.list("workspace-a", "conversation-a").memories == []


@pytest.mark.asyncio
async def test_memory_gracefully_handles_unavailable_qdrant(tmp_path: Path):
    service = ConversationMemoryService(
        vector_store=QdrantVectorStore(
            tmp_path / "unused",
            url="http://127.0.0.1:1",
        ),
        embedder_provider=FakeMemoryEmbedder(),
        collection_name="unavailable_memory_test",
        min_importance=0.2,
    )

    stored = await service.store(
        "workspace-a",
        "conversation-a",
        "Decision: use Qdrant when available.",
        "decision",
        0.9,
        "message-a",
        "user",
        "all-minilm",
    )
    listed = service.list("workspace-a", "conversation-a")
    retrieved = await service.retrieve(
        "workspace-a",
        "conversation-a",
        "Qdrant decision",
        "all-minilm",
    )

    assert stored.memories == []
    assert "Qdrant is unavailable" in stored.warnings[0]
    assert listed.memories == []
    assert "Qdrant is unavailable" in listed.warnings[0]
    assert retrieved.memories == []
    assert "Qdrant is unavailable" in retrieved.warnings[0]
    with pytest.raises(ConversationMemoryError, match="Qdrant is unavailable"):
        service.delete("missing-memory")


def test_memories_api_create_list_search_and_delete(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_service = FakeMemoryApiService()
    app.state.conversation_memory_service = fake_service

    create_response = client.post(
        "/memories",
        headers=auth_headers,
        json={
            "workspaceId": "workspace-a",
            "conversationId": "conversation-a",
            "text": "I prefer TypeScript examples.",
            "type": "preference",
            "importance": 0.8,
            "sourceMessageId": "message-a",
            "sourceRole": "user",
            "embedderModel": "all-minilm",
        },
    )
    list_response = client.get(
        "/memories?workspaceId=workspace-a&conversationId=conversation-a",
        headers=auth_headers,
    )
    search_response = client.post(
        "/memories/search",
        headers=auth_headers,
        json={
            "workspaceId": "workspace-a",
            "conversationId": "conversation-a",
            "query": "TypeScript preference",
            "embedderModel": "all-minilm",
        },
    )
    delete_response = client.delete(
        "/memories/memory-a?workspaceId=workspace-a",
        headers=auth_headers,
    )

    assert create_response.status_code == 201
    assert create_response.json()["memories"][0]["id"] == "memory-a"
    assert list_response.status_code == 200
    assert list_response.json()["memories"][0]["workspaceId"] == "workspace-a"
    assert search_response.status_code == 200
    assert search_response.json()["memories"][0]["text"] == (
        "I prefer TypeScript examples."
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "memoryId": "memory-a"}
    assert fake_service.deleted == [("memory-a", "workspace-a")]


def test_memories_api_delete_degrades_when_qdrant_is_unavailable(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    app.state.conversation_memory_service = FakeUnavailableMemoryApiService()

    response = client.delete(
        "/memories/memory-a?workspaceId=workspace-a",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": False, "memoryId": "memory-a"}


class FakeMemoryApiService:
    def __init__(self) -> None:
        self.memory = MemoryRecord(
            id="memory-a",
            workspaceId="workspace-a",
            conversationId="conversation-a",
            text="I prefer TypeScript examples.",
            type="preference",
            importance=0.8,
            sourceMessageId="message-a",
            sourceRole="user",
            sourceHash="hash-a",
        )
        self.deleted: list[tuple[str, str | None]] = []

    async def store(self, **kwargs) -> MemoryOperationResult:
        return MemoryOperationResult([self.memory], [])

    def list(self, **kwargs) -> MemoryOperationResult:
        return MemoryOperationResult([self.memory], [])

    async def retrieve(self, **kwargs) -> MemoryOperationResult:
        return MemoryOperationResult([self.memory], [])

    def delete(self, memory_id: str, workspace_id: str | None = None) -> bool:
        self.deleted.append((memory_id, workspace_id))
        return True


class FakeUnavailableMemoryApiService(FakeMemoryApiService):
    def delete(self, memory_id: str, workspace_id: str | None = None) -> bool:
        raise ConversationMemoryError("Unable to delete memory because Qdrant is unavailable")
