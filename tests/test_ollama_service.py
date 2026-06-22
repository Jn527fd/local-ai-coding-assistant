import json

import httpx
import pytest

from app.services import ollama_service as ollama_module
from app.services.ollama_service import (
    OllamaService,
    parse_parameter_size_billions,
)


@pytest.mark.anyio
async def test_generate_sends_runtime_limits(monkeypatch) -> None:
    request_body: dict[str, object] = {}

    async def handle_request(request: httpx.Request) -> httpx.Response:
        request_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "response": "Bounded response",
                "prompt_eval_count": 20,
                "eval_count": 10,
            },
        )

    transport = httpx.MockTransport(handle_request)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        ollama_module.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(transport=transport, **kwargs),
    )
    service = OllamaService(
        base_url="http://ollama.test",
        timeout_seconds=120,
        num_predict=512,
        think=False,
        keep_alive="15m",
    )

    answer = await service.generate("qwen3:4b", "Hello")

    assert answer == "Bounded response"
    assert request_body == {
        "model": "qwen3:4b",
        "prompt": "Hello",
        "stream": False,
        "think": False,
        "keep_alive": "15m",
        "options": {"num_predict": 512},
    }


@pytest.mark.anyio
async def test_list_installed_models_parses_ollama_metadata(
    monkeypatch,
) -> None:
    async def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "qwen3:4b",
                        "size": 2_500_000_000,
                        "details": {
                            "family": "qwen3",
                            "parameter_size": "4.0B",
                            "quantization_level": "Q4_K_M",
                        },
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handle_request)
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        ollama_module.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(transport=transport, **kwargs),
    )
    service = OllamaService("http://ollama.test", 120)

    models = await service.list_installed_models()

    assert len(models) == 1
    assert models[0].name == "qwen3:4b"
    assert models[0].parameters_billion == 4.0
    assert models[0].size_bytes == 2_500_000_000
    assert models[0].quantization_level == "Q4_K_M"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("7B", 7.0),
        ("3.2B", 3.2),
        ("500M", 0.5),
        ("1T", 1000.0),
        ("unknown", None),
    ],
)
def test_parse_parameter_size_billions(
    value: str,
    expected: float | None,
) -> None:
    assert parse_parameter_size_billions(value) == expected
