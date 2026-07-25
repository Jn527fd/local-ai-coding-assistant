from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.execution_context import AISettingsResolver
from app.ai.vectorstores import VectorStoreManager
from app.routers import repos
from app.services.component_registry import CAPABILITY_KEYS


def capability(
    capability_id: str,
    capability_type: str,
    available: bool = True,
) -> dict[str, object]:
    return {
        "id": capability_id,
        "label": capability_id,
        "type": capability_type,
        "available": available,
        "source": "test",
    }


def repo_capabilities() -> dict[str, list[dict[str, object]]]:
    capabilities: dict[str, list[dict[str, object]]] = {
        key: [] for key in CAPABILITY_KEYS
    }
    capabilities["llmModels"] = [capability("qwen3:4b", "llmModel")]
    capabilities["embedderModels"] = [capability("embed-a", "embedderModel")]
    capabilities["ocrEngines"] = [capability("none", "ocrEngine")]
    capabilities["pdfParsers"] = []
    capabilities["chunkers"] = [capability("recursive", "chunker")]
    capabilities["vectorDatabases"] = [capability("chroma", "vectorDatabase")]
    capabilities["ragPipelines"] = [capability("basic", "ragPipeline")]
    capabilities["contextCompressors"] = [capability("none", "contextCompressor")]
    return capabilities


class FakeComponentRegistry:
    async def capabilities(self) -> dict[str, list[dict[str, object]]]:
        return repo_capabilities()


class FakeEmbedderProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    async def embed_texts(self, texts: list[str], model: str) -> list[list[float]]:
        self.calls.append((texts, model))
        return [self._embed(text) for text in texts]

    @staticmethod
    def _embed(text: str) -> list[float]:
        normalized = text.lower()
        return [
            1.0 if "banana" in normalized else 0.0,
            1.0 if "carrot" in normalized else 0.0,
            1.0 if "router" in normalized else 0.0,
        ]


class FakeOllamaService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, model: str, prompt: str) -> str:
        self.calls.append((model, prompt))
        return "Repository answer"


def configure_repo_tests(app: FastAPI, tmp_path: Path) -> FakeEmbedderProvider:
    app.state.vector_store_manager = VectorStoreManager(tmp_path / "vector_indexes")
    app.state.vector_store = app.state.vector_store_manager.default_store()
    app.state.ai_settings_resolver = AISettingsResolver(FakeComponentRegistry())
    embedder = FakeEmbedderProvider()
    app.state.embedder_provider = embedder
    return embedder


def write_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "sample-repo"
    repo_path.mkdir()
    (repo_path / "app.py").write_text(
        "class BananaRouter:\n"
        "    def route(self):\n"
        "        return 'banana route'\n",
        encoding="utf-8",
    )
    (repo_path / "notes.md").write_text(
        "# Notes\n\nCarrot setup details live here.\n",
        encoding="utf-8",
    )
    return repo_path


def index_repo(
    client: TestClient,
    auth_headers: dict[str, str],
    repo_path: Path,
) -> dict[str, object]:
    response = client.post(
        "/repos/index-local",
        headers=auth_headers,
        json={"path": str(repo_path)},
    )
    assert response.status_code == 200
    return response.json()


def test_legacy_repository_index_and_ask_still_work(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    repo_path = write_repo(tmp_path)
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[repos.get_ollama_service] = lambda: fake_ollama
    indexed = index_repo(client, auth_headers, repo_path)

    response = client.post(
        "/repos/ask",
        headers=auth_headers,
        json={
            "repo_name": indexed["repo_name"],
            "question": "Where is the banana router?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Repository answer"
    assert "app.py" in payload["sources"]
    assert payload["warnings"] == []
    assert payload["freshness"]["fresh"] is True
    assert fake_ollama.calls
    assert "BananaRouter" in fake_ollama.calls[0][1]
    assert "class: BananaRouter" in fake_ollama.calls[0][1]


def test_repository_ask_warns_when_index_is_stale(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    repo_path = write_repo(tmp_path)
    app.dependency_overrides[repos.get_ollama_service] = lambda: FakeOllamaService()
    indexed = index_repo(client, auth_headers, repo_path)
    (repo_path / "app.py").write_text("def changed():\n    return 'new'\n", encoding="utf-8")

    response = client.post(
        "/repos/ask",
        headers=auth_headers,
        json={"repo_name": indexed["repo_name"], "question": "banana"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["freshness"]["fresh"] is False
    assert "stale" in payload["warnings"][0]


def test_repository_ask_accepts_camel_case_repo_name_alias(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    repo_path = write_repo(tmp_path)
    app.dependency_overrides[repos.get_ollama_service] = lambda: FakeOllamaService()
    indexed = index_repo(client, auth_headers, repo_path)

    response = client.post(
        "/repos/ask",
        headers=auth_headers,
        json={
            "repoName": indexed["repo_name"],
            "question": "Where is the banana router?",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Repository answer"
    assert "app.py" in response.json()["sources"]


def test_repository_vector_index_and_search_are_opt_in(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    embedder = configure_repo_tests(app, tmp_path)
    repo_path = write_repo(tmp_path)

    empty = client.post(
        "/repos/search-vector",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "query": "banana",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )
    assert empty.status_code == 200
    assert empty.json()["results"] == []

    indexed = client.post(
        "/repos/index-local/vector",
        headers=auth_headers,
        json={
            "path": str(repo_path),
            "conversationId": "conversation-a",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )
    assert indexed.status_code == 200
    assert indexed.json()["collectionId"].startswith("repo-")
    assert indexed.json()["collection"]["sourceType"] == "repository"

    response = client.post(
        "/repos/search-vector",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "query": "banana",
            "topK": 1,
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["repoName"] == "sample-repo"
    assert results[0]["filePath"] == "app.py"
    assert results[0]["language"] == "python"
    assert results[0]["symbolName"] == "BananaRouter"
    assert results[0]["symbolKind"] == "class"
    assert embedder.calls


def test_document_vector_search_does_not_return_repository_vectors(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    configure_repo_tests(app, tmp_path)
    repo_path = write_repo(tmp_path)
    response = client.post(
        "/repos/index-local/vector",
        headers=auth_headers,
        json={
            "path": str(repo_path),
            "conversationId": "conversation-a",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )
    assert response.status_code == 200

    document_search = client.post(
        "/documents/search",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "query": "banana",
            "conversationSettings": {"embedderModel": "embed-a"},
        },
    )

    assert document_search.status_code == 200
    assert document_search.json()["results"] == []


def test_repository_path_must_be_inside_allowed_roots(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    outside_path = tmp_path.parent / "outside-repo"
    outside_path.mkdir(exist_ok=True)
    (outside_path / "app.py").write_text("print('outside')\n", encoding="utf-8")

    response = client.post(
        "/repos/index-local",
        headers=auth_headers,
        json={"path": str(outside_path)},
    )

    assert response.status_code == 403
    assert "allowed root" in response.json()["detail"]
