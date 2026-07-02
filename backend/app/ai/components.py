from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class AIComponentError(RuntimeError):
    """Base error for modular AI component execution."""


class ComponentUnavailableError(AIComponentError):
    """Raised when a selected component cannot be used locally."""


class ComponentNotImplementedError(AIComponentError):
    """Raised by scaffolding components that do not execute real work yet."""


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


class LLMProvider(Protocol):
    async def generate(
        self,
        prompt: str,
        history: Sequence[Mapping[str, str]],
        settings: Mapping[str, Any],
    ) -> str:
        """Generate a text answer for a prompt and recent history."""


class EmbedderProvider(Protocol):
    async def embed_texts(
        self,
        texts: Sequence[str],
        model: str,
    ) -> list[list[float]]:
        """Return one embedding vector for each input text."""


class OCREngine(Protocol):
    async def extract_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> DocumentText:
        """Extract text from an image or scanned document."""


class PDFParser(Protocol):
    async def extract_text(
        self,
        file_path: Path,
        settings: Mapping[str, Any],
    ) -> DocumentText:
        """Extract text from a PDF file."""


class Chunker(Protocol):
    async def chunk_text(
        self,
        text: str,
        settings: Mapping[str, Any],
    ) -> list[Chunk]:
        """Split text into chunks suitable for retrieval."""


class VectorStore(Protocol):
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


class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        settings: Mapping[str, Any],
    ) -> list[RetrievedChunk]:
        """Retrieve candidate context for a query."""


class Reranker(Protocol):
    async def rerank(
        self,
        query: str,
        candidate_chunks: Sequence[Any],
        model: str,
        settings: Mapping[str, Any],
    ) -> Any:
        """Reorder retrieved chunks by query relevance."""


class ContextCompressor(Protocol):
    async def compress(
        self,
        compression_input: Any,
        settings: Mapping[str, Any] | None = None,
    ) -> Any:
        """Compress prompt inputs before generation."""


class RAGPipeline(Protocol):
    async def answer(
        self,
        query: str,
        conversation_settings: Mapping[str, Any],
        history: Sequence[Mapping[str, str]],
    ) -> str:
        """Answer a query using retrieval-augmented generation."""
