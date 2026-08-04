import json
from pathlib import Path

import pytest

from app.ai.components import Chunk
from app.ai.execution_context import AISettingsResolver
from app.ai.pipelines import DocumentRetrievalPipeline
from app.ai.vectorstores import JsonVectorStore
from app.evaluation import RetrievalEvalCase, run_retrieval_eval
from app.routers.chat import build_chat_prompt
from app.schemas.chat import ChatRequest, ConversationSettings
from app.services.component_registry import CAPABILITY_KEYS

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "retrieval_eval"


class EvalEmbedderProvider:
    vocabulary = (
        "python",
        "dependencies",
        "venv",
        "frontend",
        "ollama",
        "smollm2",
        "chat",
        "embedding",
        "document",
        "file",
        "types",
        "ocr",
        "security",
        "source",
        "control",
        "api",
        "keys",
    )

    async def embed_texts(
        self,
        texts: list[str],
        model: str,
    ) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    @classmethod
    def embed(cls, text: str) -> list[float]:
        normalized = text.lower()
        return [
            float(normalized.count(token))
            for token in cls.vocabulary
        ]


class FakeComponentRegistry:
    def __init__(self, embedder_model: str = "eval-embed") -> None:
        self.embedder_model = embedder_model

    async def capabilities(self) -> dict[str, list[dict[str, object]]]:
        capabilities: dict[str, list[dict[str, object]]] = {
            key: [] for key in CAPABILITY_KEYS
        }
        capabilities["llmModels"] = [capability("eval-llm", "llmModel")]
        capabilities["embedderModels"] = [
            capability(self.embedder_model, "embedderModel")
        ]
        capabilities["ocrEngines"] = [capability("none", "ocrEngine")]
        capabilities["chunkers"] = [capability("fixed", "chunker")]
        capabilities["vectorDatabases"] = [capability("qdrant", "vectorDatabase")]
        capabilities["ragPipelines"] = [capability("hybrid", "ragPipeline")]
        capabilities["contextCompressors"] = [
            capability("none", "contextCompressor")
        ]
        return capabilities


def capability(
    capability_id: str,
    capability_type: str,
) -> dict[str, object]:
    return {
        "id": capability_id,
        "label": capability_id,
        "type": capability_type,
        "available": True,
        "source": "eval-fixture",
    }


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


async def seed_eval_corpus(
    store: JsonVectorStore,
    corpus: dict[str, object],
) -> None:
    conversation_id = str(corpus["conversationId"])
    embedder_model = str(corpus["embedderModel"])
    vector_database = str(corpus["vectorDatabase"])
    chunks: list[Chunk] = []
    for document in corpus["documents"]:
        for raw_chunk in document["chunks"]:
            metadata = {
                "documentId": document["documentId"],
                "documentName": document["documentName"],
                "chunkId": raw_chunk["chunkId"],
                "chunkIndex": raw_chunk["chunkIndex"],
            }
            chunks.append(
                Chunk(
                    id=str(raw_chunk["chunkId"]),
                    text=str(raw_chunk["text"]),
                    metadata=metadata,
                )
            )
    collection_id = JsonVectorStore.collection_id(
        conversation_id,
        embedder_model,
        vector_database,
    )
    await store.upsert(
        collection=store.collection_ref(conversation_id, collection_id),
        chunks=chunks,
        embeddings=[EvalEmbedderProvider.embed(chunk.text) for chunk in chunks],
        metadata={
            "embedderModel": embedder_model,
            "vectorDatabase": vector_database,
            "documentIds": [
                str(document["documentId"])
                for document in corpus["documents"]
            ],
            "internalStore": "json",
        },
    )


def cases_from_fixture(items: list[dict[str, object]]) -> list[RetrievalEvalCase]:
    return [
        RetrievalEvalCase(
            id=str(item["id"]),
            query=str(item["query"]),
            expected_chunk_ids=tuple(item.get("expectedChunkIds", [])),
            top_k=int(item.get("topK", 3)),
            expected_warning_substrings=tuple(
                item.get("expectedWarningSubstrings", [])
            ),
        )
        for item in items
    ]


async def execution_context(
    embedder_model: str = "eval-embed",
) -> object:
    resolver = AISettingsResolver(FakeComponentRegistry(embedder_model))
    return await resolver.resolve(
        conversation_settings=ConversationSettings(
            llmModel="eval-llm",
            embedderModel=embedder_model,
            vectorDatabase="qdrant",
            ragPipeline="hybrid",
            contextCompressor="none",
        ),
        active_model="eval-llm",
        conversation_id="eval-chat",
    )


@pytest.mark.asyncio
async def test_retrieval_eval_baseline_metrics_are_stable(tmp_path: Path) -> None:
    corpus = load_fixture("corpus.json")
    expectations = load_fixture("expectations.json")
    store = JsonVectorStore(tmp_path / "vectors")
    await seed_eval_corpus(store, corpus)
    pipeline = DocumentRetrievalPipeline(EvalEmbedderProvider(), store)

    report = await run_retrieval_eval(
        pipeline=pipeline,
        execution_context=await execution_context(),
        conversation_id="eval-chat",
        cases=cases_from_fixture(expectations["cases"]),
    )

    assert report.mean_recall == 1.0
    assert report.mean_source_accuracy == 1.0
    assert report.warning_success_rate == 1.0
    assert report.metadata_success_rate == 1.0
    assert {
        case.case_id: case.best_rank
        for case in report.cases
    } == {
        "python-venv-setup": 1,
        "tiny-chat-model": 1,
        "document-file-types": 1,
        "local-secret-hygiene": 1,
    }


@pytest.mark.asyncio
async def test_retrieval_eval_measures_warning_behavior(tmp_path: Path) -> None:
    corpus = load_fixture("corpus.json")
    expectations = load_fixture("expectations.json")
    store = JsonVectorStore(tmp_path / "vectors")
    await seed_eval_corpus(store, corpus)
    pipeline = DocumentRetrievalPipeline(EvalEmbedderProvider(), store)

    report = await run_retrieval_eval(
        pipeline=pipeline,
        execution_context=await execution_context(embedder_model="other-embed"),
        conversation_id="eval-chat",
        cases=cases_from_fixture(expectations["warningCases"]),
    )

    assert report.mean_recall == 1.0
    assert report.warning_success_rate == 1.0
    assert report.cases[0].retrieved_chunk_ids == ()
    assert "does not match indexed embedder" in report.cases[0].warnings[0]


@pytest.mark.asyncio
async def test_retrieval_eval_sources_keep_prompt_numbering_and_shape(
    tmp_path: Path,
) -> None:
    corpus = load_fixture("corpus.json")
    expectations = load_fixture("expectations.json")
    store = JsonVectorStore(tmp_path / "vectors")
    await seed_eval_corpus(store, corpus)
    pipeline = DocumentRetrievalPipeline(EvalEmbedderProvider(), store)
    retrieval = await pipeline.retrieve(
        query=str(expectations["cases"][0]["query"]),
        conversation_id="eval-chat",
        execution_context=await execution_context(),
        top_k=2,
    )

    prompt = build_chat_prompt(
        ChatRequest(
            conversationId="eval-chat",
            message="Answer with citations.",
        ),
        max_chars=6000,
        retrieved_sources=retrieval.sources,
    )
    payloads = [source.response_payload() for source in retrieval.sources]

    assert "Source 1" in prompt.text
    assert "Source 2" in prompt.text
    assert "[Source N]" in prompt.text
    assert payloads[0]["sourceNumber"] == 1
    assert payloads[0]["finalRank"] == 1
    assert payloads[0]["vectorScore"] == payloads[0]["score"]
    assert payloads[0]["collectionId"]
    assert payloads[1]["sourceNumber"] == 2
    assert payloads[1]["finalRank"] == 2
