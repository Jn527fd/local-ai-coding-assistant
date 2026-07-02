from __future__ import annotations

import logging

from app.ai.components import LLMProvider
from app.ai.compressors.base import (
    CompressionInput,
    CompressionOptions,
    CompressionResult,
)
from app.ai.compressors.summarizer import SummarizerContextCompressor
from app.ai.compressors.token import TokenContextCompressor

logger = logging.getLogger(__name__)

SUPPORTED_MODES = {"none", "token", "summarizer", "semantic", "memory"}


class ContextCompressionManager:
    """Dispatch optional prompt compression by resolved conversation setting."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        token_compressor: TokenContextCompressor | None = None,
        summarizer: SummarizerContextCompressor | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.token_compressor = token_compressor or TokenContextCompressor()
        self.summarizer = summarizer or SummarizerContextCompressor(
            llm_provider=llm_provider,
            token_compressor=self.token_compressor,
        )

    async def compress(
        self,
        compression_input: CompressionInput,
    ) -> CompressionResult:
        mode = (
            compression_input.execution_context.resolved_context_compressor
            or "none"
        ).strip()
        if mode not in SUPPORTED_MODES:
            mode = "none"

        if mode == "none":
            return CompressionResult.unchanged(compression_input)

        if mode == "token":
            return await self.token_compressor.compress(compression_input)

        if mode == "semantic":
            return await self.token_compressor.compress(
                compression_input,
                initial_warnings=[
                    "Semantic context compression is not implemented yet; "
                    "used token compression instead."
                ],
                mode="semantic",
            )

        if mode == "memory":
            try:
                return await self.summarizer.compress(
                    compression_input,
                    initial_warnings=[
                        "Memory context compression is not implemented yet; "
                        "used summarizer compression instead."
                    ],
                    mode="memory",
                )
            except Exception as exc:
                logger.warning("Memory compression fallback failed: %s", exc)
                return await self.token_compressor.compress(
                    compression_input,
                    initial_warnings=[
                        "Memory context compression is not implemented yet; "
                        "summarizer fallback failed, so token compression was "
                        "used instead."
                    ],
                    mode="memory",
                )

        try:
            return await self.summarizer.compress(compression_input)
        except Exception as exc:
            logger.warning("Summarizer compression failed: %s", exc)
            return await self.token_compressor.compress(
                compression_input,
                initial_warnings=[
                    "Summarizer context compression failed; used token "
                    "compression instead."
                ],
                mode="summarizer",
            )


def build_compression_options(settings: object) -> CompressionOptions:
    return CompressionOptions(
        max_prompt_chars=int(
            getattr(settings, "context_compression_max_prompt_chars", 12_000)
        ),
        recent_messages_to_keep=int(
            getattr(settings, "context_compression_recent_messages_to_keep", 10)
        ),
        max_retrieved_context_chars=int(
            getattr(settings, "context_compression_max_retrieved_context_chars", 6_000)
        ),
        max_summary_chars=int(
            getattr(settings, "context_compression_max_summary_chars", 2_000)
        ),
    )
