from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.chat import get_ollama_service


class FakeOllamaService:
    """Small in-memory replacement for the real Ollama HTTP client."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, model: str, prompt: str) -> str:
        self.calls.append((model, prompt))
        return "Mocked local model response"


def test_chat_returns_mocked_ollama_answer(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "model": "qwen3:4b",
                "message": "Explain dependency injection briefly.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"answer": "Mocked local model response"}
    assert fake_ollama.calls == [
        ("qwen3:4b", "Explain dependency injection briefly.")
    ]
