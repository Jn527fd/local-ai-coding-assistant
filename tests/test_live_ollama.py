import os

import pytest

from app.services.ollama_service import OllamaService


pytestmark = [pytest.mark.ollama, pytest.mark.anyio]


async def test_live_ollama_lists_models_when_enabled() -> None:
    service = OllamaService(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        timeout_seconds=float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "5")),
        num_predict=64,
    )
    if not await service.is_available():
        pytest.skip("live Ollama daemon is not reachable")

    models = await service.list_installed_models()
    expected_model = os.environ.get("OLLAMA_TEST_MODEL")
    if expected_model:
        model_names = {model.name for model in models}
        if expected_model not in model_names:
            pytest.skip(f"required Ollama test model is not installed: {expected_model}")

    assert isinstance(models, list)
