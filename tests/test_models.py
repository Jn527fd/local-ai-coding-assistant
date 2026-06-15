from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.local_settings_service import LocalSettingsService
from app.services.model_manager import ModelManager


class FakeModelOllamaService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def list_installed_models(self) -> list[str]:
        return ["qwen3:4b"]

    async def unload_model(self, model: str) -> None:
        self.calls.append(("unload", model))

    async def pull_model(self, model, progress_callback, timeout) -> None:
        del timeout
        self.calls.append(("pull", model))
        progress_callback(100, "pull complete")

    async def delete_model(self, model: str) -> None:
        self.calls.append(("delete", model))


def test_model_switch_rejects_models_above_seven_billion_parameters(
    logged_in_client: TestClient,
) -> None:
    response = logged_in_client.post(
        "/models/switch",
        json={"model": "qwen3:14b"},
    )

    assert response.status_code == 400
    assert "7B parameters or fewer" in response.json()["detail"]


@pytest.mark.anyio
async def test_model_switch_activates_before_deleting_previous_model(
    tmp_path: Path,
) -> None:
    local_settings = LocalSettingsService(tmp_path / "app-settings.json")
    local_settings.set_active_model("qwen3:4b")
    ollama = FakeModelOllamaService()
    manager = ModelManager(
        ollama_service=ollama,
        local_settings=local_settings,
        default_model="qwen3:4b",
        pull_timeout_seconds=3600,
        delete_previous_model=True,
    )

    await manager.start_switch("llama3.2:3b")
    await manager.wait_for_switch()

    assert local_settings.get_active_model("qwen3:4b") == "llama3.2:3b"
    assert ollama.calls == [
        ("unload", "qwen3:4b"),
        ("pull", "llama3.2:3b"),
        ("delete", "qwen3:4b"),
    ]
    status = await manager.status(refresh_installed=False)
    assert status["phase"] == "complete"
    assert status["progress"] == 100
