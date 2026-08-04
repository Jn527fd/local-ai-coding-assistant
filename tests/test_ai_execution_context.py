import pytest

from app.ai.embedders import OllamaEmbedderProvider
from app.ai.execution_context import AISettingsResolver
from app.schemas.chat import ConversationSettings
from app.services.component_registry import CAPABILITY_KEYS


def capability(
    capability_id: str,
    capability_type: str,
    available: bool = True,
    source: str = "test",
) -> dict[str, object]:
    return {
        "id": capability_id,
        "label": capability_id,
        "type": capability_type,
        "available": available,
        "source": source,
        "name": capability_id,
    }


def capabilities_snapshot() -> dict[str, list[dict[str, object]]]:
    capabilities: dict[str, list[dict[str, object]]] = {
        key: [] for key in CAPABILITY_KEYS
    }
    capabilities["llmModels"] = [
        capability("qwen3:4b", "llmModel", source="ollama"),
        capability("llama3.2:3b", "llmModel", source="ollama"),
    ]
    capabilities["embedderModels"] = [
        capability("nomic-embed-text:latest", "embedderModel"),
        capability("mxbai-embed-large:latest", "embedderModel", False),
    ]
    capabilities["rerankerModels"] = [
        capability("bge-reranker-v2:m3", "rerankerModel", False),
    ]
    capabilities["ocrEngines"] = [
        capability("none", "ocrEngine", source="builtin"),
        capability("tesseract", "ocrEngine", False),
        capability("paddleocr", "ocrEngine"),
    ]
    capabilities["pdfParsers"] = [
        capability("docling", "pdfParser"),
        capability("pymupdf", "pdfParser", False),
        capability("pdfplumber", "pdfParser"),
    ]
    capabilities["chunkers"] = [
        capability("fixed", "chunker", source="static"),
        capability("recursive", "chunker", source="static"),
    ]
    capabilities["vectorDatabases"] = [
        capability("qdrant", "vectorDatabase", source="qdrant"),
    ]
    capabilities["ragPipelines"] = [
        capability("basic", "ragPipeline", source="static"),
    ]
    capabilities["contextCompressors"] = [
        capability("none", "contextCompressor", source="static"),
    ]
    return capabilities


class FakeComponentRegistry:
    def __init__(
        self,
        capabilities: dict[str, list[dict[str, object]]] | None = None,
    ) -> None:
        self._capabilities = capabilities or capabilities_snapshot()

    async def capabilities(self) -> dict[str, list[dict[str, object]]]:
        return self._capabilities


class FakeEmbeddingOllamaService:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    async def embed_texts(
        self,
        texts: list[str],
        model: str,
    ) -> list[list[float]]:
        self.calls.append((texts, model))
        return [[1.0, 2.0], [3.0, 4.0]]


@pytest.mark.anyio
async def test_execution_context_resolves_valid_per_chat_llm() -> None:
    resolver = AISettingsResolver(FakeComponentRegistry())

    context = await resolver.resolve(
        conversation_settings=ConversationSettings(
            llmModel="llama3.2:3b",
        ),
        active_model="qwen3:4b",
        conversation_id="chat-1",
    )

    assert context.conversation_id == "chat-1"
    assert context.resolved_llm_model == "llama3.2:3b"
    assert context.components["llmModel"].valid is True
    assert context.components["llmModel"].source == "ollama"


@pytest.mark.anyio
async def test_execution_context_falls_back_when_llm_is_missing() -> None:
    resolver = AISettingsResolver(FakeComponentRegistry())

    context = await resolver.resolve(
        conversation_settings=ConversationSettings(),
        active_model="qwen3:4b",
    )

    assert context.conversation_settings.llmModel == "qwen3:4b"
    assert context.conversation_settings.ocrEngine == "paddleocr"
    assert context.resolved_llm_model == "qwen3:4b"
    assert context.components["llmModel"].valid is True


@pytest.mark.anyio
async def test_execution_context_falls_back_when_llm_is_invalid() -> None:
    resolver = AISettingsResolver(FakeComponentRegistry())

    context = await resolver.resolve(
        conversation_settings=ConversationSettings(
            llmModel="missing-model:latest",
        ),
        active_model="qwen3:4b",
    )

    assert context.conversation_settings.llmModel == "missing-model:latest"
    assert context.resolved_llm_model == "qwen3:4b"
    assert context.components["llmModel"].valid is False
    assert "not an available LLM" in str(context.components["llmModel"].reason)


@pytest.mark.anyio
async def test_execution_context_normalizes_missing_optional_settings() -> None:
    resolver = AISettingsResolver(FakeComponentRegistry())

    context = await resolver.resolve(
        conversation_settings=ConversationSettings(llmModel="qwen3:4b"),
        active_model="qwen3:4b",
    )

    assert context.resolved_embedder_model == "nomic-embed-text:latest"
    assert context.resolved_ocr_engine == "paddleocr"
    assert context.resolved_pdf_parser == "docling"
    assert context.resolved_chunker == "recursive"
    assert context.resolved_vector_database == "qdrant"
    assert context.resolved_rag_pipeline == "basic"
    assert context.resolved_reranker == "none"
    assert context.resolved_context_compressor == "auto"
    assert context.resolved_vision_model == "none"


@pytest.mark.anyio
async def test_execution_context_preserves_unavailable_optional_selections() -> None:
    resolver = AISettingsResolver(FakeComponentRegistry())

    context = await resolver.resolve(
        conversation_settings=ConversationSettings(
            llmModel="qwen3:4b",
            embedderModel="mxbai-embed-large:latest",
            reranker="bge-reranker-v2:m3",
            ocrEngine="tesseract",
        ),
        active_model="qwen3:4b",
    )

    assert context.conversation_settings.embedderModel == (
        "mxbai-embed-large:latest"
    )
    assert context.conversation_settings.reranker == "bge-reranker-v2:m3"
    assert context.conversation_settings.ocrEngine == "tesseract"
    assert context.components["embedderModel"].valid is False
    assert context.components["reranker"].valid is False
    assert context.components["ocrEngine"].valid is False
    assert context.resolved_embedder_model is None
    assert context.resolved_reranker == "none"
    assert context.resolved_ocr_engine == "none"


@pytest.mark.anyio
async def test_ollama_embedder_provider_delegates_to_ollama_service() -> None:
    ollama_service = FakeEmbeddingOllamaService()
    provider = OllamaEmbedderProvider(ollama_service)

    embeddings = await provider.embed_texts(
        ["alpha", "beta"],
        model="nomic-embed-text:latest",
    )

    assert embeddings == [[1.0, 2.0], [3.0, 4.0]]
    assert ollama_service.calls == [
        (["alpha", "beta"], "nomic-embed-text:latest")
    ]
