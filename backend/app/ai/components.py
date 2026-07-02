from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class AIComponentError(RuntimeError):
    """Base error for modular AI component execution."""


class ComponentUnavailableError(AIComponentError):
    """Raised when a selected component cannot be used locally."""


class ComponentNotImplementedError(AIComponentError):
    """Raised when a component interface exists but has no execution adapter."""


@dataclass(frozen=True)
class DocumentText:
    """Text extracted from a local document-like file."""

    file_path: Path
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """A text chunk prepared for retrieval or indexing."""

    id: str
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned from a retriever or vector store query."""

    chunk: Chunk
    score: float
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """Boundary for local text-generation adapters."""

    async def generate(
        self,
        prompt: str,
        history: Sequence[Mapping[str, str]],
        settings: Mapping[str, Any],
    ) -> str:
        """Generate a text answer for a prompt and recent history."""


@runtime_checkable
class EmbedderProvider(Protocol):
    """Boundary for local embedding adapters."""

    async def embed_texts(
        self,
        texts: Sequence[str],
        model: str,
    ) -> list[list[float]]:
        """Return one embedding vector for each input text."""


@runtime_checkable
class OCREngine(Protocol):
    """Boundary for OCR adapters that extract text from visual documents."""

    async def extract_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> DocumentText:
        """Extract text from an image or scanned document."""


@runtime_checkable
class PDFParser(Protocol):
    """Boundary for PDF text extraction adapters."""

    async def extract_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> DocumentText:
        """Extract text from a PDF file."""


@runtime_checkable
class Chunker(Protocol):
    """Boundary for document chunking adapters."""

    async def chunk_text(
        self,
        text: str,
        settings: Mapping[str, Any],
    ) -> list[Chunk]:
        """Split text into chunks suitable for retrieval."""


@runtime_checkable
class VectorStore(Protocol):
    """Boundary for vector persistence and similarity search adapters."""

    async def upsert(
        self,
        collection: str,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
        metadata: Mapping[str, Any],
    ) -> None:
        """Insert or replace chunk embeddings in a collection."""

    async def query(
        self,
        collection: str,
        query_embedding: Sequence[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Return the most relevant chunks for an embedding query."""

    async def get_collection_metadata(
        self,
        collection: str,
    ) -> Mapping[str, Any]:
        """Return metadata for a stored collection."""


@runtime_checkable
class Retriever(Protocol):
    """Boundary for retrieval pipelines that return candidate context."""

    async def retrieve(
        self,
        query: str,
        settings: Mapping[str, Any],
    ) -> list[RetrievedChunk]:
        """Retrieve candidate context for a query."""


@runtime_checkable
class Reranker(Protocol):
    """Boundary for reranking retrieved context before prompt injection."""

    async def rerank(
        self,
        query: str,
        candidate_chunks: Sequence[Any],
        model: str,
        settings: Mapping[str, Any],
    ) -> Any:
        """Reorder retrieved chunks by query relevance."""


@runtime_checkable
class ContextCompressor(Protocol):
    """Boundary for prompt context compression adapters."""

    async def compress(
        self,
        compression_input: Any,
        settings: Mapping[str, Any] | None = None,
    ) -> Any:
        """Compress prompt inputs before generation."""


@runtime_checkable
class RAGPipeline(Protocol):
    """Boundary for complete retrieval-augmented generation pipelines."""

    async def answer(
        self,
        query: str,
        conversation_settings: Mapping[str, Any],
        history: Sequence[Mapping[str, str]],
    ) -> str:
        """Answer a query using retrieval-augmented generation."""
