from pathlib import Path

import pytest

from app.ai.components import Chunk
from app.ai.vectorstores import (
    ChromaVectorStore,
    JsonVectorStore,
    VectorStoreBackend,
    VectorStoreManager,
)


async def assert_basic_vector_store_contract(store, collection_ref: str) -> None:
    chunk = Chunk(
        id="chunk-apple",
        text="apple pie",
        metadata={
            "documentId": "doc-1",
            "documentName": "notes.txt",
            "chunkId": "chunk-apple",
            "chunkIndex": 0,
        },
    )

    await store.upsert(
        collection=collection_ref,
        chunks=[chunk],
        embeddings=[[1.0, 0.0]],
        metadata={
            "embedderModel": "embed-a",
            "vectorDatabase": store.backend_id,
            "documentIds": ["doc-1"],
        },
    )

    metadata = await store.get_collection_metadata(collection_ref)
    results = await store.query(collection_ref, [1.0, 0.0], top_k=1)

    assert metadata["recordCount"] >= 1
    assert results[0].chunk.id == "chunk-apple"
    assert results[0].score > 0


def test_vector_store_manager_defaults_to_json(tmp_path: Path) -> None:
    manager = VectorStoreManager(tmp_path / "vectors")

    store = manager.default_store()

    assert isinstance(store, JsonVectorStore)
    assert isinstance(store, VectorStoreBackend)
    assert store.health().id == "json"
    assert store.health().available is True


def test_vector_store_manager_falls_back_to_json_when_chroma_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ChromaVectorStore,
        "package_available",
        staticmethod(lambda: False),
    )
    manager = VectorStoreManager(tmp_path / "vectors", backend="chroma")

    assert isinstance(manager.default_store(), JsonVectorStore)
    health = {item.id: item for item in manager.health()}
    assert health["json"].available is True
    assert health["chroma"].available is False
    assert health["chroma"].implemented is False


def test_vector_store_manager_selects_chroma_when_configured_and_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ChromaVectorStore,
        "package_available",
        staticmethod(lambda: True),
    )
    manager = VectorStoreManager(tmp_path / "vectors", backend="chroma")

    assert isinstance(manager.default_store(), ChromaVectorStore)
    assert isinstance(manager.store_for_selection("chroma"), ChromaVectorStore)
    assert isinstance(manager.store_for_selection("faiss"), JsonVectorStore)


def test_json_and_chroma_collection_ids_are_backend_scoped() -> None:
    json_id = JsonVectorStore.collection_id("chat-1", "embed-a", "chroma")
    chroma_id = ChromaVectorStore.collection_id("chat-1", "embed-a", "chroma")

    assert json_id.startswith("json-")
    assert chroma_id.startswith("chroma-")
    assert json_id.removeprefix("json-") == chroma_id.removeprefix("chroma-")


@pytest.mark.asyncio
async def test_json_vector_store_contract(tmp_path: Path) -> None:
    store = JsonVectorStore(tmp_path / "json")
    collection_ref = store.collection_ref(
        "chat-1",
        JsonVectorStore.collection_id("chat-1", "embed-a", "json"),
    )

    await assert_basic_vector_store_contract(store, collection_ref)


@pytest.mark.asyncio
async def test_json_vector_store_exports_and_imports_portable_collection(
    tmp_path: Path,
) -> None:
    source = JsonVectorStore(tmp_path / "source")
    target = JsonVectorStore(tmp_path / "target")
    collection_id = JsonVectorStore.collection_id("chat-1", "embed-a", "json")
    collection_ref = source.collection_ref("chat-1", collection_id)
    await assert_basic_vector_store_contract(source, collection_ref)

    payload = await source.export_collection("chat-1", collection_id)
    imported = await target.import_collection(payload)
    results = await target.query(
        target.collection_ref("chat-1", collection_id),
        [1.0, 0.0],
        top_k=1,
    )

    assert payload["format"] == "local-ai-vector-collection-v1"
    assert imported["collectionId"] == collection_id
    assert imported["recordCount"] == 1
    assert results[0].chunk.metadata["documentName"] == "notes.txt"


def test_vector_store_manager_reports_deferred_backends(tmp_path: Path) -> None:
    diagnostics = VectorStoreManager(tmp_path / "vectors").diagnostics()
    backends = {item["id"]: item for item in diagnostics["backends"]}

    assert diagnostics["activeBackend"] == "json"
    assert diagnostics["fallbackUsed"] is False
    assert backends["json"]["available"] is True
    assert backends["qdrant"]["mode"] == "deferred"
    assert backends["lancedb"]["implemented"] is False


@pytest.mark.asyncio
async def test_vector_store_manager_migrates_collection_to_json_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ChromaVectorStore,
        "package_available",
        staticmethod(lambda: False),
    )
    manager = VectorStoreManager(tmp_path / "vectors", backend="chroma")
    collection_id = JsonVectorStore.collection_id("chat-1", "embed-a", "json")
    await assert_basic_vector_store_contract(
        manager.json_store,
        manager.json_store.collection_ref("chat-1", collection_id),
    )

    migrated = await manager.migrate_collection(
        "chat-1",
        collection_id,
        source_backend="json",
        target_backend="chroma",
    )

    assert migrated["sourceBackend"] == "json"
    assert migrated["targetBackend"] == "json"
    assert migrated["fallbackUsed"] is True
    assert migrated["collection"]["recordCount"] == 1


@pytest.mark.asyncio
async def test_chroma_vector_store_contract_when_dependency_is_installed(
    tmp_path: Path,
) -> None:
    pytest.importorskip("chromadb")
    store = ChromaVectorStore(tmp_path / "chroma")
    collection_ref = store.collection_ref(
        "chat-1",
        ChromaVectorStore.collection_id("chat-1", "embed-a", "chroma"),
    )

    await assert_basic_vector_store_contract(store, collection_ref)
