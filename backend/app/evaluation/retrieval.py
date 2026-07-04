from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ai.execution_context import AIExecutionContext
from app.ai.pipelines import DocumentRetrievalPipeline, RetrievedSource


@dataclass(frozen=True)
class RetrievalEvalCase:
    """One deterministic retrieval evaluation query."""

    id: str
    query: str
    expected_chunk_ids: tuple[str, ...]
    top_k: int = 3
    expected_warning_substrings: tuple[str, ...] = ()
    document_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalEvalMetrics:
    """Metrics for one retrieval evaluation case."""

    case_id: str
    retrieved_chunk_ids: tuple[str, ...]
    expected_chunk_ids: tuple[str, ...]
    recall: float
    best_rank: int | None
    source_accuracy: float
    warning_expectations_met: bool
    source_metadata_valid: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalEvalReport:
    """Aggregate deterministic retrieval evaluation result."""

    cases: tuple[RetrievalEvalMetrics, ...]
    mean_recall: float
    mean_source_accuracy: float
    warning_success_rate: float
    metadata_success_rate: float


async def run_retrieval_eval(
    *,
    pipeline: DocumentRetrievalPipeline,
    execution_context: AIExecutionContext,
    conversation_id: str,
    cases: list[RetrievalEvalCase],
) -> RetrievalEvalReport:
    """Run deterministic retrieval cases and return stable quality metrics."""

    results: list[RetrievalEvalMetrics] = []
    for case in cases:
        retrieval = await pipeline.retrieve(
            query=case.query,
            conversation_id=conversation_id,
            execution_context=execution_context,
            top_k=case.top_k,
            document_ids=list(case.document_ids),
        )
        retrieved_ids = tuple(source.chunk_id for source in retrieval.sources)
        expected = case.expected_chunk_ids
        hits = [chunk_id for chunk_id in expected if chunk_id in retrieved_ids]
        recall = len(hits) / len(expected) if expected else 1.0
        best_rank = _best_rank(retrieved_ids, expected)
        source_accuracy = _source_accuracy(retrieval.sources, expected)
        warning_expectations_met = all(
            any(expected_warning in warning for warning in retrieval.warnings)
            for expected_warning in case.expected_warning_substrings
        )
        results.append(
            RetrievalEvalMetrics(
                case_id=case.id,
                retrieved_chunk_ids=retrieved_ids,
                expected_chunk_ids=expected,
                recall=recall,
                best_rank=best_rank,
                source_accuracy=source_accuracy,
                warning_expectations_met=warning_expectations_met,
                source_metadata_valid=validate_source_metadata_shape(
                    retrieval.sources
                ),
                warnings=tuple(retrieval.warnings),
            )
        )

    return RetrievalEvalReport(
        cases=tuple(results),
        mean_recall=_mean(item.recall for item in results),
        mean_source_accuracy=_mean(item.source_accuracy for item in results),
        warning_success_rate=_mean(
            1.0 if item.warning_expectations_met else 0.0
            for item in results
        ),
        metadata_success_rate=_mean(
            1.0 if item.source_metadata_valid else 0.0
            for item in results
        ),
    )


def validate_source_metadata_shape(sources: list[RetrievedSource]) -> bool:
    """Return whether source payloads have stable numbering and metadata."""

    for index, source in enumerate(sources, start=1):
        payload: dict[str, Any] = source.response_payload()
        required = {
            "sourceNumber",
            "documentId",
            "documentName",
            "chunkId",
            "chunkIndex",
            "score",
            "vectorScore",
            "rerankScore",
            "finalRank",
            "textPreview",
            "collectionId",
        }
        if not required.issubset(payload):
            return False
        if payload["sourceNumber"] != index:
            return False
        if payload["finalRank"] != index:
            return False
        if not payload["documentId"] or not payload["documentName"]:
            return False
        if not payload["chunkId"] or not payload["textPreview"]:
            return False
    return True


def _best_rank(
    retrieved_chunk_ids: tuple[str, ...],
    expected_chunk_ids: tuple[str, ...],
) -> int | None:
    ranks = [
        retrieved_chunk_ids.index(chunk_id) + 1
        for chunk_id in expected_chunk_ids
        if chunk_id in retrieved_chunk_ids
    ]
    return min(ranks) if ranks else None


def _source_accuracy(
    sources: list[RetrievedSource],
    expected_chunk_ids: tuple[str, ...],
) -> float:
    if not expected_chunk_ids:
        return 1.0
    expected = set(expected_chunk_ids)
    source_ids = {source.chunk_id for source in sources}
    return len(source_ids & expected) / len(expected)


def _mean(values: Any) -> float:
    items = list(values)
    if not items:
        return 1.0
    return sum(float(value) for value in items) / len(items)
