import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.execution_context import AISettingsResolver
from app.routers.chat import get_ollama_service
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


def document_capabilities(
    pdfplumber_available: bool = True,
) -> dict[str, list[dict[str, object]]]:
    capabilities: dict[str, list[dict[str, object]]] = {
        key: [] for key in CAPABILITY_KEYS
    }
    capabilities["llmModels"] = [capability("qwen3:4b", "llmModel")]
    capabilities["ocrEngines"] = [
        capability("none", "ocrEngine"),
        capability("tesseract", "ocrEngine", False),
    ]
    capabilities["pdfParsers"] = [
        capability("pymupdf", "pdfParser", False),
        capability("pdfplumber", "pdfParser", pdfplumber_available),
    ]
    capabilities["chunkers"] = [
        capability("fixed", "chunker"),
        capability("recursive", "chunker"),
        capability("semantic", "chunker"),
        capability("document-aware", "chunker"),
    ]
    capabilities["vectorDatabases"] = [capability("chroma", "vectorDatabase")]
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
        self._capabilities = capabilities or document_capabilities()

    async def capabilities(self) -> dict[str, list[dict[str, object]]]:
        return self._capabilities


class FakeOllamaService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, model: str, prompt: str) -> str:
        self.calls.append((model, prompt))
        return "Mocked local model response"

    async def list_installed_models(self) -> list[object]:
        return []


def configure_documents(
    app: FastAPI,
    tmp_path: Path,
    capabilities: dict[str, list[dict[str, object]]] | None = None,
    chunk_size: int = 24,
    max_chunks: int = 500,
) -> None:
    app.state.document_service = DocumentService(
        upload_directory=tmp_path / "uploads",
        max_upload_bytes=1024 * 1024,
        chunk_size=chunk_size,
        max_chunks=max_chunks,
    )
    app.state.ai_settings_resolver = AISettingsResolver(
        FakeComponentRegistry(capabilities)
    )


def upload_document(
    client: TestClient,
    auth_headers: dict[str, str],
    conversation_id: str,
    filename: str,
    content: bytes,
    settings: dict[str, str] | None = None,
    content_type: str = "text/plain",
) -> dict[str, object]:
    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        data={
            "conversationId": conversation_id,
            "conversationSettings": json.dumps(settings or {}),
        },
        files={"file": (filename, content, content_type)},
    )
    assert response.status_code == 200
    return response.json()


def process_document(
    client: TestClient,
    auth_headers: dict[str, str],
    conversation_id: str,
    document_id: str,
    settings: dict[str, str] | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/documents/{document_id}/process",
        headers=auth_headers,
        json={
            "conversationId": conversation_id,
            "conversationSettings": settings or {},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_upload_rejects_unsupported_file_types(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)

    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        data={"conversationId": "conversation-a"},
        files={"file": ("image.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400
    assert "Only .txt, .md, and .pdf" in response.json()["detail"]


def test_upload_stores_document_under_correct_conversation_id(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)

    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "../notes.txt",
        b"hello local document",
    )

    assert metadata["conversationId"] == "conversation-a"
    assert metadata["originalFilename"] == "notes.txt"
    assert metadata["storedFilename"] == "original.txt"
    stored_path = (
        app.state.document_service.upload_directory
        / "conversation-a"
        / metadata["documentId"]
        / "original"
        / "original.txt"
    )
    assert stored_path.read_text(encoding="utf-8") == "hello local document"


def test_conversation_cannot_access_another_conversation_document(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"private notes",
    )

    response = client.get(
        f"/documents/{metadata['documentId']}",
        headers=auth_headers,
        params={"conversationId": "conversation-b"},
    )

    assert response.status_code == 404


def test_txt_extraction_and_chunking_work(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path, chunk_size=18)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"alpha beta gamma delta epsilon",
        {"chunker": "fixed"},
    )

    summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        metadata["documentId"],
        {"chunker": "fixed"},
    )
    chunks = client.get(
        f"/documents/{metadata['documentId']}/chunks",
        headers=auth_headers,
        params={"conversationId": "conversation-a"},
    ).json()["chunks"]

    assert summary["status"] == "processed"
    assert summary["chunkCount"] == 2
    assert chunks[0]["documentId"] == metadata["documentId"]
    assert chunks[0]["conversationId"] == "conversation-a"
    assert chunks[0]["index"] == 0
    assert chunks[0]["charStart"] == 0
    assert chunks[0]["charEnd"] == 18
    assert chunks[0]["text"] == "alpha beta gamma d"
    assert chunks[0]["metadata"]["chunker"] == "fixed"


def test_document_chunking_respects_configured_max_chunks(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path, chunk_size=6, max_chunks=2)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"alpha beta gamma delta epsilon",
        {"chunker": "fixed"},
    )

    summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        metadata["documentId"],
        {"chunker": "fixed"},
    )
    chunks = client.get(
        f"/documents/{metadata['documentId']}/chunks",
        headers=auth_headers,
        params={"conversationId": "conversation-a"},
    ).json()["chunks"]

    assert summary["chunkCount"] == 2
    assert len(chunks) == 2
    assert any("configured limit" in warning for warning in summary["warnings"])


def test_markdown_extraction_works(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.md",
        b"# Title\n\nMarkdown body",
        {"chunker": "recursive"},
        "text/markdown",
    )

    summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        metadata["documentId"],
        {"chunker": "recursive"},
    )

    assert summary["status"] == "processed"
    assert summary["charLength"] == len("# Title\n\nMarkdown body")
    assert summary["chunkCount"] >= 1


def test_empty_text_document_fails_with_clear_error(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "empty.txt",
        b"   \n\t",
    )

    summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        metadata["documentId"],
    )

    assert summary["status"] == "failed"
    assert summary["chunkCount"] == 0
    assert "No text could be extracted" in summary["error"]


def test_pdf_parser_fallback_is_safe_when_parser_is_unavailable(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path, document_capabilities())
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "scan.pdf",
        b"%PDF-1.4\nnot really a pdf",
        {"pdfParser": "pymupdf", "ocrEngine": "none"},
        "application/pdf",
    )

    summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        metadata["documentId"],
        {"pdfParser": "pymupdf", "ocrEngine": "none"},
    )

    assert summary["status"] == "failed"
    assert summary["document"]["resolvedParser"] == "pdfplumber"
    assert summary["document"]["selectedSettings"]["pdfParser"] == "pymupdf"


def test_recursive_and_fixed_chunkers_work(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path, chunk_size=18)
    recursive_doc = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "recursive.txt",
        b"first paragraph\n\nsecond paragraph",
        {"chunker": "recursive"},
    )
    fixed_doc = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "fixed.txt",
        b"abcdefghij1234567890",
        {"chunker": "fixed"},
    )

    recursive_summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        recursive_doc["documentId"],
        {"chunker": "recursive"},
    )
    fixed_summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        fixed_doc["documentId"],
        {"chunker": "fixed"},
    )

    assert recursive_summary["document"]["actualChunker"] == "recursive"
    assert recursive_summary["chunkCount"] == 2
    assert fixed_summary["document"]["actualChunker"] == "fixed"
    assert fixed_summary["chunkCount"] == 2


def test_semantic_and_document_aware_chunkers_fallback_to_recursive(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    semantic_doc = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "semantic.md",
        b"semantic chunk fallback",
        {"chunker": "semantic"},
        "text/markdown",
    )
    document_aware_doc = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "document-aware.md",
        b"document aware fallback",
        {"chunker": "document-aware"},
        "text/markdown",
    )

    semantic_summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        semantic_doc["documentId"],
        {"chunker": "semantic"},
    )
    document_aware_summary = process_document(
        client,
        auth_headers,
        "conversation-a",
        document_aware_doc["documentId"],
        {"chunker": "document-aware"},
    )

    assert semantic_summary["document"]["actualChunker"] == "recursive"
    assert document_aware_summary["document"]["actualChunker"] == "recursive"
    assert "used recursive" in semantic_summary["warnings"][0]
    assert "used recursive" in document_aware_summary["warnings"][0]


def test_missing_or_corrupt_artifacts_do_not_crash_list_or_get(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"hello",
    )
    metadata_path = (
        app.state.document_service.upload_directory
        / "conversation-a"
        / metadata["documentId"]
        / "metadata.json"
    )
    metadata_path.write_text("{not valid json", encoding="utf-8")

    list_response = client.get(
        "/documents",
        headers=auth_headers,
        params={"conversationId": "conversation-a"},
    )
    get_response = client.get(
        f"/documents/{metadata['documentId']}",
        headers=auth_headers,
        params={"conversationId": "conversation-a"},
    )

    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert list_response.json()["documents"][0]["status"] == "failed"
    assert get_response.json()["status"] == "failed"


def test_metadata_identity_mismatch_is_reported_as_failed_artifact(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"hello",
    )
    metadata_path = (
        app.state.document_service.upload_directory
        / "conversation-a"
        / metadata["documentId"]
        / "metadata.json"
    )
    stored = json.loads(metadata_path.read_text(encoding="utf-8"))
    stored["documentId"] = "0" * 32
    metadata_path.write_text(json.dumps(stored), encoding="utf-8")

    response = client.get(
        f"/documents/{metadata['documentId']}",
        headers=auth_headers,
        params={"conversationId": "conversation-a"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["documentId"] == metadata["documentId"]
    assert "documentId does not match" in payload["error"]


def test_missing_original_artifact_returns_not_found(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"hello",
    )
    original_path = (
        app.state.document_service.upload_directory
        / "conversation-a"
        / metadata["documentId"]
        / "original"
        / "original.txt"
    )
    original_path.unlink()

    response = client.post(
        f"/documents/{metadata['documentId']}/process",
        headers=auth_headers,
        json={"conversationId": "conversation-a", "conversationSettings": {}},
    )

    assert response.status_code == 404
    assert "Original document artifact" in response.json()["detail"]


def test_invalid_chunks_artifact_returns_warning_instead_of_crashing(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    metadata = upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"hello document",
    )
    process_document(client, auth_headers, "conversation-a", metadata["documentId"])
    chunks_path = (
        app.state.document_service.upload_directory
        / "conversation-a"
        / metadata["documentId"]
        / "chunks.json"
    )
    chunks_path.write_text(json.dumps({"chunks": {"bad": "shape"}}), encoding="utf-8")

    response = client.get(
        f"/documents/{metadata['documentId']}/chunks",
        headers=auth_headers,
        params={"conversationId": "conversation-a"},
    )

    assert response.status_code == 200
    assert response.json()["chunks"] == []
    assert response.json()["warning"] == "Chunks artifact is invalid."


def test_uploaded_documents_do_not_affect_existing_chat_flow(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_documents(app, tmp_path)
    upload_document(
        client,
        auth_headers,
        "conversation-a",
        "notes.txt",
        b"document text should not enter chat prompt",
    )
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Hello",
                "conversationSettings": {"llmModel": "qwen3:4b"},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"] == "Mocked local model response"
    assert fake_ollama.calls == [("qwen3:4b", "Hello")]
