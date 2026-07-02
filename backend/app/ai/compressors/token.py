from __future__ import annotations

from dataclasses import replace

from app.ai.compressors.base import (
    CompressionInput,
    CompressionResult,
    CompressionStats,
    approximate_tokens,
    estimate_prompt_chars,
    trim_source_text,
)
from app.ai.pipelines import RetrievedSource
from app.schemas.chat import ChatHistoryMessage


class TokenContextCompressor:
    """Deterministic compressor that trims oldest history, then context."""

    async def compress(
        self,
        compression_input: CompressionInput,
        memory_summary: str | None = None,
        summary_generated: bool = False,
        initial_warnings: list[str] | None = None,
        mode: str = "token",
    ) -> CompressionResult:
        options = compression_input.options
        original_chars = estimate_prompt_chars(
            history=compression_input.history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=compression_input.retrieved_sources,
            memory_summary=memory_summary,
        )
        history = list(compression_input.history)
        sources = list(compression_input.retrieved_sources)
        warnings = list(initial_warnings or [])
        messages_trimmed = 0
        context_trimmed = 0

        target_history_count = min(options.recent_messages_to_keep, len(history))
        while (
            estimate_prompt_chars(
                history=history,
                latest_user_message=compression_input.latest_user_message,
                retrieved_sources=sources,
                memory_summary=memory_summary,
            )
            > options.max_prompt_chars
            and len(history) > target_history_count
        ):
            history.pop(0)
            messages_trimmed += 1

        while (
            estimate_prompt_chars(
                history=history,
                latest_user_message=compression_input.latest_user_message,
                retrieved_sources=sources,
                memory_summary=memory_summary,
            )
            > options.max_prompt_chars
            and history
        ):
            history.pop(0)
            messages_trimmed += 1

        sources, trim_count = self._fit_sources_to_context_budget(
            sources,
            options.max_retrieved_context_chars,
        )
        context_trimmed += trim_count

        while (
            estimate_prompt_chars(
                history=history,
                latest_user_message=compression_input.latest_user_message,
                retrieved_sources=sources,
                memory_summary=memory_summary,
            )
            > options.max_prompt_chars
            and sources
        ):
            sources.pop()
            context_trimmed += 1

        compressed_chars = estimate_prompt_chars(
            history=history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=sources,
            memory_summary=memory_summary,
        )
        if messages_trimmed:
            warnings.append(
                f"Token compression trimmed {messages_trimmed} older history "
                "message(s)."
            )
        if context_trimmed:
            warnings.append(
                f"Token compression trimmed {context_trimmed} retrieved "
                "context item(s)."
            )

        compression_used = (
            messages_trimmed > 0
            or context_trimmed > 0
            or summary_generated
            or bool(initial_warnings)
        )
        return CompressionResult(
            history=history,
            retrieved_sources=self._renumber_sources(sources),
            memory_summary=memory_summary,
            warnings=warnings,
            stats=CompressionStats(
                original_char_estimate=original_chars,
                compressed_char_estimate=compressed_chars,
                original_token_estimate=approximate_tokens(original_chars),
                compressed_token_estimate=approximate_tokens(compressed_chars),
                messages_trimmed=messages_trimmed,
                context_trimmed=context_trimmed,
                summary_generated=summary_generated,
            ),
            compression_used=compression_used,
            compressor_mode=mode,
        )

    @staticmethod
    def _fit_sources_to_context_budget(
        sources: list[RetrievedSource],
        max_context_chars: int,
    ) -> tuple[list[RetrievedSource], int]:
        if not sources:
            return sources, 0

        total_chars = sum(len(source.text) for source in sources)
        if total_chars <= max_context_chars:
            return sources, 0

        per_source = max(240, max_context_chars // len(sources))
        trimmed_sources: list[RetrievedSource] = []
        trim_count = 0
        for source in sources:
            trimmed = trim_source_text(source, per_source)
            if trimmed.text != source.text:
                trim_count += 1
            trimmed_sources.append(trimmed)
        return trimmed_sources, trim_count

    @staticmethod
    def _renumber_sources(
        sources: list[RetrievedSource],
    ) -> list[RetrievedSource]:
        return [
            replace(source, source_number=index, final_rank=index)
            for index, source in enumerate(sources, start=1)
        ]
