import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.execution_context import AISettingsResolver
from app.ai.vectorstores import JsonVectorStore, VectorStoreManager
from app.services.component_registry import CAPABILITY_KEYS
from app.services.document_service import DocumentService


def capability(
    capability_id: str,
    capability_type: str,
    available: bool = True,
) -> dict[str, object]:
    return {
        "id": capability_id,
        "label": capability_id,
        "type": capability_type,
        "available": available,
        "source": "test",
    }


def vector_capabilities(
    embedder_models: list[str] | None = None,
) -> dict[str, list[dict[str, object]]]:
    capabilities: dict[str, list[dict[str, object]]] = {
        key: [] for key in CAPABILITY_KEYS
    }
    capabilities["llmModels"] = [capability("qwen3:4b", "llmModel")]
    models = ["embed-a"] if embedder_models is None else embedder_models
    capabilities["embedderModels"] = [
        capability(model, "embedderModel")
        for model in models
    ]
    capabilities["ocrEngines"] = [capability("none", "ocrEngine")]
    capabilities["pdfParsers"] = []
    capabilities["chunkers"] = [
        capability("fixed", "chunker"),
        capability("recursive", "chunker"),
    ]
    capabilities["vectorDatabases"] = [
        capability("qdrant", "vectorDatabase"),
    ]
    capabilities["ragPipelines"] = [capability("basic", "ragPipeline")]
    capabilities["contextCompressors"] = [
        capability("none", "contextCompressor")
    ]
    return capabilities


class FakeComponentRegistry:
    def __init__(
        self,
        capabilities: dict[str, list[dict[str, object]]] | None = None,
    ) -> None:
        self._capabilities = capabilities or vector_capabilities()

    async def capabilities(self) -> dict[str, list[dict[str, object]]]:
        return self._capabilities


class FakeEmbedderProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    async def embed_texts(
        self,
        texts: list[str],
        model: str,
    ) -> list[list[float]]:
        self.calls.append((texts, model))
        return [self._embed(text) for text in texts]

    @staticmethod
    def _embed(text: str) -> list[float]:
        normalized = text.lower()
        return [
            1.0 if "apple" in normalized else 0.0,
            1.0 if "banana" in normalized else 0.0,
            1.0 if "carrot" in normalized else 0.0,
        ]


def configure_vector_tests(
    app: FastAPI,
    tmp_path: Path,
    capabilities: dict[str, list[dict[str, object]]] | None = None,
    chunk_size: int = 32,
    backend: str = "json",
) -> FakeEmbedderProvider:
    app.state.document_service = DocumentService(
        upload_directory=tmp_path / "uploads",
        max_upload_bytes=1024 * 1024,
        chunk_size=chunk_size,
    )
    app.state.vector_store_manager = VectorStoreManager(
        tmp_path / "vector_indexes",
        backend=backend,
    )
    app.state.vector_store = app.state.vector_store_manager.default_store()
    app.state.ai_settings_resolver = AISettingsResolver(
        FakeComponentRegistry(capabilities)
    )
    embedder = FakeEmbedderProvider()
    app.state.embedder_provider = embedder
    return embedder


def upload_document(
    client: TestClient,
    auth_headers: dict[str, str],
    conversation_id: str,
    content: bytes,
) -> dict[str, object]:
    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        data={
            "conversationId": conversation_id,
            "conversationSettings": json.dumps(
                {"embedderModel": "embed-a", "chunker": "fixed"}
            ),
        },
        files={"file": ("notes.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    return response.json()


def process_document(
    client: TestClient,
    auth_headers: dict[str, str],
    conversation_id: str,
    document_id: str,
) -> dict[str, object]:
    response = client.post(
        f"/documents/{document_id}/process",
        headers=auth_headers,
        json={
            "conversationId": conversation_id,
            "conversationSettings": {
                "embedderModel": "embed-a",
                "chunker": "fixed",
            },
        },
    )
    assert response.status_code == 200
    return response.json()


def index_document(
    client: TestClient,
    auth_headers: dict[str, str],
    conversation_id: str,
    document_id: str,
    embedder_model: str = "embed-a",
) -> dict[str, object]:
    response = client.post(
        f"/documents/{document_id}/index",
        headers=auth_headers,
        json={
            "conversationId": conversation_id,
            "conversationSettings": {
                "embedderModel": embedder_model,
                "chunker": "fixed",
                "vectorDatabase": "qdrant",
            },
        },
    )
    assert response.status_code == 200
    return response.json()


def test_cannot_index_unprocessed_document(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path)
    document = upload_document(client, auth_headers, "conversation-a", b"apple")

    response = client.post(
        f"/documents/{document['documentId']}/index",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )

    assert response.status_code == 400
    assert "processed before" in response.json()["detail"]


def test_cannot_index_malformed_chunks_artifact(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path)
    document = upload_document(client, auth_headers, "conversation-a", b"apple")
    process_document(client, auth_headers, "conversation-a", document["documentId"])
    chunks_path = (
        app.state.document_service.upload_directory
        / "conversation-a"
        / document["documentId"]
        / "chunks.json"
    )
    chunks_path.write_text(
        json.dumps(
            {
                "documentId": document["documentId"],
                "conversationId": "conversation-a",
                "chunks": [{"chunkId": "bad", "text": 42}],
            }
        ),
        encoding="utf-8",
    )

    response = client.post(
        f"/documents/{document['documentId']}/index",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )

    assert response.status_code == 400
    assert "indexable text chunks" in response.json()["detail"]


def test_cannot_index_without_valid_embedder(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path, vector_capabilities(embedder_models=[]))
    document = upload_document(client, auth_headers, "conversation-a", b"apple")
    process_document(client, auth_headers, "conversation-a", document["documentId"])

    response = client.post(
        f"/documents/{document['documentId']}/index",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )

    assert response.status_code == 400
    assert "valid available embedderModel" in response.json()["detail"]


def test_indexing_stores_vectors_under_correct_conversation_id(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path, chunk_size=64)
    document = upload_document(client, auth_headers, "conversation-a", b"apple chunk")
    process_document(client, auth_headers, "conversation-a", document["documentId"])

    summary = index_document(
        client,
        auth_headers,
        "conversation-a",
        document["documentId"],
    )

    assert summary["conversationId"] == "conversation-a"
    collection_path = (
        app.state.vector_store.index_directory
        / "conversation-a"
        / summary["collectionId"]
        / "index.json"
    )
    index_data = json.loads(collection_path.read_text(encoding="utf-8"))
    assert index_data["conversationId"] == "conversation-a"
    assert index_data["vectors"][0]["documentId"] == document["documentId"]


def test_indexing_batches_embedding_requests(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    embedder = configure_vector_tests(app, tmp_path, chunk_size=6)
    app.state.settings.embedding_batch_size = 2
    document = upload_document(
        client,
        auth_headers,
        "conversation-a",
        b"alpha beta gamma delta epsilon",
    )
    process_document(client, auth_headers, "conversation-a", document["documentId"])

    index_document(client, auth_headers, "conversation-a", document["documentId"])

    assert [len(texts) for texts, _model in embedder.calls] == [2, 2, 1]


def test_conversation_a_cannot_query_conversation_b_indexes(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path)
    document = upload_document(client, auth_headers, "conversation-a", b"apple")
    process_document(client, auth_headers, "conversation-a", document["documentId"])
    index_document(client, auth_headers, "conversation-a", document["documentId"])

    response = client.post(
        "/documents/search",
        headers=auth_headers,
        json={
            "conversationId": "conversation-b",
            "query": "apple",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_reindexing_replaces_document_vectors_instead_of_duplicating(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path, chunk_size=16)
    document = upload_document(
        client,
        auth_headers,
        "conversation-a",
        b"apple apple apple apple",
    )
    process_document(client, auth_headers, "conversation-a", document["documentId"])

    first = index_document(
        client,
        auth_headers,
        "conversation-a",
        document["documentId"],
    )
    second = index_document(
        client,
        auth_headers,
        "conversation-a",
        document["documentId"],
    )

    assert first["collectionId"] == second["collectionId"]
    assert first["collection"]["recordCount"] == second["collection"]["recordCount"]


def test_search_returns_ranked_chunks_and_respects_top_k(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path, chunk_size=32)
    document = upload_document(
        client,
        auth_headers,
        "conversation-a",
        b"apple pie\n\nbanana bread\n\ncarrot cake",
    )
    process_document(client, auth_headers, "conversation-a", document["documentId"])
    index_document(client, auth_headers, "conversation-a", document["documentId"])

    response = client.post(
        "/documents/search",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "query": "banana",
            "topK": 1,
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert "banana" in results[0]["text"]
    assert results[0]["score"] > 0


def test_query_embedder_must_match_collection_embedder(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(
        app,
        tmp_path,
        vector_capabilities(embedder_models=["embed-a", "embed-b"]),
    )
    document = upload_document(client, auth_headers, "conversation-a", b"apple")
    process_document(client, auth_headers, "conversation-a", document["documentId"])
    index_document(client, auth_headers, "conversation-a", document["documentId"])

    response = client.post(
        "/documents/search",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "query": "apple",
            "conversationSettings": {"embedderModel": "embed-b"},
        },
    )

    assert response.status_code == 409
    assert "Embedder mismatch" in response.json()["detail"]


def test_deleting_index_is_scoped_to_conversation(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path)
    document = upload_document(client, auth_headers, "conversation-a", b"apple")
    process_document(client, auth_headers, "conversation-a", document["documentId"])
    summary = index_document(
        client,
        auth_headers,
        "conversation-a",
        document["documentId"],
    )

    other_conversation = client.delete(
        f"/documents/indexes/{summary['collectionId']}",
        headers=auth_headers,
        params={"conversationId": "conversation-b"},
    )
    owning_conversation = client.delete(
        f"/documents/indexes/{summary['collectionId']}",
        headers=auth_headers,
        params={"conversationId": "conversation-a"},
    )

    assert other_conversation.status_code == 404
    assert owning_conversation.status_code == 200
    assert owning_conversation.json()["deleted"] is True


def test_vector_store_health_endpoint_reports_backends(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path)

    response = client.get("/vectorstores/health", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    backends = {item["id"]: item for item in payload["backends"]}
    assert payload["configuredBackend"] == "json"
    assert payload["activeBackend"] == "json"
    assert backends["json"]["available"] is True
    assert backends["qdrant"]["implemented"] in {True, False}
    assert backends["lancedb"]["available"] is False


def test_vector_store_export_import_and_migrate_endpoints(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_vector_tests(app, tmp_path)
    document = upload_document(client, auth_headers, "conversation-a", b"apple")
    process_document(client, auth_headers, "conversation-a", document["documentId"])
    summary = index_document(
        client,
        auth_headers,
        "conversation-a",
        document["documentId"],
    )

    export_response = client.get(
        "/vectorstores/collections/export",
        headers=auth_headers,
        params={
            "conversationId": "conversation-a",
            "collectionId": summary["collectionId"],
            "backend": "json",
        },
    )
    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["format"] == "local-ai-vector-collection-v1"
    assert payload["vectors"][0]["metadata"]["documentName"] == "notes.txt"

    import_response = client.post(
        "/vectorstores/collections/import",
        headers=auth_headers,
        json={"backend": "qdrant", "payload": payload},
    )
    assert import_response.status_code == 200
    assert import_response.json()["backend"] == "qdrant"
    assert import_response.json()["fallbackUsed"] is False

    migrate_response = client.post(
        "/vectorstores/collections/migrate",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "collectionId": summary["collectionId"],
            "sourceBackend": "json",
            "targetBackend": "lancedb",
        },
    )
    assert migrate_response.status_code == 200
    assert migrate_response.json()["targetBackend"] == "json"
    assert migrate_response.json()["fallbackUsed"] is True
