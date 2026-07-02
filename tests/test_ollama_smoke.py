from __future__ import annotations

import os
from pathlib import Path
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient

from app.auth.credentials import hash_password, write_credentials_file
from app.config import Settings
from app.main import create_app


pytestmark = [pytest.mark.ollama, pytest.mark.ollama_smoke, pytest.mark.integration]

TEST_API_KEY = "ollama-smoke-test-key"
TEST_USERNAME = "ollama-smoke-user"
TEST_PASSWORD = "ollama-smoke-password"
DEFAULT_LLM = "smollm2:135m"
DEFAULT_EMBEDDER = "all-minilm"
DEFAULT_RERANKER = "qllama/bge-reranker-v2-m3:q4_k_m"


def ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def requested_llm() -> str:
    return os.environ.get("OLLAMA_TEST_LLM", DEFAULT_LLM)


def requested_embedder() -> str:
    return os.environ.get("OLLAMA_TEST_EMBEDDER", DEFAULT_EMBEDDER)


def requested_reranker() -> str:
    return os.environ.get("OLLAMA_TEST_RERANKER", DEFAULT_RERANKER)


def fetch_ollama_tags() -> list[str]:
    try:
        with urllib.request.urlopen(f"{ollama_base_url()}/api/tags", timeout=10) as response:
            payload = response.read().decode("utf-8")
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"live Ollama daemon is not reachable at {ollama_base_url()}: {exc}")

    import json

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        pytest.skip(f"Ollama /api/tags returned invalid JSON: {exc}")

    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        pytest.skip("Ollama /api/tags did not return a models list")

    names = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("name") or model.get("model")
        if isinstance(name, str) and name:
            names.append(name)
    return names


def resolve_model(requested: str, installed: list[str]) -> str:
    candidates = [requested]
    if ":" not in requested:
        candidates.append(f"{requested}:latest")
    for candidate in candidates:
        if candidate in installed:
            return candidate

    requested_repo = requested.split(":", 1)[0]
    for name in installed:
        if name.split(":", 1)[0] == requested_repo:
            return name

    pytest.skip(
        f"required Ollama smoke model is not installed: {requested}. "
        "Run 'make setup-ollama-smoke' first."
    )


@pytest.fixture(scope="session")
def live_ollama_models() -> dict[str, str]:
    installed = fetch_ollama_tags()
    if not installed:
        pytest.skip("Ollama is reachable but has no installed models")
    return {
        "llm": resolve_model(requested_llm(), installed),
        "embedder": resolve_model(requested_embedder(), installed),
    }


@pytest.fixture
def live_client(
    tmp_path: Path,
    live_ollama_models: dict[str, str],
) -> TestClient:
    credentials_file = tmp_path / "config" / "credentials.json"
    local_settings_file = tmp_path / "config" / "app-settings.json"
    write_credentials_file(
        credentials_file,
        [
            {
                "username": TEST_USERNAME,
                "password_hash": hash_password(TEST_PASSWORD),
            }
        ],
    )
    settings = Settings(
        api_key=TEST_API_KEY,
        credentials_file=credentials_file,
        local_settings_file=local_settings_file,
        data_directory=tmp_path,
        ollama_base_url=ollama_base_url(),
        default_model=live_ollama_models["llm"],
        ollama_timeout_seconds=float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "120")),
        ollama_num_predict=int(os.environ.get("OLLAMA_NUM_PREDICT", "96")),
        document_chunk_size=600,
        embedding_batch_size=2,
        rag_top_k=2,
        rag_candidate_k=3,
    )
    with TestClient(create_app(settings)) as client:
        yield client


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_API_KEY}"}


def conversation_settings(models: dict[str, str], **overrides: str) -> dict[str, str]:
    settings = {
        "llmModel": models["llm"],
        "embedderModel": models["embedder"],
        "chunker": "recursive",
        "vectorDatabase": "chroma",
        "ragPipeline": "hybrid",
        "reranker": "none",
        "contextCompressor": "none",
    }
    settings.update(overrides)
    return settings


def upload_process_index_document(
    client: TestClient,
    models: dict[str, str],
    conversation_id: str,
) -> str:
    text = (
        "The amber capacitor calibration note says the zebra threshold is 42. "
        "This smoke document exists only to validate local embeddings and RAG wiring."
    )
    upload_response = client.post(
        "/documents/upload",
        headers=auth_headers(),
        data={
            "conversationId": conversation_id,
            "conversationSettings": "{}",
        },
        files={"file": ("smoke-notes.txt", text.encode("utf-8"), "text/plain")},
    )
    assert upload_response.status_code == 200, upload_response.text
    document_id = upload_response.json()["documentId"]

    settings = conversation_settings(models)
    process_response = client.post(
        f"/documents/{document_id}/process",
        headers=auth_headers(),
        json={
            "conversationId": conversation_id,
            "conversationSettings": settings,
        },
    )
    assert process_response.status_code == 200, process_response.text
    assert process_response.json()["chunkCount"] >= 1

    index_response = client.post(
        f"/documents/{document_id}/index",
        headers=auth_headers(),
        json={
            "conversationId": conversation_id,
            "conversationSettings": settings,
        },
    )
    assert index_response.status_code == 200, index_response.text
    assert index_response.json()["indexedChunks"] >= 1
    return document_id


def test_ollama_smoke_tags_and_generation(
    live_client: TestClient,
    live_ollama_models: dict[str, str],
) -> None:
    tags = fetch_ollama_tags()

    response = live_client.post(
        "/chat",
        headers=auth_headers(),
        json={
            "conversationId": "ollama-smoke-chat",
            "message": "Reply with one short sentence saying the smoke test is running.",
            "conversationSettings": conversation_settings(live_ollama_models),
        },
    )

    assert live_ollama_models["llm"] in tags
    assert live_ollama_models["embedder"] in tags
    assert response.status_code == 200, response.text
    assert response.json()["answer"].strip()


def test_ollama_smoke_embeddings_index_search_and_rag_chat(
    live_client: TestClient,
    live_ollama_models: dict[str, str],
) -> None:
    conversation_id = "ollama-smoke-rag"
    document_id = upload_process_index_document(
        live_client,
        live_ollama_models,
        conversation_id,
    )

    search_response = live_client.post(
        "/documents/search",
        headers=auth_headers(),
        json={
            "conversationId": conversation_id,
            "query": "What is the zebra threshold in the amber capacitor note?",
            "topK": 2,
            "conversationSettings": conversation_settings(live_ollama_models),
        },
    )
    assert search_response.status_code == 200, search_response.text
    search_results = search_response.json()["results"]
    assert search_results
    assert search_results[0]["documentId"] == document_id

    chat_response = live_client.post(
        "/chat",
        headers=auth_headers(),
        json={
            "conversationId": conversation_id,
            "message": "Use the document context: what is the zebra threshold?",
            "conversationSettings": conversation_settings(live_ollama_models),
            "ragOptions": {
                "enabled": True,
                "topK": 2,
                "candidateK": 3,
                "includeSources": True,
            },
        },
    )
    assert chat_response.status_code == 200, chat_response.text
    payload = chat_response.json()
    assert payload["answer"].strip()
    assert payload["ragUsed"] is True
    assert payload["sources"]
    assert payload["sources"][0]["documentId"] == document_id


def test_ollama_smoke_optional_reranker(
    live_client: TestClient,
    live_ollama_models: dict[str, str],
) -> None:
    if os.environ.get("RUN_RERANKER_TESTS") != "1":
        pytest.skip("set RUN_RERANKER_TESTS=1 to run live reranker smoke")

    reranker_model = resolve_model(requested_reranker(), fetch_ollama_tags())
    conversation_id = "ollama-smoke-reranker"
    document_id = upload_process_index_document(
        live_client,
        live_ollama_models,
        conversation_id,
    )
    settings = conversation_settings(
        live_ollama_models,
        ragPipeline="reranked",
        reranker=reranker_model,
    )

    response = live_client.post(
        "/chat",
        headers=auth_headers(),
        json={
            "conversationId": conversation_id,
            "message": "Use the document context: what is the zebra threshold?",
            "conversationSettings": settings,
            "ragOptions": {
                "enabled": True,
                "topK": 1,
                "candidateK": 2,
                "includeSources": True,
            },
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"].strip()
    assert payload["sources"]
    assert payload["sources"][0]["documentId"] == document_id
    assert payload["rerankingUsed"] is True
    assert payload["rerankerModel"] == reranker_model
