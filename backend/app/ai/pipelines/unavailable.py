from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.components import ComponentNotImplementedError, RetrievedChunk


class UnavailableRetriever:
    """Explicit placeholder used when a retriever adapter has no implementation."""

    async def retrieve(
        self,
        query: str,
        settings: Mapping[str, Any],
    ) -> list[RetrievedChunk]:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for this retriever."
        )


class UnavailableContextCompressor:
    """Explicit placeholder used when a compressor adapter has no implementation."""

    async def compress(
        self,
        messages: Sequence[Mapping[str, str]],
        retrieved_context: Sequence[RetrievedChunk],
        settings: Mapping[str, Any],
    ) -> str:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for this context compressor."
        )


class UnavailableRAGPipeline:
    """Explicit placeholder used when a RAG pipeline adapter has no implementation."""

    async def answer(
        self,
        query: str,
        conversation_settings: Mapping[str, Any],
        history: Sequence[Mapping[str, str]],
    ) -> str:
        raise ComponentNotImplementedError(
            "No executable adapter is registered for this RAG pipeline."
        )

