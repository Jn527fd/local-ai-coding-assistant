from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from math import ceil
from typing import Any

from app.ai.execution_context import AIExecutionContext
from app.ai.pipelines import RetrievedSource
from app.schemas.chat import ChatHistoryMessage


@dataclass(frozen=True)
class CompressionOptions:
    """Budget knobs for prompt context compression."""

    max_prompt_chars: int = 12_000
    recent_messages_to_keep: int = 10
    max_retrieved_context_chars: int = 6_000
    max_summary_chars: int = 2_000


@dataclass(frozen=True)
class CompressionInput:
    """Inputs available to a context compressor."""

    history: Sequence[ChatHistoryMessage]
    latest_user_message: str
    retrieved_sources: Sequence[RetrievedSource]
    execution_context: AIExecutionContext
    options: CompressionOptions
    model: str
    memory_context: str | None = None


@dataclass(frozen=True)
class CompressionStats:
    """Compression counters and estimates returned to the frontend."""

    original_char_estimate: int
    compressed_char_estimate: int
    original_token_estimate: int
    compressed_token_estimate: int
    messages_trimmed: int = 0
    context_trimmed: int = 0
    summary_generated: bool = False
    evidence_extracted: bool = False
    context_overflow: bool = False

    def response_payload(self) -> dict[str, Any]:
        return {
            "originalCharEstimate": self.original_char_estimate,
            "compressedCharEstimate": self.compressed_char_estimate,
            "originalTokenEstimate": self.original_token_estimate,
            "compressedTokenEstimate": self.compressed_token_estimate,
            "messagesTrimmed": self.messages_trimmed,
            "contextTrimmed": self.context_trimmed,
            "summaryGenerated": self.summary_generated,
            "evidenceExtracted": self.evidence_extracted,
            "contextOverflow": self.context_overflow,
        }


@dataclass(frozen=True)
class CompressionResult:
    """Compressed prompt parts plus warnings and metadata."""

    history: list[ChatHistoryMessage]
    retrieved_sources: list[RetrievedSource]
    memory_summary: str | None
    warnings: list[str]
    stats: CompressionStats
    compression_used: bool
    compressor_mode: str

    @staticmethod
    def unchanged(
        compression_input: CompressionInput,
        mode: str = "none",
        warnings: list[str] | None = None,
    ) -> CompressionResult:
        original_chars = estimate_prompt_chars(
            history=compression_input.history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=compression_input.retrieved_sources,
            memory_summary=compression_input.memory_context,
        )
        return CompressionResult(
            history=list(compression_input.history),
            retrieved_sources=list(compression_input.retrieved_sources),
            memory_summary=compression_input.memory_context,
            warnings=warnings or [],
            stats=CompressionStats(
                original_char_estimate=original_chars,
                compressed_char_estimate=original_chars,
                original_token_estimate=approximate_tokens(original_chars),
                compressed_token_estimate=approximate_tokens(original_chars),
            ),
            compression_used=False,
            compressor_mode=mode,
        )


def approximate_tokens(char_count: int) -> int:
    return max(1, ceil(max(0, char_count) / 4))


def estimate_prompt_chars(
    history: Sequence[ChatHistoryMessage],
    latest_user_message: str,
    retrieved_sources: Sequence[RetrievedSource] = (),
    memory_summary: str | None = None,
) -> int:
    """Estimate final prompt size without importing the router prompt builder."""

    total = len(latest_user_message) + 128
    if history:
        total += 72
    for message in history:
        total += len(message.content) + 16
    if memory_summary:
        total += len(memory_summary) + 48
    if retrieved_sources:
        total += 220
    for source in retrieved_sources:
        total += len(source.text) + len(source.document_name) + len(source.chunk_id) + 48
    return total


def trim_source_text(
    source: RetrievedSource,
    max_chars: int,
) -> RetrievedSource:
    text = source.text.strip()
    if len(text) <= max_chars:
        return source
    truncated = f"{text[: max(0, max_chars - 14)].rstrip()} [truncated]"
    return replace(
        source,
        text=truncated,
        text_preview=_preview(truncated),
    )


def _preview(text: str, max_chars: int = 280) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 14].rstrip()} [truncated]"


class ContextCompressor:
    async def compress(
        self,
        compression_input: CompressionInput,
        settings: Mapping[str, Any] | None = None,
    ) -> CompressionResult:
        raise NotImplementedError
