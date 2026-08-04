from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.vectorstores import VectorStoreManager
from app.services.component_registry import (
    CAPABILITY_KEYS,
    CAPABILITY_STATUS_DISCOVERY_ONLY,
    CAPABILITY_STATUS_FALLBACK,
    CAPABILITY_STATUS_IMPLEMENTED,
    CAPABILITY_STATUS_UNAVAILABLE,
    ComponentRegistry,
)
from app.services.ollama_service import (
    InstalledOllamaModel,
    OllamaUnavailableError,
)


def installed_model(
    name: str,
    parameter_size: str = "4.0B",
    parameters_billion: float | None = 4.0,
    size_bytes: int = 2_500_000_000,
) -> InstalledOllamaModel:
    return InstalledOllamaModel(
        name=name,
        size_bytes=size_bytes,
        parameter_size=parameter_size,
        parameters_billion=parameters_billion,
        family=name.split(":", maxsplit=1)[0],
        quantization_level="Q4_K_M",
        modified_at="2026-06-27T00:00:00Z",
    )


class FakeComponentOllamaService:
    def __init__(
        self,
        installed_models: list[InstalledOllamaModel] | None = None,
    ) -> None:
        self.installed_models = installed_models or []

    async def list_installed_models(self) -> list[InstalledOllamaModel]:
        return list(self.installed_models)


class UnavailableOllamaService:
    async def list_installed_models(self) -> list[InstalledOllamaModel]:
        raise OllamaUnavailableError("Ollama is offline.")


class FakeModelManager:
    async def status(self) -> dict[str, object]:
        return {
            "active_model": "qwen3:4b",
            "supported_models": [
                {
                    "name": "qwen3:4b",
                    "label": "qwen3:4b",
                    "parameters_billion": 4.0,
                    "parameter_size": "4.0B",
                    "size_bytes": 2_500_000_000,
                    "size_display": "2.3 GiB",
                    "family": "qwen3",
                    "quantization_level": "Q4_K_M",
                }
            ],
            "installed_models": ["qwen3:4b"],
            "ollama_connected": True,
            "switching": False,
            "target_model": None,
            "phase": "idle",
            "progress": None,
            "message": "Ready",
            "error": None,
            "warning": None,
        }


def capability_ids(
    response_json: dict[str, list[dict[str, object]]],
    key: str,
) -> set[str]:
    return {str(item["id"]) for item in response_json[key]}


def capability_by_id(
    response_json: dict[str, list[dict[str, object]]],
    key: str,
    capability_id: str,
) -> dict[str, object]:
    return next(item for item in response_json[key] if item["id"] == capability_id)


def assert_execution_metadata(
    item: dict[str, object],
    status: str,
    implemented: bool,
) -> None:
    assert item["implementationStatus"] == status
    assert item["implemented"] is implemented
    assert isinstance(item["execution"], dict)
    execution = item["execution"]
    assert execution["status"] == status
    assert execution["implemented"] is implemented
    assert isinstance(execution["mode"], str)
    assert isinstance(execution["description"], str)
    assert execution["description"]


def test_component_capabilities_endpoint_returns_required_categories(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.state.component_registry = ComponentRegistry(
        FakeComponentOllamaService([installed_model("qwen3:4b")])
    )

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert set(data) == set(CAPABILITY_KEYS)
    for key in CAPABILITY_KEYS:
        assert isinstance(data[key], list)

    assert {"none", "tesseract", "ocrmypdf", "paddleocr", "easyocr", "docling"} <= (
        capability_ids(data, "ocrEngines")
    )
    assert {"pymupdf", "pdfplumber", "docling"} <= capability_ids(
        data,
        "pdfParsers",
    )
    assert {"fixed", "recursive", "semantic", "document-aware"} <= capability_ids(
        data,
        "chunkers",
    )


def test_component_capabilities_does_not_crash_when_ollama_is_unavailable(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.state.component_registry = ComponentRegistry(UnavailableOllamaService())

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["llmModels"] == []
    assert data["embedderModels"] == []
    assert data["rerankerModels"] == []
    assert data["visionModels"] == []
    assert "none" in capability_ids(data, "ocrEngines")


def test_component_capabilities_categorizes_known_ollama_model_names(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.state.component_registry = ComponentRegistry(
        FakeComponentOllamaService(
            [
                installed_model("qwen3:4b"),
                installed_model("nomic-embed-text:latest", "137M", 0.137),
                installed_model("bge-reranker-v2:m3", "568M", 0.568),
                installed_model("llava:latest", "7.0B", 7.0),
                installed_model("qwen2.5vl:7b", "7.0B", 7.0),
            ]
        )
    )

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert capability_ids(data, "llmModels") == {"qwen3:4b"}
    assert capability_ids(data, "embedderModels") == {
        "nomic-embed-text:latest"
    }
    assert capability_ids(data, "rerankerModels") == {"bge-reranker-v2:m3"}
    assert capability_ids(data, "visionModels") == {
        "llava:latest",
        "qwen2.5vl:7b",
    }
    llm = data["llmModels"][0]
    assert llm["source"] == "ollama"
    assert llm["type"] == "llmModel"
    assert llm["available"] is True
    assert_execution_metadata(llm, CAPABILITY_STATUS_IMPLEMENTED, True)
    assert llm["name"] == "qwen3:4b"
    assert llm["size"] == 2_500_000_000
    assert llm["modifiedAt"] == "2026-06-27T00:00:00Z"
    assert llm["details"]["family"] == "qwen3"

    vision = capability_by_id(data, "visionModels", "llava:latest")
    assert_execution_metadata(vision, CAPABILITY_STATUS_IMPLEMENTED, True)


def test_component_capabilities_reports_execution_status_for_static_options(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.state.component_registry = ComponentRegistry(
        FakeComponentOllamaService([installed_model("qwen3:4b")])
    )

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert_execution_metadata(
        capability_by_id(data, "chunkers", "recursive"),
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )
    assert_execution_metadata(
        capability_by_id(data, "chunkers", "semantic"),
        CAPABILITY_STATUS_FALLBACK,
        False,
    )
    assert_execution_metadata(
        capability_by_id(data, "vectorDatabases", "qdrant"),
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )
    assert capability_by_id(data, "vectorDatabases", "qdrant")["fallbackStore"] in {
        "json",
        "qdrant",
    }
    assert "chroma" not in capability_ids(data, "vectorDatabases")
    assert_execution_metadata(
        capability_by_id(data, "contextCompressors", "token"),
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )
    assert_execution_metadata(
        capability_by_id(data, "contextCompressors", "memory"),
        CAPABILITY_STATUS_FALLBACK,
        False,
    )


def test_component_capabilities_reports_qdrant_as_only_vector_database(
    app: FastAPI,
    logged_in_client: TestClient,
    tmp_path,
) -> None:
    app.state.component_registry = ComponentRegistry(
        FakeComponentOllamaService([installed_model("qwen3:4b")]),
        vector_store_manager=VectorStoreManager(tmp_path / "vectors", backend="qdrant"),
    )

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert capability_ids(data, "vectorDatabases") == {"qdrant"}
    qdrant = capability_by_id(data, "vectorDatabases", "qdrant")
    assert_execution_metadata(qdrant, CAPABILITY_STATUS_IMPLEMENTED, True)
    assert qdrant["adapter"]["id"] == "qdrant"


def test_component_capabilities_reports_tool_execution_metadata(
    app: FastAPI,
    logged_in_client: TestClient,
    monkeypatch,
) -> None:
    def fake_find_spec(name: str) -> object | None:
        return object() if name in {"docling", "pdfplumber"} else None

    monkeypatch.setattr(
        "app.services.component_registry.find_spec",
        fake_find_spec,
    )
    monkeypatch.setattr(
        "app.services.component_registry.shutil.which",
        lambda _name: None,
    )
    app.state.component_registry = ComponentRegistry(UnavailableOllamaService())

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert_execution_metadata(
        capability_by_id(data, "ocrEngines", "none"),
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )
    assert_execution_metadata(
        capability_by_id(data, "ocrEngines", "tesseract"),
        CAPABILITY_STATUS_UNAVAILABLE,
        False,
    )
    assert_execution_metadata(
        capability_by_id(data, "pdfParsers", "pdfplumber"),
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )
    assert_execution_metadata(
        capability_by_id(data, "pdfParsers", "docling"),
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )


def test_component_capabilities_marks_ocrmypdf_implemented_when_binary_exists(
    app: FastAPI,
    logged_in_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.component_registry.find_spec",
        lambda _name: None,
    )
    monkeypatch.setattr(
        "app.services.component_registry.shutil.which",
        lambda name: "ocrmypdf" if name == "ocrmypdf" else None,
    )
    app.state.component_registry = ComponentRegistry(UnavailableOllamaService())

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert_execution_metadata(
        capability_by_id(data, "ocrEngines", "ocrmypdf"),
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )


def test_component_capabilities_marks_paddleocr_implemented_when_packages_exist(
    app: FastAPI,
    logged_in_client: TestClient,
    monkeypatch,
) -> None:
    def fake_find_spec(name: str) -> object | None:
        return object() if name in {"paddleocr", "paddle"} else None

    monkeypatch.setattr(
        "app.services.component_registry.find_spec",
        fake_find_spec,
    )
    monkeypatch.setattr(
        "app.services.component_registry.shutil.which",
        lambda _name: None,
    )
    app.state.component_registry = ComponentRegistry(UnavailableOllamaService())

    response = logged_in_client.get("/components/capabilities")

    assert response.status_code == 200
    data = response.json()
    paddle = capability_by_id(data, "ocrEngines", "paddleocr")
    assert paddle["label"] == "PaddleOCR (Baidu)"
    assert_execution_metadata(
        paddle,
        CAPABILITY_STATUS_IMPLEMENTED,
        True,
    )


def test_component_capabilities_preserves_models_status_behavior(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.state.model_manager = FakeModelManager()

    response = logged_in_client.get("/models/status")

    assert response.status_code == 200
    assert response.json()["active_model"] == "qwen3:4b"
    assert response.json()["supported_models"][0]["name"] == "qwen3:4b"
