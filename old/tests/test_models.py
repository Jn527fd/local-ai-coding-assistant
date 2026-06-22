from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.local_settings_service import LocalSettingsService
from app.services.model_manager import ModelManager, UnsupportedModelError
from app.services.ollama_service import InstalledOllamaModel


def installed_model(
    name: str,
    parameter_size: str,
    parameters_billion: float | None,
    size_bytes: int = 2_500_000_000,
) -> InstalledOllamaModel:
    return InstalledOllamaModel(
        name=name,
        size_bytes=size_bytes,
        parameter_size=parameter_size,
        parameters_billion=parameters_billion,
        family=name.split(":", maxsplit=1)[0],
        quantization_level="Q4_K_M",
    )


class FakeModelOllamaService:
    def __init__(
        self,
        installed_models: list[InstalledOllamaModel] | None = None,
    ) -> None:
        self.installed_models = installed_models or []
        self.calls: list[str] = []

    async def list_installed_models(self) -> list[InstalledOllamaModel]:
        self.calls.append("list")
        return list(self.installed_models)


def make_manager(
    tmp_path: Path,
    ollama: FakeModelOllamaService,
) -> ModelManager:
    local_settings = LocalSettingsService(tmp_path / "app-settings.json")
    local_settings.set_active_model("qwen3:4b")
    return ModelManager(
        ollama_service=ollama,
        local_settings=local_settings,
        default_model="qwen3:4b",
        max_parameters_billion=7,
    )


def test_model_switch_rejects_models_above_seven_billion_parameters(
    app: FastAPI,
    logged_in_client: TestClient,
    tmp_path: Path,
) -> None:
    app.state.model_manager = make_manager(
        tmp_path,
        FakeModelOllamaService(
            [installed_model("qwen3:14b", "14.0B", 14.0)]
        ),
    )

    response = logged_in_client.post(
        "/models/switch",
        json={"model": "qwen3:14b"},
    )

    assert response.status_code == 400
    assert "Only models up to 7B" in response.json()["detail"]


@pytest.mark.anyio
async def test_model_status_builds_catalog_from_local_ollama_inventory(
    tmp_path: Path,
) -> None:
    ollama = FakeModelOllamaService(
        [
            installed_model("qwen3:4b", "4.0B", 4.0),
            installed_model("llama3.2:3b", "3.0B", 3.0),
            installed_model("qwen3:14b", "14.0B", 14.0),
            installed_model("unknown:latest", "", None),
        ]
    )
    manager = make_manager(tmp_path, ollama)

    status = await manager.status()

    assert [model["name"] for model in status["supported_models"]] == [
        "llama3.2:3b",
        "qwen3:4b",
    ]
    assert status["installed_models"] == [
        "qwen3:4b",
        "llama3.2:3b",
        "qwen3:14b",
        "unknown:latest",
    ]
    assert status["excluded_model_count"] == 2
    assert status["max_parameters_billion"] == 7


@pytest.mark.anyio
async def test_model_switch_reuses_installed_model_without_network_pull(
    tmp_path: Path,
) -> None:
    ollama = FakeModelOllamaService(
        [
            installed_model("qwen3:4b", "4.0B", 4.0),
            installed_model("llama3.2:3b", "3.0B", 3.0),
        ]
    )
    manager = make_manager(tmp_path, ollama)

    await manager.start_switch("llama3.2:3b")
    await manager.wait_for_switch()

    assert manager.active_model == "llama3.2:3b"
    assert ollama.calls == ["list"]
    status = await manager.status(refresh_installed=False)
    assert status["phase"] == "complete"
    assert status["progress"] == 100


@pytest.mark.anyio
async def test_model_switch_rejects_model_that_is_not_installed(
    tmp_path: Path,
) -> None:
    manager = make_manager(
        tmp_path,
        FakeModelOllamaService(
            [installed_model("qwen3:4b", "4.0B", 4.0)]
        ),
    )

    with pytest.raises(UnsupportedModelError, match="not installed locally"):
        await manager.start_switch("llama3.2:3b")
