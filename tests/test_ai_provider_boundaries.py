from pathlib import Path

import pytest

from app.ai.chunkers import UnavailableChunker
from app.ai.components import (
    Chunker,
    ComponentNotImplementedError,
    ContextCompressor,
    EmbedderProvider,
    OCREngine,
    PDFParser,
    RAGPipeline,
    Reranker,
    Retriever,
    VectorStore,
)
from app.ai.embedders import OllamaEmbedderProvider
from app.ai.ocr import UnavailableOCREngine
from app.ai.parsers import UnavailablePDFParser
from app.ai.pipelines import (
    UnavailableContextCompressor,
    UnavailableRAGPipeline,
    UnavailableRetriever,
)
from app.ai.rerankers import OllamaRerankerProvider, UnavailableReranker
from app.ai.vectorstores import JsonVectorStore, UnavailableVectorStore


def test_real_adapters_match_runtime_protocols(tmp_path: Path) -> None:
    """Provider boundaries remain explicit and testable at runtime."""

    class OllamaService:
        pass

    assert isinstance(OllamaEmbedderProvider(OllamaService()), EmbedderProvider)
    assert isinstance(OllamaRerankerProvider(OllamaService()), Reranker)
    assert isinstance(JsonVectorStore(tmp_path), VectorStore)


def test_unavailable_adapters_match_runtime_protocols() -> None:
    assert isinstance(UnavailableChunker(), Chunker)
    assert isinstance(UnavailableOCREngine(), OCREngine)
    assert isinstance(UnavailablePDFParser(), PDFParser)
    assert isinstance(UnavailableRetriever(), Retriever)
    assert isinstance(UnavailableContextCompressor(), ContextCompressor)
    assert isinstance(UnavailableRAGPipeline(), RAGPipeline)
    assert isinstance(UnavailableReranker(), Reranker)
    assert isinstance(UnavailableVectorStore(), VectorStore)


@pytest.mark.asyncio
async def test_unavailable_document_adapters_fail_with_clear_boundary_errors() -> None:
    with pytest.raises(ComponentNotImplementedError, match="PDF parser"):
        await UnavailablePDFParser().extract_text(Path("document.pdf"), {})

    with pytest.raises(ComponentNotImplementedError, match="OCR engine"):
        await UnavailableOCREngine().extract_text(Path("scan.pdf"), {})

    with pytest.raises(ComponentNotImplementedError, match="chunker"):
        await UnavailableChunker().chunk_text("hello", {})


@pytest.mark.asyncio
async def test_unavailable_retrieval_adapters_fail_with_clear_boundary_errors() -> None:
    with pytest.raises(ComponentNotImplementedError, match="retriever"):
        await UnavailableRetriever().retrieve("query", {})

    with pytest.raises(ComponentNotImplementedError, match="context compressor"):
        await UnavailableContextCompressor().compress([], [], {})

    with pytest.raises(ComponentNotImplementedError, match="RAG pipeline"):
        await UnavailableRAGPipeline().answer("query", {}, [])

    with pytest.raises(ComponentNotImplementedError, match="reranker"):
        await UnavailableReranker().rerank("query", [], "model", {})


@pytest.mark.asyncio
async def test_unavailable_vector_store_fails_with_clear_boundary_errors() -> None:
    vector_store = UnavailableVectorStore()

    with pytest.raises(ComponentNotImplementedError, match="persistence"):
        await vector_store.upsert("collection", [], [], {})

    with pytest.raises(ComponentNotImplementedError, match="queries"):
        await vector_store.query("collection", [], 5)

    with pytest.raises(ComponentNotImplementedError, match="metadata"):
        await vector_store.get_collection_metadata("collection")
