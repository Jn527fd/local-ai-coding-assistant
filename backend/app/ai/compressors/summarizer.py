from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from app.ai.components import LLMProvider
from app.ai.compressors.base import (
    CompressionInput,
    CompressionResult,
    approximate_tokens,
    estimate_prompt_chars,
)
from app.ai.compressors.token import TokenContextCompressor
from app.schemas.chat import ChatHistoryMessage


class SummarizerContextCompressor:
    """LLM-backed compressor that summarizes older chat history."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        token_compressor: TokenContextCompressor | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.token_compressor = token_compressor or TokenContextCompressor()

    async def compress(
        self,
        compression_input: CompressionInput,
        settings: Mapping[str, object] | None = None,
        initial_warnings: list[str] | None = None,
        mode: str = "summarizer",
    ) -> CompressionResult:
        options = compression_input.options
        history = list(compression_input.history)
        keep_count = min(options.recent_messages_to_keep, len(history))
        older_history = history[:-keep_count] if keep_count else history
        recent_history = history[-keep_count:] if keep_count else []

        if not older_history:
            return await self.token_compressor.compress(
                compression_input,
                initial_warnings=initial_warnings,
                mode=mode,
            )

        original_chars = estimate_prompt_chars(
            history=compression_input.history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=compression_input.retrieved_sources,
        )
        summary = await self._summarize(
            older_history=older_history,
            latest_user_message=compression_input.latest_user_message,
            model=compression_input.model,
            max_summary_chars=options.max_summary_chars,
        )
        summary_input = CompressionInput(
            history=recent_history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=compression_input.retrieved_sources,
            execution_context=compression_input.execution_context,
            options=compression_input.options,
            model=compression_input.model,
        )
        result = await self.token_compressor.compress(
            summary_input,
            memory_summary=summary,
            summary_generated=True,
            initial_warnings=initial_warnings,
            mode=mode,
        )
        return replace(
            result,
            stats=replace(
                result.stats,
                original_char_estimate=original_chars,
                original_token_estimate=approximate_tokens(original_chars),
                messages_trimmed=(
                    result.stats.messages_trimmed + len(older_history)
                ),
                summary_generated=True,
            ),
            compression_used=True,
        )

    async def _summarize(
        self,
        older_history: list[ChatHistoryMessage],
        latest_user_message: str,
        model: str,
        max_summary_chars: int,
    ) -> str:
        transcript = "\n".join(
            f"{message.role.title()}: {message.content}"
            for message in older_history
        )
        prompt = (
            "Summarize the older conversation history into compact memory for "
            "a local chat model.\n"
            "Preserve durable facts, user preferences, decisions, unresolved "
            "questions, and constraints.\n"
            "Do not answer the latest user message. Do not mention source "
            "citation metadata.\n"
            f"Keep the summary under {max_summary_chars} characters.\n\n"
            "Older conversation:\n"
            f"{transcript}\n\n"
            "Latest user message, for continuity only:\n"
            f"{latest_user_message}\n\n"
            "Memory summary:"
        )
        summary = await self.llm_provider.generate(
            prompt=prompt,
            history=[],
            settings={"model": model},
        )
        summary = " ".join(summary.split())
        if len(summary) > max_summary_chars:
            summary = f"{summary[: max(0, max_summary_chars - 14)].rstrip()} [truncated]"
        return summary
