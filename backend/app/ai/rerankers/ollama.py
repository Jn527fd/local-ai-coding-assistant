from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import re
from typing import Any

from app.ai.components import ComponentUnavailableError
from app.ai.pipelines import RetrievedSource
from app.services.ollama_service import OllamaService

SCORE_PATTERN = re.compile(
    r"(?<![\d.])(?:0(?:\.\d+)?|1(?:\.0+)?)(?![\d.])"
)


@dataclass(frozen=True)
class RerankResult:
    """Reranked document candidates and non-fatal scoring warnings."""

    sources: list[RetrievedSource]
    warnings: list[str]


class OllamaRerankerProvider:
    """Conservative reranker adapter backed by Ollama text generation."""

    def __init__(self, ollama_service: OllamaService) -> None:
        self.ollama_service = ollama_service

    async def rerank(
        self,
        query: str,
        candidate_chunks: Sequence[RetrievedSource],
        model: str,
        settings: Mapping[str, Any],
    ) -> RerankResult:
        if not model.strip():
            raise ComponentUnavailableError(
                "Ollama reranking requires a resolved reranker model."
            )

        max_passage_chars = self._coerce_positive_int(
            settings.get("maxPassageChars"),
            default=2_000,
        )
        warnings: list[str] = []
        scored_sources: list[RetrievedSource] = []

        for source in candidate_chunks:
            prompt = self._build_prompt(
                query=query,
                passage=source.text[:max_passage_chars],
            )
            raw_score = await self.ollama_service.generate(
                model=model.strip(),
                prompt=prompt,
            )
            score = self._parse_score(raw_score)
            if score is None:
                score = 0.0
                warnings.append(
                    "Reranker returned a non-numeric score for "
                    f"{source.document_name} chunk {source.chunk_index}; "
                    "assigned 0.0."
                )
            scored_sources.append(
                replace(
                    source,
                    score=score,
                    rerank_score=score,
                )
            )

        scored_sources.sort(
            key=lambda item: (
                item.rerank_score if item.rerank_score is not None else 0.0,
                item.vector_score,
            ),
            reverse=True,
        )
        return RerankResult(sources=scored_sources, warnings=warnings)

    @staticmethod
    def _build_prompt(query: str, passage: str) -> str:
        return (
            "You are a relevance scoring model.\n"
            "Score how relevant the passage is to the query.\n"
            "Return only a number from 0 to 1.\n\n"
            "Query:\n"
            f"{query}\n\n"
            "Passage:\n"
            f"{passage}\n\n"
            "Score:"
        )

    @staticmethod
    def _parse_score(value: str) -> float | None:
        match = SCORE_PATTERN.search(value.strip())
        if match is None:
            return None
        try:
            score = float(match.group(0))
        except ValueError:
            return None
        if score < 0.0:
            return 0.0
        if score > 1.0:
            return 1.0
        return score

    @staticmethod
    def _coerce_positive_int(value: object, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, parsed)
