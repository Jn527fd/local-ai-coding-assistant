from __future__ import annotations

import json

import pytest

from app.ai.compressors.base import CompressionInput, CompressionOptions
from app.ai.compressors.manager import ContextCompressionManager
from app.ai.execution_context import AIExecutionContext, ResolvedComponent
from app.ai.pipelines import RetrievedSource
from app.schemas.chat import ChatHistoryMessage, ConversationSettings


class FakeEvidenceLLM:
    def __init__(self, response: object | None = None, fail: bool = False) -> None:
        self.response = response or {"evidence": []}
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    async def generate(self, prompt, history, settings):
        self.calls.append(
            {
                "prompt": prompt,
                "history": history,
                "settings": settings,
            }
        )
        if self.fail:
            raise RuntimeError("evidence failed")
        if isinstance(self.response, str):
            return self.response
        return json.dumps(self.response)


@pytest.mark.anyio
async def test_auto_context_preserves_recent_messages_and_trims_old_history():
    llm = FakeEvidenceLLM()
    manager = ContextCompressionManager(llm)
    history = [
        ChatHistoryMessage(
            role="user" if index % 2 == 0 else "assistant",
            content=f"message-{index} " + ("x" * 600),
        )
        for index in range(10)
    ]

    result = await manager.compress(
        _compression_input(
            llm=llm,
            history=history,
            latest_user_message="Preserve this exact latest request.",
            options=CompressionOptions(
                max_prompt_chars=1_700,
                recent_messages_to_keep=4,
                max_retrieved_context_chars=1_000,
            ),
        )
    )

    assert result.compressor_mode == "auto"
    assert result.compression_used is True
    assert result.stats.messages_trimmed > 0
    assert "message-0" not in [message.content[:9] for message in result.history]
    assert result.history[-1].content.startswith("message-9")
    assert result.memory_summary
    assert "Latest user message preserved verbatim" in result.memory_summary


@pytest.mark.anyio
async def test_auto_context_extracts_exact_evidence_when_budget_requires_it():
    source_text = (
        "Install QDRANT_COLLECTION=local_docs before indexing.\n"
        "Unrelated prose " * 120
    )
    llm = FakeEvidenceLLM(
        {
            "evidence": [
                {
                    "sourceNumber": 1,
                    "exactEvidence": "Install QDRANT_COLLECTION=local_docs before indexing.",
                }
            ]
        }
    )
    manager = ContextCompressionManager(llm)

    result = await manager.compress(
        _compression_input(
            llm=llm,
            latest_user_message="Which Qdrant collection setting is required?",
            sources=[_source(1, "doc-a", "chunk-a", source_text)],
            options=CompressionOptions(
                max_prompt_chars=900,
                recent_messages_to_keep=8,
                max_retrieved_context_chars=850,
            ),
        )
    )

    assert llm.calls
    assert result.stats.evidence_extracted is True
    assert result.stats.context_overflow is False
    assert result.retrieved_sources[0].source_number == 1
    assert result.retrieved_sources[0].document_id == "doc-a"
    assert result.retrieved_sources[0].chunk_id == "chunk-a"
    assert (
        result.retrieved_sources[0].text
        == "Install QDRANT_COLLECTION=local_docs before indexing."
    )


@pytest.mark.anyio
async def test_auto_context_rejects_drifted_evidence_and_falls_back():
    source_text = "Call get_user_by_id(user_id) before saving the record. " * 80
    llm = FakeEvidenceLLM(
        {
            "evidence": [
                {
                    "sourceNumber": 1,
                    "exactEvidence": "Call getUserById(userId) before saving the record.",
                }
            ]
        }
    )
    manager = ContextCompressionManager(llm)

    result = await manager.compress(
        _compression_input(
            llm=llm,
            latest_user_message="Which function checks the user?",
            sources=[_source(1, "doc-a", "chunk-a", source_text)],
            options=CompressionOptions(
                max_prompt_chars=850,
                recent_messages_to_keep=8,
                max_retrieved_context_chars=700,
            ),
        )
    )

    assert result.stats.evidence_extracted is False
    assert any("changed source text" in warning for warning in result.warnings)
    assert all(
        "getUserById(userId)" not in source.text
        for source in result.retrieved_sources
    )


@pytest.mark.anyio
async def test_auto_context_falls_back_when_evidence_extraction_fails():
    source_text = "banana retry policy " * 120
    llm = FakeEvidenceLLM(fail=True)
    manager = ContextCompressionManager(llm)

    result = await manager.compress(
        _compression_input(
            llm=llm,
            latest_user_message="What policy mentions banana?",
            sources=[_source(1, "doc-a", "chunk-a", source_text)],
            options=CompressionOptions(
                max_prompt_chars=850,
                recent_messages_to_keep=8,
                max_retrieved_context_chars=700,
            ),
        )
    )

    assert result.compression_used is True
    assert result.stats.evidence_extracted is False
    assert any("extraction failed" in warning for warning in result.warnings)


@pytest.mark.anyio
async def test_auto_context_reports_overflow_without_removing_latest_message():
    latest_message = "latest-user-message " + ("z" * 1_000)
    llm = FakeEvidenceLLM()
    manager = ContextCompressionManager(llm)

    result = await manager.compress(
        _compression_input(
            llm=llm,
            latest_user_message=latest_message,
            options=CompressionOptions(
                max_prompt_chars=300,
                recent_messages_to_keep=2,
                max_retrieved_context_chars=100,
            ),
        )
    )

    assert result.stats.context_overflow is True
    assert result.history == []
    assert any("latest user message was preserved" in warning for warning in result.warnings)


def _compression_input(
    llm: FakeEvidenceLLM,
    latest_user_message: str,
    history: list[ChatHistoryMessage] | None = None,
    sources: list[RetrievedSource] | None = None,
    options: CompressionOptions | None = None,
) -> CompressionInput:
    return CompressionInput(
        history=history or [],
        latest_user_message=latest_user_message,
        retrieved_sources=sources or [],
        execution_context=_execution_context(),
        options=options or CompressionOptions(),
        model="qwen3:4b",
    )


def _execution_context() -> AIExecutionContext:
    settings = ConversationSettings(
        llmModel="qwen3:4b",
        embedderModel="all-minilm",
        vectorDatabase="qdrant",
        contextCompressor="auto",
    )
    component = ResolvedComponent(
        setting_key="contextCompressor",
        category="contextCompressors",
        requested_id="auto",
        resolved_id="auto",
        valid=True,
        available=True,
        required=False,
        source="builtin",
    )
    return AIExecutionContext(
        conversation_id="conversation-a",
        conversation_settings=settings,
        resolved_llm_model="qwen3:4b",
        resolved_embedder_model="all-minilm",
        resolved_ocr_engine="paddleocr",
        resolved_pdf_parser="docling",
        resolved_chunker="recursive",
        resolved_vector_database="qdrant",
        resolved_rag_pipeline="hybrid",
        resolved_reranker="none",
        resolved_context_compressor="auto",
        resolved_vision_model="none",
        capabilities_snapshot={},
        components={"contextCompressor": component},
    )


def _source(
    source_number: int,
    document_id: str,
    chunk_id: str,
    text: str,
) -> RetrievedSource:
    return RetrievedSource(
        source_number=source_number,
        document_id=document_id,
        document_name=f"{document_id}.txt",
        chunk_id=chunk_id,
        chunk_index=source_number - 1,
        score=0.9,
        vector_score=0.9,
        text=text,
        text_preview=text[:120],
        final_rank=source_number,
        collection_id="collection-a",
    )
