import asyncio
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.components import Chunk, ComponentUnavailableError
from app.ai.execution_context import AISettingsResolver
from app.ai.rerankers import RerankResult
from app.ai.vectorstores import JsonVectorStore, VectorStoreError
from app.routers.chat import get_ollama_service
from app.services.component_registry import CAPABILITY_KEYS
from app.services.ollama_service import InstalledOllamaModel


class FakeOllamaService:
    """Small in-memory replacement for the real Ollama HTTP client."""

    def __init__(
        self,
        installed_models: list[InstalledOllamaModel] | None = None,
        summary_response: str = "Condensed memory summary.",
        fail_summary: bool = False,
    ) -> None:
        self.calls: list[tuple[str, str]] = []
        self.installed_models = installed_models or []
        self.summary_response = summary_response
        self.fail_summary = fail_summary

    async def generate(self, model: str, prompt: str) -> str:
        self.calls.append((model, prompt))
        if "Memory summary:" in prompt:
            if self.fail_summary:
                raise ComponentUnavailableError("summary failed")
            return self.summary_response
        return "Mocked local model response"

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
    capabilities["ocrEngines"] = [capability("none", "ocrEngine")]
    capabilities["chunkers"] = [
        capability("fixed", "chunker"),
        capability("recursive", "chunker"),
    ]
    capabilities["vectorDatabases"] = [
        capability("chroma", "vectorDatabase"),
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
    vector_database: str = "chroma",
    document_id: str = "doc-1",
    chunk_texts: list[str] | None = None,
) -> None:
    texts = chunk_texts or ["apple pie", "banana bread"]
    chunks = []
    for index, text in enumerate(texts):
        keyword = text.split(maxsplit=1)[0].lower()
        chunk_id = f"chunk-{keyword}"
        chunks.append(
            Chunk(
                id=chunk_id,
                text=text,
                metadata={
                    "documentId": document_id,
                    "documentName": "notes.txt",
                    "chunkId": chunk_id,
                    "chunkIndex": index,
                },
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
        ("qwen3:4b", "Explain dependency injection briefly.")
    ]


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
    assert response.json()["compressorMode"] == "none"


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
    assert payload["compressorMode"] == "token"
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
                    "vectorDatabase": "chroma",
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
    assert payload["compressionUsed"] is True
    assert payload["compressorMode"] == "summarizer"
    assert payload["compressionStats"]["summaryGenerated"] is True
    assert "Older conversation:" in fake_ollama.calls[0][1]
    assert "message-0" in fake_ollama.calls[0][1]

    final_prompt = fake_ollama.calls[-1][1]
    assert "[Conversation Memory]" in final_prompt
    assert "Remember the API design." in final_prompt
    assert "message-11" in final_prompt
    assert "message-0" not in final_prompt
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
    assert payload["compressorMode"] == "summarizer"
    assert "Summarizer context compression failed" in payload["compressionWarnings"][0]
    assert "[Conversation Memory]" not in fake_ollama.calls[-1][1]


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
    assert payload["compressorMode"] == "semantic"
    assert "Semantic context compression is not implemented yet" in payload[
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
    assert payload["compressionUsed"] is True
    assert payload["compressorMode"] == "memory"
    assert payload["compressionStats"]["summaryGenerated"] is True
    assert "Memory context compression is not implemented yet" in payload[
        "compressionWarnings"
    ][0]
    assert "Persistent memory summary." in fake_ollama.calls[-1][1]


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
                    "vectorDatabase": "chroma",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ragUsed"] is False
    assert response.json()["sources"] == []
    assert fake_embedder.calls == []
    assert "[Retrieved Context]" not in fake_ollama.calls[0][1]


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
                    "vectorDatabase": "chroma",
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
    assert payload["sources"][0]["vectorScore"] == payload["sources"][0]["score"]
    assert payload["sources"][0]["rerankScore"] is None
    assert "banana bread" in payload["sources"][0]["textPreview"]

    prompt = fake_ollama.calls[0][1]
    assert "[Retrieved Context]" in prompt
    assert "Source 1" in prompt
    assert "Document: notes.txt" in prompt
    assert "banana bread" in prompt
    assert "[Source N]" in prompt
    assert fake_embedder.calls == [
        (["What document talks about banana?"], "embed-a")
    ]


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
                    "vectorDatabase": "chroma",
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
                    "vectorDatabase": "chroma",
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
                    "vectorDatabase": "chroma",
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
                    "vectorDatabase": "chroma",
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
                    "vectorDatabase": "chroma",
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
                    "vectorDatabase": "chroma",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ragUsed"] is False
    assert response.json()["sources"] == []
    assert "[Retrieved Context]" not in fake_ollama.calls[0][1]
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
                    "vectorDatabase": "chroma",
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
    assert "[Retrieved Context]" not in fake_ollama.calls[0][1]


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
                    "vectorDatabase": "chroma",
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
    assert "[Retrieved Context]" not in fake_ollama.calls[0][1]


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
                    "vectorDatabase": "chroma",
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
    assert "[Retrieved Context]" not in fake_ollama.calls[0][1]
