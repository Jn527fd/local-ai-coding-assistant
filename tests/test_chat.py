import asyncio
import json
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.ai.components import Chunk, ComponentUnavailableError
from app.ai.execution_context import AISettingsResolver
from app.ai.ocr import OCRResult
from app.ai.pipelines.retrieval import DocumentRetrievalPipeline
from app.ai.rerankers import RerankResult
from app.ai.vectorstores import JsonVectorStore, QdrantVectorStore, VectorStoreError
from app.routers.chat import (
    get_conversation_memory_service,
    get_ollama_service,
    get_vision_artifact_service,
)
from app.schemas.memories import MemoryRecord
from app.services.component_registry import CAPABILITY_KEYS
from app.services.conversation_memory import MemoryOperationResult
from app.services.document_service import DocumentService
from app.services.ollama_service import InstalledOllamaModel
from app.services.vision_artifacts import VisionArtifactService


class FakeOllamaService:
    """Small in-memory replacement for the real Ollama HTTP client."""

    def __init__(
        self,
        installed_models: list[InstalledOllamaModel] | None = None,
        summary_response: str = "Condensed memory summary.",
        chat_response: str = "Mocked local model response",
        vision_response: str = (
            '{"visibleText":["Traceback (most recent call last):"],'
            '"errors":["ModuleNotFoundError: No module named qdrant_client"],'
            '"filePaths":["backend/app/main.py"],'
            '"code":["from qdrant_client import QdrantClient"],'
            '"uiElements":["terminal"],'
            '"observations":["The screenshot shows a Python import error."],'
            '"uncertainties":[]}'
        ),
        fail_summary: bool = False,
        fail_vision: bool = False,
    ) -> None:
        self.calls: list[tuple[str, str, list[str]]] = []
        self.installed_models = installed_models or []
        self.summary_response = summary_response
        self.chat_response = chat_response
        self.vision_response = vision_response
        self.fail_summary = fail_summary
        self.fail_vision = fail_vision

    async def generate(
        self,
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ) -> str:
        self.calls.append((model, prompt, list(images or [])))
        if images:
            if self.fail_vision:
                raise ComponentUnavailableError("vision failed")
            return self.vision_response
        if "Memory summary:" in prompt:
            if self.fail_summary:
                raise ComponentUnavailableError("summary failed")
            return self.summary_response
        return self.chat_response

    async def list_installed_models(self) -> list[InstalledOllamaModel]:
        return list(self.installed_models)


class FakeComponentRegistry:
    def __init__(
        self,
        capabilities: dict[str, list[dict[str, object]]],
    ) -> None:
        self._capabilities = capabilities

    async def capabilities(self) -> dict[str, list[dict[str, object]]]:
        return self._capabilities


class FakeEmbedderProvider:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[list[str], str]] = []

    async def embed_texts(
        self,
        texts: list[str],
        model: str,
    ) -> list[list[float]]:
        self.calls.append((texts, model))
        if self.fail:
            raise ComponentUnavailableError("embedder unavailable")
        return [self.embed(text) for text in texts]

    @staticmethod
    def embed(text: str) -> list[float]:
        normalized = text.lower()
        return [
            1.0 if "apple" in normalized else 0.0,
            1.0 if "banana" in normalized else 0.0,
            1.0 if "carrot" in normalized else 0.0,
            1.0 if "react" in normalized else 0.0,
            (
                1.0
                if "certificate" in normalized
                or "certification" in normalized
                else 0.0
            ),
            1.0 if "program" in normalized else 0.0,
        ]


class FakeRerankerProvider:
    def __init__(
        self,
        scores_by_chunk: dict[str, float] | None = None,
        fail: bool = False,
    ) -> None:
        self.scores_by_chunk = scores_by_chunk or {}
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    async def rerank(
        self,
        query: str,
        candidate_chunks: list[object],
        model: str,
        settings: dict[str, object],
    ) -> RerankResult:
        self.calls.append(
            {
                "query": query,
                "candidateCount": len(candidate_chunks),
                "model": model,
                "settings": settings,
            }
        )
        if self.fail:
            raise ComponentUnavailableError("reranker failed")

        scored = []
        for source in candidate_chunks:
            score = self.scores_by_chunk.get(source.chunk_id, 0.0)
            scored.append(
                replace(
                    source,
                    score=score,
                    rerank_score=score,
                )
            )
        scored.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return RerankResult(sources=scored, warnings=[])


class FakeConversationMemoryService:
    def __init__(self, context: str = "") -> None:
        self.context = context
        self.retrieve_calls: list[dict[str, object]] = []
        self.store_calls: list[dict[str, object]] = []

    async def retrieve(self, **kwargs) -> MemoryOperationResult:
        self.retrieve_calls.append(kwargs)
        return MemoryOperationResult(memories=[], warnings=[])

    def list(self, **kwargs) -> MemoryOperationResult:
        return MemoryOperationResult(
            memories=[
                MemoryRecord(
                    id="memory-a",
                    workspaceId="default",
                    conversationId=kwargs.get("conversation_id"),
                    text="I prefer TypeScript examples.",
                    type="preference",
                    importance=0.8,
                    sourceHash="hash-a",
                )
            ],
            warnings=[],
        )

    def format_memory_context(self, memories) -> str:
        return self.context

    async def store_from_message(self, **kwargs) -> MemoryOperationResult:
        self.store_calls.append(kwargs)
        return MemoryOperationResult(memories=[], warnings=[])


class FakePDFOCREngine:
    engine_id = "ocrmypdf"

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[Path] = []

    def extract_pdf_text(self, file_path: Path, settings: dict[str, object]) -> OCRResult:
        self.calls.append(file_path)
        return OCRResult(text=self.text, warnings=[], metadata={})


class FakeStreamingLLMProvider:
    def __init__(
        self,
        chunks: list[str] | None = None,
        fail: bool = False,
    ) -> None:
        self.chunks = chunks or ["Streamed ", "answer"]
        self.fail = fail
        self.calls: list[dict[str, object]] = []
        self.ollama_service: object | None = None

    async def generate(self, prompt, history, settings):
        return "".join(self.chunks)

    async def stream_generate(self, prompt, history, settings):
        self.calls.append(
            {
                "prompt": prompt,
                "history": history,
                "settings": settings,
            }
        )
        if self.fail:
            raise ComponentUnavailableError("streaming failed")
        for chunk in self.chunks:
            yield chunk


class FailingVectorStore:
    async def list_collections(
        self,
        conversation_id: str,
    ) -> list[dict[str, object]]:
        raise VectorStoreError("vector store unavailable")


def installed_model(name: str) -> InstalledOllamaModel:
    return InstalledOllamaModel(
        name=name,
        size_bytes=2_500_000_000,
        parameter_size="4.0B",
        parameters_billion=4.0,
        family=name.split(":", maxsplit=1)[0],
        quantization_level="Q4_K_M",
    )


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


def chat_capabilities(
    embedder_models: list[str] | None = None,
    reranker_models: list[str] | None = None,
    vision_models: list[str] | None = None,
) -> dict[str, list[dict[str, object]]]:
    capabilities: dict[str, list[dict[str, object]]] = {
        key: [] for key in CAPABILITY_KEYS
    }
    capabilities["llmModels"] = [capability("qwen3:4b", "llmModel")]
    capabilities["embedderModels"] = [
        capability(model, "embedderModel")
        for model in (["embed-a"] if embedder_models is None else embedder_models)
    ]
    capabilities["rerankerModels"] = [
        capability(model, "rerankerModel")
        for model in (
            ["rerank-a"] if reranker_models is None else reranker_models
        )
    ]
    capabilities["visionModels"] = [
        capability(model, "visionModel")
        for model in ([] if vision_models is None else vision_models)
    ]
    capabilities["ocrEngines"] = [capability("none", "ocrEngine")]
    capabilities["chunkers"] = [
        capability("fixed", "chunker"),
        capability("recursive", "chunker"),
    ]
    capabilities["vectorDatabases"] = [
        capability("qdrant", "vectorDatabase"),
    ]
    capabilities["ragPipelines"] = [
        capability("basic", "ragPipeline"),
        capability("hybrid", "ragPipeline"),
        capability("reranked", "ragPipeline"),
        capability("graph", "ragPipeline"),
        capability("agentic", "ragPipeline"),
    ]
    capabilities["contextCompressors"] = [
        capability("none", "contextCompressor"),
        capability("token", "contextCompressor"),
        capability("summarizer", "contextCompressor"),
        capability("semantic", "contextCompressor"),
        capability("memory", "contextCompressor"),
    ]
    return capabilities


def configure_chat_rag_tests(
    app: FastAPI,
    tmp_path: Path,
    capabilities: dict[str, list[dict[str, object]]] | None = None,
    embedder: FakeEmbedderProvider | None = None,
    reranker: FakeRerankerProvider | None = None,
) -> FakeEmbedderProvider:
    app.state.ai_settings_resolver = AISettingsResolver(
        FakeComponentRegistry(capabilities or chat_capabilities())
    )
    app.state.vector_store = JsonVectorStore(tmp_path / "vector_indexes")
    app.state.embedder_provider = embedder or FakeEmbedderProvider()
    app.state.reranker_provider = reranker or FakeRerankerProvider()
    return app.state.embedder_provider


def seed_vector_index(
    app: FastAPI,
    conversation_id: str,
    embedder_model: str = "embed-a",
    vector_database: str = "qdrant",
    document_id: str = "doc-1",
    chunk_texts: list[str] | None = None,
    chunk_metadata: list[dict[str, object]] | None = None,
) -> None:
    texts = chunk_texts or ["apple pie", "banana bread"]
    chunks = []
    for index, text in enumerate(texts):
        keyword = (text.split(maxsplit=1)[0].lower() if text.split() else f"empty-{index}")
        chunk_id = f"chunk-{keyword}"
        metadata = {
            "documentId": document_id,
            "documentName": "notes.txt",
            "chunkId": chunk_id,
            "chunkIndex": index,
        }
        if chunk_metadata and index < len(chunk_metadata):
            metadata.update(chunk_metadata[index])
        chunks.append(
            Chunk(
                id=chunk_id,
                text=text,
                metadata=metadata,
            )
        )
    collection_id = JsonVectorStore.collection_id(
        conversation_id=conversation_id,
        embedder_model=embedder_model,
        vector_database=vector_database,
    )
    collection_ref = app.state.vector_store.collection_ref(
        conversation_id,
        collection_id,
    )
    asyncio.run(
        app.state.vector_store.upsert(
            collection=collection_ref,
            chunks=chunks,
            embeddings=[FakeEmbedderProvider.embed(chunk.text) for chunk in chunks],
            metadata={
                "embedderModel": embedder_model,
                "vectorDatabase": vector_database,
                "documentIds": [document_id],
                "internalStore": "json",
            },
        )
    )


@pytest.mark.asyncio
async def test_qdrant_retrieval_pipeline_returns_indexed_sources(
    tmp_path: Path,
) -> None:
    pytest.importorskip("qdrant_client")
    store = QdrantVectorStore(tmp_path / "qdrant")
    embedder = FakeEmbedderProvider()
    capabilities = chat_capabilities()
    resolver = AISettingsResolver(FakeComponentRegistry(capabilities))
    execution_context = await resolver.resolve(
        conversation_settings=None,
        active_model="qwen3:4b",
        conversation_id="chat-qdrant",
    )
    chunks = [
        Chunk(
            id="chunk-apple",
            text="apple tart instructions",
            metadata={
                "documentId": "doc-apple",
                "documentName": "recipes.txt",
                "chunkId": "chunk-apple",
                "chunkIndex": 0,
            },
        ),
        Chunk(
            id="chunk-banana",
            text="banana bread notes",
            metadata={
                "documentId": "doc-banana",
                "documentName": "recipes.txt",
                "chunkId": "chunk-banana",
                "chunkIndex": 1,
            },
        ),
    ]
    collection_id = store.collection_id(
        "chat-qdrant",
        "embed-a",
        "qdrant",
    )
    try:
        await store.upsert(
            collection=store.collection_ref("chat-qdrant", collection_id),
            chunks=chunks,
            embeddings=[embedder.embed(chunk.text) for chunk in chunks],
            metadata={
                "embedderModel": "embed-a",
                "vectorDatabase": "qdrant",
                "documentIds": ["doc-apple", "doc-banana"],
            },
        )

        result = await DocumentRetrievalPipeline(embedder, store).retrieve(
            query="apple",
            conversation_id="chat-qdrant",
            execution_context=execution_context,
            top_k=1,
        )
        assert result.rag_used is True
        assert result.sources[0].document_id == "doc-apple"
        assert result.sources[0].collection_id == collection_id
        assert result.sources[0].vector_score > 0
    finally:
        store.close()


def seed_processed_document_metadata(
    app: FastAPI,
    conversation_id: str,
    document_id: str,
    filename: str = "notes.txt",
    status: str = "processed",
    chunk_count: int = 2,
    error: str | None = None,
) -> None:
    document_directory = (
        app.state.document_service.upload_directory
        / conversation_id
        / document_id
    )
    document_directory.mkdir(parents=True, exist_ok=True)
    metadata = {
        "documentId": document_id,
        "conversationId": conversation_id,
        "originalFilename": filename,
        "storedFilename": "original.txt",
        "storedPath": f"{conversation_id}/{document_id}/original/original.txt",
        "mimeType": "text/plain",
        "size": 24,
        "extension": ".txt",
        "createdAt": "2026-07-05T00:00:00+00:00",
        "processedAt": "2026-07-05T00:00:01+00:00",
        "extractionWarnings": [],
        "extractionDiagnostics": {
            "charLength": 42,
            "chunkCount": chunk_count,
        },
        "chunkCount": chunk_count,
        "status": status,
        "error": error,
    }
    (document_directory / "metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )


def vector_index_path(
    app: FastAPI,
    conversation_id: str,
    embedder_model: str = "embed-a",
    vector_database: str = "qdrant",
) -> Path:
    collection_id = JsonVectorStore.collection_id(
        conversation_id=conversation_id,
        embedder_model=embedder_model,
        vector_database=vector_database,
    )
    return (
        app.state.vector_store.index_directory
        / conversation_id
        / collection_id
        / "index.json"
    )


def pdf_bytes(text: str | list[str]) -> bytes:
    import fitz

    document = fitz.open()
    try:
        page_texts = text if isinstance(text, list) else [text]
        for page_text in page_texts:
            page = document.new_page()
            if page_text:
                page.insert_text((72, 72), page_text)
        return bytes(document.write())
    finally:
        document.close()


def image_like_pdf_bytes(embedded_text: str = "Name") -> bytes:
    import fitz

    document = fitz.open()
    try:
        page = document.new_page()
        page.draw_rect(fitz.Rect(72, 90, 460, 250), fill=(0.9, 0.9, 0.9))
        if embedded_text:
            page.insert_text((72, 72), embedded_text)
        return bytes(document.write())
    finally:
        document.close()


def pdf_chat_settings() -> dict[str, str]:
    return {
        "embedderModel": "embed-a",
        "pdfParser": "pdfplumber",
        "ocrEngine": "none",
        "chunker": "recursive",
        "vectorDatabase": "qdrant",
        "ragPipeline": "basic",
        "contextCompressor": "none",
    }


def chat_capabilities_with_pdf() -> dict[str, list[dict[str, object]]]:
    capabilities = chat_capabilities()
    capabilities["pdfParsers"] = [capability("pdfplumber", "pdfParser")]
    capabilities["ocrEngines"] = [
        capability("none", "ocrEngine"),
        capability("ocrmypdf", "ocrEngine"),
    ]
    return capabilities


def upload_process_index_pdf(
    client: TestClient,
    auth_headers: dict[str, str],
    conversation_id: str,
    filename: str,
    content: bytes,
    settings: dict[str, str],
) -> str:
    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers,
        data={
            "conversationId": conversation_id,
            "conversationSettings": json.dumps(settings),
        },
        files={"file": (filename, content, "application/pdf")},
    )
    assert upload_response.status_code == 200, upload_response.text
    document_id = upload_response.json()["documentId"]

    process_response = client.post(
        f"/documents/{document_id}/process",
        headers=auth_headers,
        json={
            "conversationId": conversation_id,
            "conversationSettings": settings,
        },
    )
    assert process_response.status_code == 200, process_response.text
    if process_response.json()["status"] != "processed":
        return document_id

    index_response = client.post(
        f"/documents/{document_id}/index",
        headers=auth_headers,
        json={
            "conversationId": conversation_id,
            "conversationSettings": settings,
        },
    )
    assert index_response.status_code == 200, index_response.text
    assert index_response.json()["indexedChunks"] >= 1
    return document_id


def test_chat_returns_mocked_ollama_answer(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "model": "qwen3:4b",
                "message": "Explain dependency injection briefly.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["model"] == "qwen3:4b"
    assert response.json()["answer"] == "Mocked local model response"
    assert response.json()["ragUsed"] is False
    assert response.json()["ragWarnings"] == []
    assert response.json()["rerankingUsed"] is False
    assert response.json()["rerankWarnings"] == []
    assert response.json()["sources"] == []
    assert fake_ollama.calls == [
        ("qwen3:4b", "Explain dependency injection briefly.", [])
    ]


def test_chat_hides_model_reasoning_blocks(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService(
        chat_response="<think>private chain of thought</think>\nVisible answer"
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={"message": "Hello"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"] == "Visible answer"


def test_chat_injects_retrieved_conversation_memory(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    fake_memory = FakeConversationMemoryService(
        "Long-term project memory from Qdrant:\n"
        "1. [preference] I prefer TypeScript examples."
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    app.dependency_overrides[get_conversation_memory_service] = lambda: fake_memory

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "Show an example.",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = fake_ollama.calls[0][1]
    assert "[Conversation Memory]" in prompt
    assert "I prefer TypeScript examples." in prompt
    assert fake_memory.retrieve_calls[0]["conversation_id"] == "conversation-a"
    assert fake_memory.store_calls


def test_chat_sends_only_explicit_history_as_context(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "And how is it declared?",
                "history": [
                    {
                        "role": "user",
                        "content": "What is a FastAPI dependency?",
                    },
                    {
                        "role": "assistant",
                        "content": "It provides reusable request-time values.",
                    },
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = fake_ollama.calls[0][1]
    assert "User: What is a FastAPI dependency?" in prompt
    assert "Assistant: It provides reusable request-time values." in prompt
    assert "User: And how is it declared?" in prompt


def test_chat_includes_conversation_system_prompt_in_model_prompt(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Say hello.",
                "systemPrompt": (
                    "Always answer in a concise, friendly tone and mention "
                    "local-only execution."
                ),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = fake_ollama.calls[0][1]
    assert "[System Instructions]" in prompt
    assert "Always answer in a concise, friendly tone" in prompt
    assert "local-only execution" in prompt
    assert prompt.index("[System Instructions]") < prompt.index("User: Say hello.")


def test_chat_bounds_large_history_to_recent_context(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index} " + ("x" * 2_000),
        }
        for index in range(12)
    ]

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Use the most recent context.",
                "history": history,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = fake_ollama.calls[0][1]
    assert len(prompt) <= app.state.settings.chat_context_max_chars
    assert "message-11" in prompt
    assert "message-0" not in prompt


def test_context_compressor_none_preserves_prompt_behavior(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "And how is it declared?",
                "conversationSettings": {"contextCompressor": "none"},
                "history": [
                    {
                        "role": "user",
                        "content": "What is a FastAPI dependency?",
                    },
                    {
                        "role": "assistant",
                        "content": "It provides reusable request-time values.",
                    },
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = fake_ollama.calls[0][1]
    assert "User: What is a FastAPI dependency?" in prompt
    assert "Assistant: It provides reusable request-time values." in prompt
    assert "User: And how is it declared?" in prompt
    assert response.json()["compressionUsed"] is False
    assert response.json()["compressorMode"] == "auto"


def test_token_compression_trims_older_history_first_and_preserves_latest(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index} " + ("x" * 1_500),
        }
        for index in range(14)
    ]
    latest_message = "Keep this latest request intact."

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": latest_message,
                "conversationSettings": {"contextCompressor": "token"},
                "history": history,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    prompt = fake_ollama.calls[0][1]
    assert payload["compressionUsed"] is True
    assert payload["compressorMode"] == "auto"
    assert payload["compressionStats"]["messagesTrimmed"] > 0
    assert "message-0" not in prompt
    assert "message-13" in prompt
    assert latest_message in prompt


def test_token_compression_trims_retrieved_context_after_history(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    seed_vector_index(
        app,
        "conversation-a",
        chunk_texts=[
            "banana " + ("context " * 1_500),
            "apple " + ("context " * 1_500),
        ],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "hybrid",
                    "contextCompressor": "token",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["compressionUsed"] is True
    assert payload["compressionStats"]["messagesTrimmed"] == 0
    assert payload["compressionStats"]["contextTrimmed"] > 0
    assert payload["sources"][0]["sourceNumber"] == 1
    assert payload["sources"][0]["finalRank"] == 1
    assert "[truncated]" in payload["sources"][0]["textPreview"]


def test_summarizer_compression_generates_memory_and_keeps_recent_messages(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService(summary_response="Remember the API design.")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index}",
        }
        for index in range(12)
    ]

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "What should we do next?",
                "conversationSettings": {"contextCompressor": "summarizer"},
                "history": history,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["compressorMode"] == "auto"
    assert payload["compressionStats"]["summaryGenerated"] is False

    final_prompt = fake_ollama.calls[-1][1]
    assert "message-11" in final_prompt
    assert "message-0" in final_prompt
    assert "What should we do next?" in final_prompt


def test_summarizer_failure_falls_back_safely_with_warning(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService(fail_summary=True)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index} " + ("x" * 900),
        }
        for index in range(14)
    ]

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Keep answering.",
                "conversationSettings": {"contextCompressor": "summarizer"},
                "history": history,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["compressionUsed"] is True
    assert payload["compressorMode"] == "auto"
    assert "Context management is automatic" in payload["compressionWarnings"][0]


def test_semantic_compression_falls_back_to_token_with_warning(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index} " + ("x" * 1_500),
        }
        for index in range(14)
    ]

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Use fallback compression.",
                "conversationSettings": {"contextCompressor": "semantic"},
                "history": history,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["compressionUsed"] is True
    assert payload["compressorMode"] == "auto"
    assert "Context management is automatic" in payload[
        "compressionWarnings"
    ][0]
    assert payload["compressionStats"]["messagesTrimmed"] > 0


def test_memory_compression_falls_back_to_summarizer_with_warning(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService(summary_response="Persistent memory summary.")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index}",
        }
        for index in range(12)
    ]

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Continue with memory.",
                "conversationSettings": {"contextCompressor": "memory"},
                "history": history,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["compressionUsed"] is False
    assert payload["compressorMode"] == "auto"
    assert payload["compressionStats"]["summaryGenerated"] is False
    assert "Context management is automatic" in payload[
        "compressionWarnings"
    ][0]


def test_chat_uses_conversation_llm_model_when_available(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService(
        [
            installed_model("qwen3:4b"),
            installed_model("llama3.2:3b"),
        ]
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Use this chat model.",
                "conversationSettings": {
                    "llmModel": "llama3.2:3b",
                    "embedderModel": "nomic-embed-text",
                    "ocrEngine": "none",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["model"] == "llama3.2:3b"
    assert fake_ollama.calls[0][0] == "llama3.2:3b"


def test_chat_falls_back_to_global_model_when_conversation_llm_is_invalid(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService([installed_model("qwen3:4b")])
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Use fallback.",
                "conversationSettings": {
                    "llmModel": "missing-model:latest",
                    "chunker": "recursive",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["model"] == "qwen3:4b"
    assert fake_ollama.calls[0][0] == "qwen3:4b"


def test_chat_uses_selected_vision_model_for_image_request(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(
        app,
        tmp_path,
        capabilities=chat_capabilities(vision_models=["llava:latest"]),
    )
    vision_service = VisionArtifactService(tmp_path / "vision", fake_ollama)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    app.dependency_overrides[get_vision_artifact_service] = lambda: vision_service

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "Describe this image.",
                "messageId": "message-a",
                "conversationSettings": {
                    "llmModel": "qwen3:4b",
                    "visionModel": "llava:latest",
                },
                "images": [
                    {
                        "id": "image-a",
                        "name": "tiny.png",
                        "mimeType": "image/png",
                        "data": "aW1hZ2UtYnl0ZXM=",
                    }
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["model"] == "qwen3:4b"
    assert payload["visionUsed"] is True
    assert payload["visionModel"] == "llava:latest"
    assert fake_ollama.calls[0][0] == "llava:latest"
    assert fake_ollama.calls[0][2] == ["aW1hZ2UtYnl0ZXM="]
    assert fake_ollama.calls[1][0] == "qwen3:4b"
    assert fake_ollama.calls[1][2] == []
    assert "Structured image evidence" in fake_ollama.calls[1][1]
    assert "ModuleNotFoundError: No module named qdrant_client" in fake_ollama.calls[1][1]
    listed = vision_service.retrieve_relevant("conversation-a", "qdrant_client")
    assert listed.artifacts[0].messageId == "message-a"
    assert listed.artifacts[0].imageId == "image-a"


def test_chat_falls_back_when_image_request_has_no_available_vision_model(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Describe this image.",
                "conversationSettings": {"llmModel": "qwen3:4b"},
                "images": [
                    {
                        "name": "tiny.png",
                        "mimeType": "image/png",
                        "data": "aW1hZ2UtYnl0ZXM=",
                    }
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    payload = response.json()
    assert response.status_code == 200
    assert payload["model"] == "qwen3:4b"
    assert payload["visionUsed"] is False
    assert "requires a valid available vision model" in payload["visionWarnings"][0]
    assert fake_ollama.calls[0][0] == "qwen3:4b"
    assert fake_ollama.calls[0][2] == []


def test_chat_reuses_prior_image_artifact_for_multiturn_continuity(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(
        app,
        tmp_path,
        capabilities=chat_capabilities(vision_models=["llava:latest"]),
    )
    vision_service = VisionArtifactService(tmp_path / "vision", fake_ollama)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    app.dependency_overrides[get_vision_artifact_service] = lambda: vision_service

    try:
        first = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "messageId": "message-a",
                "message": "What error is in this screenshot?",
                "conversationSettings": {
                    "llmModel": "qwen3:4b",
                    "visionModel": "llava:latest",
                },
                "images": [
                    {
                        "id": "image-a",
                        "name": "tiny.png",
                        "mimeType": "image/png",
                        "data": "aW1hZ2UtYnl0ZXM=",
                    }
                ],
            },
        )
        second = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "messageId": "message-b",
                "message": "Which file path did the screenshot mention?",
                "conversationSettings": {
                    "llmModel": "qwen3:4b",
                    "visionModel": "llava:latest",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    final_text_prompt = fake_ollama.calls[-1][1]
    assert "Structured image evidence" in final_text_prompt
    assert "backend/app/main.py" in final_text_prompt


def test_chat_rejects_invalid_image_base64(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(
        app,
        tmp_path,
        capabilities=chat_capabilities(vision_models=["llava:latest"]),
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Describe this image.",
                "conversationSettings": {"visionModel": "llava:latest"},
                "images": [
                    {
                        "name": "broken.png",
                        "mimeType": "image/png",
                        "data": "not base64!",
                    }
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "not valid base64" in response.json()["detail"]
    assert fake_ollama.calls == []


def test_chat_stream_returns_progress_tokens_and_done(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService([installed_model("qwen3:4b")])
    streaming_provider = FakeStreamingLLMProvider(["Hello", " stream"])
    streaming_provider.ollama_service = fake_ollama
    app.state.llm_provider = streaming_provider
    configure_chat_rag_tests(app, tmp_path)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        with client.stream(
            "POST",
            "/chat/stream",
            headers=auth_headers,
            json={
                "message": "Stream please.",
                "conversationSettings": {"llmModel": "qwen3:4b"},
            },
        ) as response:
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: progress" in body
    assert "event: metadata" in body
    assert 'event: token\ndata: {"text": "Hello"}' in body
    assert 'event: token\ndata: {"text": " stream"}' in body
    assert "event: done" in body
    assert '"answer": "Hello stream"' in body
    assert streaming_provider.calls[0]["settings"]["model"] == "qwen3:4b"


def test_chat_stream_hides_model_reasoning_blocks(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService([installed_model("qwen3:4b")])
    streaming_provider = FakeStreamingLLMProvider(
        ["Hello ", "<thi", "nk>private", " reasoning</thi", "nk>answer"]
    )
    streaming_provider.ollama_service = fake_ollama
    app.state.llm_provider = streaming_provider
    configure_chat_rag_tests(app, tmp_path)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        with client.stream(
            "POST",
            "/chat/stream",
            headers=auth_headers,
            json={
                "message": "Stream please.",
                "conversationSettings": {"llmModel": "qwen3:4b"},
            },
        ) as response:
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "private" not in body
    assert "reasoning" not in body
    assert '"answer": "Hello answer"' in body


def test_chat_stream_reports_generation_errors_as_error_events(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService([installed_model("qwen3:4b")])
    streaming_provider = FakeStreamingLLMProvider(fail=True)
    streaming_provider.ollama_service = fake_ollama
    app.state.llm_provider = streaming_provider
    configure_chat_rag_tests(app, tmp_path)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        with client.stream(
            "POST",
            "/chat/stream",
            headers=auth_headers,
            json={
                "message": "Stream please.",
                "conversationSettings": {"llmModel": "qwen3:4b"},
            },
        ) as response:
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "event: error" in body
    assert '"status": 503' in body
    assert "streaming failed" in body


def test_basic_rag_pipeline_does_not_retrieve_documents(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(app, tmp_path)
    seed_vector_index(app, "conversation-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What mentions banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ragUsed"] is False
    assert response.json()["sources"] == []
    assert fake_embedder.calls == []
    assert "<document_context>" not in fake_ollama.calls[0][1]


def test_attached_document_ids_force_retrieval_with_basic_pipeline(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(app, tmp_path)
    document_id = "a" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        document_id,
        filename="certificates.pdf",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=document_id,
        chunk_texts=[
            "certificate for local AI training completion",
            "resume details not relevant",
        ],
        chunk_metadata=[
            {"documentName": "certificates.pdf"},
            {"documentName": "certificates.pdf"},
        ],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is this document?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {
                    "enabled": True,
                    "includeSources": True,
                },
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ragUsed"] is True
    assert payload["sources"][0]["documentId"] == document_id
    assert payload["sources"][0]["documentName"] == "certificates.pdf"
    assert "certificate" in payload["sources"][0]["textPreview"]
    prompt = fake_ollama.calls[0][1]
    assert "<document_context>" in prompt
    assert "Source 1: certificates.pdf" in prompt
    assert "certificate for local AI training completion" in prompt
    assert fake_embedder.calls == [(["What is this document?"], "embed-a")]


def test_uploaded_pdf_question_answers_from_extracted_document_context(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    bad_model_answer = (
        "To view the contents of Certificates.pdf, please ensure it's attached "
        "to your current message or a conversation document."
    )
    fake_ollama = FakeOllamaService(chat_response=bad_model_answer)
    configure_chat_rag_tests(app, tmp_path, capabilities=chat_capabilities_with_pdf())
    settings = pdf_chat_settings()
    certificate_text = (
        "This certificate is for Junior Software Engineer AI-Native "
        "Development Program."
    )
    document_id = upload_process_index_pdf(
        client,
        auth_headers,
        "conversation-a",
        "Certificates.pdf",
        pdf_bytes(certificate_text),
        settings,
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is in this document?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": settings,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ragUsed"] is True
    assert payload["sources"]
    assert payload["sources"][0]["documentId"] == document_id
    assert certificate_text in payload["answer"]
    assert "please ensure" not in payload["answer"].lower()
    prompt = fake_ollama.calls[0][1]
    assert "<document_context>" in prompt
    assert "</document_context>" in prompt
    assert certificate_text in prompt
    assert "Do not claim you cannot access the file" in prompt


def test_document_followup_reuses_indexed_pdf_context_without_reattaching(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService(
        chat_response="I cannot access the document unless you attach it."
    )
    configure_chat_rag_tests(app, tmp_path, capabilities=chat_capabilities_with_pdf())
    settings = pdf_chat_settings()
    certificate_text = (
        "This certificate is for Junior Software Engineer AI-Native "
        "Development Program."
    )
    document_id = upload_process_index_pdf(
        client,
        auth_headers,
        "conversation-a",
        "Certificates.pdf",
        pdf_bytes(certificate_text),
        settings,
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What program is mentioned?",
                "history": [
                    {
                        "role": "user",
                        "content": "What is in this document?",
                    },
                    {
                        "role": "assistant",
                        "content": "It is a certificate.",
                    },
                ],
                "conversationSettings": settings,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ragUsed"] is True
    assert payload["sources"][0]["documentId"] == document_id
    assert "Junior Software Engineer AI-Native Development Program" in payload["answer"]
    assert "attach" not in payload["answer"].lower()
    assert "Retrieval mode: semantic_rag" in fake_ollama.calls[0][1]


def test_broad_attached_short_pdf_includes_all_chunks(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(
        app,
        tmp_path,
        capabilities=chat_capabilities_with_pdf(),
    )
    app.state.document_service.chunk_size = 120
    settings = pdf_chat_settings()
    first_page = (
        "Page one says Certificate A covers Claude 101 fundamentals and "
        "practical prompting."
    )
    second_page = (
        "Page two says Certificate B covers AI Fluency Framework and "
        "Foundations."
    )
    document_id = upload_process_index_pdf(
        client,
        auth_headers,
        "conversation-a",
        "certificates.pdf",
        pdf_bytes([first_page, second_page]),
        settings,
    )
    embed_calls_after_indexing = list(fake_embedder.calls)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What does this document contain?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": settings,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["sources"]) >= 2
    prompt = fake_ollama.calls[0][1]
    assert first_page in prompt
    assert second_page in prompt
    assert fake_embedder.calls == embed_calls_after_indexing


def test_document_context_does_not_show_truncated_marker_to_model(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    document_id = "9" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        document_id,
        filename="large-certificate.txt",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=document_id,
        chunk_texts=[
            "certificate details " + ("clean excerpt text " * 600),
        ],
        chunk_metadata=[{"documentName": "large-certificate.txt"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What certificate details are in this document?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    prompt = fake_ollama.calls[0][1]
    document_context = prompt.split("<document_context>", 1)[1].split(
        "</document_context>",
        1,
    )[0]
    assert "truncated" not in document_context.lower()


def test_document_context_refusal_about_full_text_is_repaired(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService(
        chat_response="I would need access to the full text to answer."
    )
    configure_chat_rag_tests(app, tmp_path)
    document_id = "c" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        document_id,
        filename="certificate.txt",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=document_id,
        chunk_texts=["certificate says Claude 101 completion"],
        chunk_metadata=[{"documentName": "certificate.txt"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What certificate is mentioned?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    answer = response.json()["answer"]
    assert "Claude 101 completion" in answer
    assert "full text" not in answer.lower()


def test_image_based_pdf_without_ocr_reports_limited_embedded_text(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService(chat_response="The PDF includes the name Jesus.")
    configure_chat_rag_tests(app, tmp_path, capabilities=chat_capabilities_with_pdf())
    settings = pdf_chat_settings()
    document_id = upload_process_index_pdf(
        client,
        auth_headers,
        "conversation-a",
        "certificates.pdf",
        image_like_pdf_bytes("Jesus"),
        settings,
    )
    metadata = app.state.document_service.get_document("conversation-a", document_id)
    diagnostics = metadata["extractionDiagnostics"]
    assert diagnostics["ocrNeeded"] is True
    assert diagnostics["likelyImageBased"] is True
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is in this document?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": settings,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert response.json()["answer"].startswith(
        "I found the uploaded PDF, but most of its content appears to be "
        "image-based and OCR is not available"
    )


def test_ocr_text_from_low_text_pdf_is_indexed_and_answerable(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService(
        chat_response="I would need access to the full text to answer."
    )
    fake_ocr = FakePDFOCREngine(
        "Claude 101\nAI Fluency: Framework & Foundations"
    )
    configure_chat_rag_tests(app, tmp_path, capabilities=chat_capabilities_with_pdf())
    app.state.document_service = DocumentService(
        upload_directory=tmp_path / "uploads",
        max_upload_bytes=1024 * 1024,
        chunk_size=2000,
        ocr_engines={"ocrmypdf": fake_ocr},
    )
    settings = {
        **pdf_chat_settings(),
        "ocrEngine": "ocrmypdf",
    }
    document_id = upload_process_index_pdf(
        client,
        auth_headers,
        "conversation-a",
        "certificates.pdf",
        image_like_pdf_bytes("Jesus"),
        settings,
    )
    assert fake_ocr.calls
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What certificates are in this file?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": settings,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "Claude 101" in payload["answer"]
    assert "AI Fluency: Framework & Foundations" in payload["answer"]
    assert "Claude 101" in payload["sources"][0]["textPreview"]


def test_empty_pdf_without_ocr_reports_clear_processing_failure(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path, capabilities=chat_capabilities_with_pdf())
    settings = pdf_chat_settings()
    document_id = upload_process_index_pdf(
        client,
        auth_headers,
        "conversation-a",
        "scan.pdf",
        pdf_bytes(""),
        settings,
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is in this document?",
                "attachmentDocumentIds": [document_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": settings,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "scan.pdf" in detail
    assert "No text could be extracted" in detail
    assert fake_ollama.calls == []


def test_document_question_without_uploaded_document_asks_for_attachment(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService(
        chat_response="Please upload or attach the document so I can read it."
    )
    configure_chat_rag_tests(app, tmp_path)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is in this document?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"] == []
    assert payload["answer"] == "Please upload or attach the document so I can read it."
    assert "<document_context>" not in fake_ollama.calls[0][1]


def test_second_attachment_in_same_conversation_excludes_first_document_context(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    resume_id = "e" * 32
    certificate_id = "f" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        resume_id,
        filename="resume.pdf",
    )
    seed_processed_document_metadata(
        app,
        "conversation-a",
        certificate_id,
        filename="certificate.pdf",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=resume_id,
        chunk_texts=["resume says Senior Python Engineer"],
        chunk_metadata=[{"documentName": "resume.pdf"}],
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=certificate_id,
        chunk_texts=["certificate says Cloud Security Completion"],
        chunk_metadata=[{"documentName": "certificate.pdf"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is this?",
                "attachmentDocumentIds": [certificate_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert [source["documentId"] for source in payload["sources"]] == [
        certificate_id
    ]
    prompt = fake_ollama.calls[0][1]
    assert "certificate.pdf" in prompt
    assert "Cloud Security Completion" in prompt
    assert "resume.pdf" not in prompt
    assert "Senior Python Engineer" not in prompt


def test_compare_attachment_to_previous_document_includes_current_then_historical(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    resume_id = "1" * 32
    certificate_id = "2" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        resume_id,
        filename="resume.pdf",
    )
    seed_processed_document_metadata(
        app,
        "conversation-a",
        certificate_id,
        filename="certificate.pdf",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=resume_id,
        chunk_texts=["resume says Senior Python Engineer"],
        chunk_metadata=[{"documentName": "resume.pdf"}],
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=certificate_id,
        chunk_texts=["certificate says Cloud Security Completion"],
        chunk_metadata=[{"documentName": "certificate.pdf"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "Compare this PDF to the previous one.",
                "attachmentDocumentIds": [certificate_id],
                "ragOptions": {"enabled": True, "includeSources": True},
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][0]["documentId"] == certificate_id
    assert any(source["documentId"] == resume_id for source in payload["sources"])
    prompt = fake_ollama.calls[0][1]
    assert prompt.index("certificate.pdf") < prompt.index("resume.pdf")
    assert "Scope: current message attachment" in prompt
    assert "Scope: historical conversation document" in prompt


def test_conversation_reference_retrieves_previous_resume_without_attachment(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    resume_id = "3" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        resume_id,
        filename="resume.pdf",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=resume_id,
        chunk_texts=["resume says React and TypeScript frontend experience"],
        chunk_metadata=[{"documentName": "resume.pdf"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What did my resume say about React?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][0]["documentId"] == resume_id
    assert payload["sources"][0]["documentName"] == "resume.pdf"
    prompt = fake_ollama.calls[0][1]
    assert "Retrieval mode: conversation_reference" in prompt
    assert "resume says React and TypeScript frontend experience" in prompt


def test_conversation_reference_retrieves_previous_certificate_without_attachment(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    certificate_id = "4" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        certificate_id,
        filename="certificate.pdf",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=certificate_id,
        chunk_texts=["certificate expiration date is July 2028"],
        chunk_metadata=[{"documentName": "certificate.pdf"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "When does the certificate expire?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][0]["documentId"] == certificate_id
    assert "certificate expiration date" in payload["sources"][0]["textPreview"]
    assert "Retrieval mode: conversation_reference" in fake_ollama.calls[0][1]


def test_ambiguous_previous_pdf_reference_asks_for_clarification(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    seed_processed_document_metadata(
        app,
        "conversation-a",
        "5" * 32,
        filename="resume.pdf",
    )
    seed_processed_document_metadata(
        app,
        "conversation-a",
        "6" * 32,
        filename="certificate.pdf",
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What did the PDF say?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "Which PDF" in detail
    assert "resume.pdf" in detail
    assert "certificate.pdf" in detail
    assert fake_ollama.calls == []


def test_semantic_rag_retrieves_relevant_document_without_attachment(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(app, tmp_path)
    document_id = "7" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        document_id,
        filename="profile-notes.txt",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=document_id,
        chunk_texts=["React frontend experience from uploaded profile notes"],
        chunk_metadata=[{"documentName": "profile-notes.txt"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What did my experience mention about React?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"][0]["documentId"] == document_id
    assert "React frontend experience" in payload["sources"][0]["textPreview"]
    assert "Retrieval mode: semantic_rag" in fake_ollama.calls[0][1]
    assert fake_embedder.calls == [
        (["What did my experience mention about React?"], "embed-a")
    ]


def test_unrelated_message_does_not_inject_document_context(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(app, tmp_path)
    document_id = "8" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        document_id,
        filename="resume.pdf",
    )
    seed_vector_index(
        app,
        "conversation-a",
        document_id=document_id,
        chunk_texts=["React frontend experience from resume"],
        chunk_metadata=[{"documentName": "resume.pdf"}],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "Write me a poem.",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "<document_context>" not in fake_ollama.calls[0][1]
    assert fake_embedder.calls == []


def test_attached_missing_document_is_rejected_before_generation(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is this document?",
                "ragOptions": {
                    "enabled": True,
                    "documentIds": ["b" * 32],
                },
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "Attached document was not found" in response.json()["detail"]
    assert fake_ollama.calls == []


def test_attached_processed_document_without_index_is_rejected_before_generation(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    document_id = "c" * 32
    seed_processed_document_metadata(app, "conversation-a", document_id)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is this document?",
                "ragOptions": {
                    "enabled": True,
                    "documentIds": [document_id],
                },
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "Attached document content could not be retrieved" in response.json()["detail"]
    assert fake_ollama.calls == []


def test_attached_failed_document_is_rejected_before_generation(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    document_id = "d" * 32
    seed_processed_document_metadata(
        app,
        "conversation-a",
        document_id,
        filename="scan.pdf",
        status="failed",
        chunk_count=0,
        error="No text could be extracted from the PDF.",
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What is this document?",
                "ragOptions": {
                    "enabled": True,
                    "documentIds": [document_id],
                },
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "basic",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "scan.pdf" in detail
    assert "No text could be extracted" in detail
    assert fake_ollama.calls == []


def test_hybrid_rag_retrieves_chunks_and_inserts_them_into_prompt(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(app, tmp_path)
    seed_vector_index(app, "conversation-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "hybrid",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ragUsed"] is True
    assert payload["rerankingUsed"] is False
    assert payload["ragWarnings"] == []
    assert payload["sources"][0]["sourceNumber"] == 1
    assert payload["sources"][0]["finalRank"] == 1
    assert payload["sources"][0]["documentId"] == "doc-1"
    assert payload["sources"][0]["documentName"] == "notes.txt"
    assert payload["sources"][0]["chunkId"] == "chunk-banana"
    assert payload["sources"][0]["chunkIndex"] == 1
    assert payload["sources"][0]["collectionId"]
    assert payload["sources"][0]["vectorScore"] == payload["sources"][0]["score"]
    assert payload["sources"][0]["rerankScore"] is None
    assert "banana bread" in payload["sources"][0]["textPreview"]

    prompt = fake_ollama.calls[0][1]
    assert "<document_context>" in prompt
    assert "Source 1" in prompt
    assert "Source 1: notes.txt" in prompt
    assert "banana bread" in prompt
    assert "Do not claim you cannot access the file" in prompt
    assert fake_embedder.calls == [
        (["What document talks about banana?"], "embed-a")
    ]


def test_rag_source_metadata_is_normalized_for_sparse_vector_records(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    seed_vector_index(
        app,
        "conversation-a",
        chunk_texts=["banana bread"],
    )
    index_path = vector_index_path(app, "conversation-a")
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    index_data["vectors"][0]["documentId"] = ""
    index_data["vectors"][0]["chunkId"] = ""
    index_data["vectors"][0]["chunkIndex"] = "bad"
    index_data["vectors"][0]["metadata"] = {
        "documentId": "",
        "documentName": "Very long document name " + ("with extra detail " * 20),
        "chunkId": "",
    }
    index_path.write_text(json.dumps(index_data), encoding="utf-8")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "hybrid",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    source = response.json()["sources"][0]
    assert source["sourceNumber"] == 1
    assert source["finalRank"] == 1
    assert source["documentId"] == "unknown-document"
    assert source["chunkId"] == "unknown-document:0"
    assert source["chunkIndex"] == 0
    assert len(source["documentName"]) <= 160
    assert source["documentName"].endswith("[truncated]")
    assert source["collectionId"]


def test_rag_skips_empty_retrieved_chunks_and_keeps_source_numbers_stable(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    seed_vector_index(app, "conversation-a", chunk_texts=["", "banana bread"])
    index_path = vector_index_path(app, "conversation-a")
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    index_data["vectors"][0]["embedding"] = [0.0, 2.0, 0.0]
    index_path.write_text(json.dumps(index_data), encoding="utf-8")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "hybrid",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["sourceNumber"] == 1
    assert payload["sources"][0]["finalRank"] == 1
    assert payload["sources"][0]["chunkId"] == "chunk-banana"
    assert "Skipped retrieved chunk" in payload["ragWarnings"][0]
    prompt = fake_ollama.calls[0][1]
    assert "<document_context>" in prompt
    assert "Source 1" in prompt
    assert "banana bread" in prompt
    assert "Source 2" not in prompt


def test_reranked_pipeline_attempts_reranking_and_uses_reranked_order(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_reranker = FakeRerankerProvider(
        {"chunk-apple": 0.95, "chunk-banana": 0.10}
    )
    configure_chat_rag_tests(app, tmp_path, reranker=fake_reranker)
    seed_vector_index(app, "conversation-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "reranked",
                    "reranker": "rerank-a",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ragUsed"] is True
    assert payload["rerankingUsed"] is True
    assert payload["rerankerModel"] == "rerank-a"
    assert payload["rerankWarnings"] == []
    assert fake_reranker.calls[0]["model"] == "rerank-a"
    assert fake_reranker.calls[0]["settings"]["candidateK"] == 20
    assert fake_reranker.calls[0]["settings"]["topK"] == 5

    first_source = payload["sources"][0]
    assert first_source["chunkId"] == "chunk-apple"
    assert first_source["finalRank"] == 1
    assert first_source["rerankScore"] == 0.95
    assert first_source["vectorScore"] == 0.0
    assert first_source["score"] == 0.95

    prompt = fake_ollama.calls[0][1]
    assert prompt.index("apple pie") < prompt.index("banana bread")
    assert "Source 1" in prompt


def test_valid_reranker_with_hybrid_pipeline_attempts_reranking(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_reranker = FakeRerankerProvider(
        {"chunk-apple": 0.95, "chunk-banana": 0.10}
    )
    configure_chat_rag_tests(app, tmp_path, reranker=fake_reranker)
    seed_vector_index(app, "conversation-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "hybrid",
                    "reranker": "rerank-a",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["rerankingUsed"] is True
    assert response.json()["sources"][0]["chunkId"] == "chunk-apple"
    assert fake_reranker.calls[0]["model"] == "rerank-a"


def test_invalid_reranker_falls_back_with_warning(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_reranker = FakeRerankerProvider({"chunk-apple": 0.95})
    configure_chat_rag_tests(
        app,
        tmp_path,
        capabilities=chat_capabilities(reranker_models=[]),
        reranker=fake_reranker,
    )
    seed_vector_index(app, "conversation-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "reranked",
                    "reranker": "missing-reranker",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["rerankingUsed"] is False
    assert payload["sources"][0]["chunkId"] == "chunk-banana"
    assert "selected reranker 'missing-reranker'" in payload["ragWarnings"][0]
    assert payload["ragWarnings"] == payload["rerankWarnings"]
    assert fake_reranker.calls == []


def test_reranker_failure_falls_back_with_warning(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_reranker = FakeRerankerProvider(fail=True)
    configure_chat_rag_tests(app, tmp_path, reranker=fake_reranker)
    seed_vector_index(app, "conversation-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "reranked",
                    "reranker": "rerank-a",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["rerankingUsed"] is False
    assert payload["rerankerModel"] is None
    assert payload["sources"][0]["chunkId"] == "chunk-banana"
    assert payload["sources"][0]["rerankScore"] is None
    assert "selected reranker failed" in payload["ragWarnings"][0]
    assert payload["ragWarnings"] == payload["rerankWarnings"]
    assert fake_reranker.calls[0]["model"] == "rerank-a"


def test_rerank_candidate_k_is_never_less_than_top_k(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_reranker = FakeRerankerProvider(
        {
            "chunk-apple": 0.10,
            "chunk-banana": 0.90,
            "chunk-carrot": 0.20,
        }
    )
    configure_chat_rag_tests(app, tmp_path, reranker=fake_reranker)
    seed_vector_index(
        app,
        "conversation-a",
        chunk_texts=["apple pie", "banana bread", "carrot cake"],
    )
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "What document talks about banana?",
                "ragOptions": {"topK": 2, "candidateK": 1},
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "reranked",
                    "reranker": "rerank-a",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert fake_reranker.calls[0]["settings"]["topK"] == 2
    assert fake_reranker.calls[0]["settings"]["candidateK"] == 2
    assert fake_reranker.calls[0]["candidateCount"] == 2
    assert len(response.json()["sources"]) == 2


def test_hybrid_rag_without_index_falls_back_to_normal_chat(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    configure_chat_rag_tests(app, tmp_path)
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "No indexed documents yet.",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "hybrid",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ragUsed"] is False
    assert response.json()["sources"] == []
    assert "<document_context>" not in fake_ollama.calls[0][1]
    assert fake_ollama.calls[0][1] == "No indexed documents yet."


def test_hybrid_rag_without_valid_embedder_warns_and_falls_back(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(
        app,
        tmp_path,
        capabilities=chat_capabilities(embedder_models=[]),
    )
    seed_vector_index(app, "conversation-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "Use docs if possible.",
                "conversationSettings": {
                    "embedderModel": "missing-embedder",
                    "ragPipeline": "hybrid",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ragUsed"] is False
    assert "valid embedderModel" in response.json()["ragWarnings"][0]
    assert response.json()["sources"] == []
    assert fake_embedder.calls == []
    assert "<document_context>" not in fake_ollama.calls[0][1]


def test_hybrid_rag_embedder_mismatch_warns_and_falls_back(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(
        app,
        tmp_path,
        capabilities=chat_capabilities(embedder_models=["embed-a", "embed-b"]),
    )
    seed_vector_index(app, "conversation-a", embedder_model="embed-a")
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "Use docs if possible.",
                "conversationSettings": {
                    "embedderModel": "embed-b",
                    "ragPipeline": "hybrid",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ragUsed"] is False
    assert "does not match indexed embedder" in response.json()["ragWarnings"][0]
    assert response.json()["sources"] == []
    assert fake_embedder.calls == []
    assert "<document_context>" not in fake_ollama.calls[0][1]


def test_hybrid_rag_vector_failure_warns_and_falls_back(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    fake_ollama = FakeOllamaService()
    fake_embedder = configure_chat_rag_tests(app, tmp_path)
    app.state.vector_store = FailingVectorStore()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "conversationId": "conversation-a",
                "message": "Use docs if possible.",
                "conversationSettings": {
                    "embedderModel": "embed-a",
                    "ragPipeline": "hybrid",
                    "vectorDatabase": "qdrant",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ragUsed"] is False
    assert "vector indexes could not be read" in response.json()["ragWarnings"][0]
    assert response.json()["sources"] == []
    assert fake_embedder.calls == []
    assert "<document_context>" not in fake_ollama.calls[0][1]
