from __future__ import annotations

from dataclasses import replace
import json
import logging
from typing import Any

from app.ai.components import LLMProvider
from app.ai.compressors.base import (
    CompressionInput,
    CompressionOptions,
    CompressionResult,
    CompressionStats,
    estimate_prompt_chars,
)
from app.ai.pipelines import RetrievedSource
from app.ai.compressors.token import TokenContextCompressor

logger = logging.getLogger(__name__)

SUPPORTED_MODES = {"auto", "none", "token", "summarizer", "semantic", "memory"}


class ContextCompressionManager:
    """Automatic layered context manager for final prompt assembly."""

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
    ) -> CompressionResult:
        requested_mode = str(
            compression_input.execution_context.conversation_settings.contextCompressor
            or "auto"
        ).strip()
        warnings: list[str] = []
        if requested_mode not in {"", "auto", "none"}:
            warnings.append(
                "Context management is automatic; the selected compressor "
                f"'{requested_mode}' was ignored."
            )

        original_chars = estimate_prompt_chars(
            history=compression_input.history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=compression_input.retrieved_sources,
            memory_summary=compression_input.memory_context,
        )
        if original_chars <= compression_input.options.max_prompt_chars:
            return CompressionResult.unchanged(
                compression_input,
                mode="auto",
                warnings=warnings,
            )

        token_result = await self.token_compressor.compress(
            compression_input,
            initial_warnings=warnings,
            mode="auto",
            drop_sources_to_fit=False,
        )
        if (
            token_result.stats.compressed_char_estimate
            <= compression_input.options.max_prompt_chars
        ):
            return self._with_structured_memory(token_result, compression_input)

        evidence_result = await self._extract_evidence_if_needed(
            compression_input=compression_input,
            current=token_result,
        )
        if (
            evidence_result.stats.compressed_char_estimate
            <= compression_input.options.max_prompt_chars
        ):
            return self._with_structured_memory(evidence_result, compression_input)

        overflow_result = self._force_fit_context(
            compression_input=compression_input,
            current=evidence_result,
        )
        return self._with_structured_memory(overflow_result, compression_input)

    async def _extract_evidence_if_needed(
        self,
        compression_input: CompressionInput,
        current: CompressionResult,
    ) -> CompressionResult:
        if not current.retrieved_sources:
            return current

        warnings = list(current.warnings)
        try:
            raw_response = await self.llm_provider.generate(
                prompt=self._evidence_prompt(
                    query=compression_input.latest_user_message,
                    sources=current.retrieved_sources,
                ),
                history=[],
                settings={
                    "model": compression_input.model,
                    "llmModel": compression_input.model,
                    "purpose": "context_evidence_extraction",
                },
            )
        except Exception as exc:
            logger.warning("Structured evidence extraction failed: %s", exc)
            warnings.append(
                "Structured evidence extraction failed; used deterministic "
                "context trimming instead."
            )
            return replace(current, warnings=warnings)

        extracted, drifted_count = self._parse_evidence(
            raw_response=raw_response,
            sources=current.retrieved_sources,
        )
        if not extracted:
            if drifted_count:
                warnings.append(
                    "Structured evidence extraction was discarded because it "
                    "changed source text."
                )
            else:
                warnings.append(
                    "Structured evidence extraction returned no usable "
                    "evidence; used deterministic context trimming instead."
                )
            return replace(current, warnings=warnings)

        if drifted_count:
            warnings.append(
                f"Discarded {drifted_count} extracted evidence item(s) that "
                "did not exactly match source text."
            )
        warnings.append(
            "Structured evidence extraction was used after deterministic "
            "trimming could not fit the context budget."
        )
        compressed_chars = estimate_prompt_chars(
            history=current.history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=extracted,
            memory_summary=current.memory_summary,
        )
        return replace(
            current,
            retrieved_sources=self.token_compressor._renumber_sources(extracted),
            warnings=warnings,
            stats=replace(
                current.stats,
                compressed_char_estimate=compressed_chars,
                compressed_token_estimate=max(1, (compressed_chars + 3) // 4),
                evidence_extracted=True,
            ),
            compression_used=True,
            compressor_mode="auto",
        )

    def _force_fit_context(
        self,
        compression_input: CompressionInput,
        current: CompressionResult,
    ) -> CompressionResult:
        sources = list(current.retrieved_sources)
        context_trimmed = current.stats.context_trimmed
        warnings = list(current.warnings)

        while (
            estimate_prompt_chars(
                history=current.history,
                latest_user_message=compression_input.latest_user_message,
                retrieved_sources=sources,
                memory_summary=current.memory_summary,
            )
            > compression_input.options.max_prompt_chars
            and sources
        ):
            sources.pop()
            context_trimmed += 1

        compressed_chars = estimate_prompt_chars(
            history=current.history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=sources,
            memory_summary=current.memory_summary,
        )
        overflow = compressed_chars > compression_input.options.max_prompt_chars
        if overflow:
            warnings.append(
                "Context still exceeds the configured prompt budget after "
                "automatic compression; the latest user message was preserved."
            )
        elif context_trimmed != current.stats.context_trimmed:
            warnings.append(
                "Automatic context management omitted lower-ranked source "
                "chunks to fit the prompt budget."
            )

        return replace(
            current,
            retrieved_sources=self.token_compressor._renumber_sources(sources),
            warnings=warnings,
            stats=replace(
                current.stats,
                compressed_char_estimate=compressed_chars,
                compressed_token_estimate=max(1, (compressed_chars + 3) // 4),
                context_trimmed=context_trimmed,
                context_overflow=overflow,
            ),
            compression_used=True,
            compressor_mode="auto",
        )

    @staticmethod
    def _with_structured_memory(
        result: CompressionResult,
        compression_input: CompressionInput,
    ) -> CompressionResult:
        if result.stats.messages_trimmed <= 0:
            if result.memory_summary or not compression_input.memory_context:
                return result
            return replace(result, memory_summary=compression_input.memory_context)
        if result.memory_summary and not compression_input.memory_context:
            return result
        recent_count = len(result.history)
        structured_state = (
            "Structured conversation state:\n"
            f"- Older messages omitted: {result.stats.messages_trimmed}\n"
            f"- Recent messages preserved verbatim: {recent_count}\n"
            "- Latest user message preserved verbatim."
        )
        memory_summary = (
            f"{compression_input.memory_context}\n\n{structured_state}"
            if compression_input.memory_context
            else structured_state
        )
        compressed_chars = estimate_prompt_chars(
            history=result.history,
            latest_user_message=compression_input.latest_user_message,
            retrieved_sources=result.retrieved_sources,
            memory_summary=memory_summary,
        )
        if compressed_chars > compression_input.options.max_prompt_chars:
            return result
        return replace(
            result,
            memory_summary=memory_summary,
            stats=replace(
                result.stats,
                compressed_char_estimate=compressed_chars,
                compressed_token_estimate=max(1, (compressed_chars + 3) // 4),
            ),
        )

    @staticmethod
    def _evidence_prompt(query: str, sources: list[RetrievedSource]) -> str:
        passages = "\n\n".join(
            (
                f"Source {source.source_number} "
                f"(documentId={source.document_id}, chunkId={source.chunk_id}):\n"
                f"{source.text}"
            )
            for source in sources
        )
        return (
            "You extract evidence for a retrieval-augmented prompt.\n"
            "Return JSON only, with this shape:\n"
            '{"evidence":[{"sourceNumber":1,"exactEvidence":"..."}]}\n'
            "Rules:\n"
            "- Include only text that is relevant to the query.\n"
            "- exactEvidence must be copied verbatim from the source passage.\n"
            "- Preserve code, identifiers, paths, numbers, and names exactly.\n"
            "- Do not paraphrase.\n\n"
            f"Query:\n{query}\n\n"
            f"Passages:\n{passages}\n"
        )

    @staticmethod
    def _parse_evidence(
        raw_response: str,
        sources: list[RetrievedSource],
    ) -> tuple[list[RetrievedSource], int]:
        try:
            payload = json.loads(raw_response.strip())
        except json.JSONDecodeError:
            return [], 0
        items: Any = payload.get("evidence") if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return [], 0

        sources_by_number = {source.source_number: source for source in sources}
        snippets_by_number: dict[int, list[str]] = {}
        drifted_count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                source_number = int(item.get("sourceNumber"))
            except (TypeError, ValueError):
                continue
            evidence = str(item.get("exactEvidence") or "").strip()
            source = sources_by_number.get(source_number)
            if not source or not evidence:
                continue
            if evidence not in source.text:
                drifted_count += 1
                continue
            snippets_by_number.setdefault(source_number, []).append(evidence)

        extracted: list[RetrievedSource] = []
        for source in sources:
            snippets = snippets_by_number.get(source.source_number)
            if not snippets:
                continue
            text = "\n...\n".join(snippets)
            extracted.append(
                replace(
                    source,
                    text=text,
                    text_preview=_preview(text),
                )
            )
        return extracted, drifted_count


def _preview(text: str, max_chars: int = 280) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 14].rstrip()} [truncated]"


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
