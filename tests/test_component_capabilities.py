from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.component_registry import CAPABILITY_KEYS, ComponentRegistry
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
    assert llm["name"] == "qwen3:4b"
    assert llm["size"] == 2_500_000_000
    assert llm["modifiedAt"] == "2026-06-27T00:00:00Z"
    assert llm["details"]["family"] == "qwen3"


def test_component_capabilities_preserves_models_status_behavior(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.state.model_manager = FakeModelManager()

    response = logged_in_client.get("/models/status")

    assert response.status_code == 200
    assert response.json()["active_model"] == "qwen3:4b"
    assert response.json()["supported_models"][0]["name"] == "qwen3:4b"
