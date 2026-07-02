from collections.abc import Mapping, Sequence
from typing import Any

from app.ai.components import ComponentNotImplementedError, RetrievedChunk


class UnavailableRetriever:
    """Retriever scaffold that fails explicitly until retrieval is implemented."""

    async def retrieve(
        self,
        query: str,
        settings: Mapping[str, Any],
    ) -> list[RetrievedChunk]:
        raise ComponentNotImplementedError(
            "Retriever execution is not implemented in this phase."
        )


class UnavailableContextCompressor:
    """Context compressor scaffold for later RAG/chat phases."""

    async def compress(
        self,
        messages: Sequence[Mapping[str, str]],
        retrieved_context: Sequence[RetrievedChunk],
        settings: Mapping[str, Any],
    ) -> str:
        raise ComponentNotImplementedError(
            "Context compression is not implemented in this phase."
        )


class UnavailableRAGPipeline:
    """RAG pipeline scaffold that fails explicitly until RAG is implemented."""

    async def answer(
        self,
        query: str,
        conversation_settings: Mapping[str, Any],
        history: Sequence[Mapping[str, str]],
    ) -> str:
        raise ComponentNotImplementedError(
            "RAG pipeline execution is not implemented in this phase."
        )
