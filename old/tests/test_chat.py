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
    assert response.json() == {
        "model": "qwen3:4b",
        "answer": "Mocked local model response",
    }
    assert fake_ollama.calls == [
        ("qwen3:4b", "Explain dependency injection briefly.")
    ]


def test_chat_sends_only_explicit_history_as_context(
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
                "message": "And how is it declared?",
                "history": [
                    {
                        "role": "user",
                        "content": "What is a FastAPI dependency?",
                    },
                    {
                        "role": "assistant",
                        "content": "It provides reusable request-time values.",
                    },
                ],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = fake_ollama.calls[0][1]
    assert "User: What is a FastAPI dependency?" in prompt
    assert "Assistant: It provides reusable request-time values." in prompt
    assert "User: And how is it declared?" in prompt


def test_chat_bounds_large_history_to_recent_context(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    fake_ollama = FakeOllamaService()
    app.dependency_overrides[get_ollama_service] = lambda: fake_ollama
    history = [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index} " + ("x" * 2_000),
        }
        for index in range(12)
    ]

    try:
        response = client.post(
            "/chat",
            headers=auth_headers,
            json={
                "message": "Use the most recent context.",
                "history": history,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    prompt = fake_ollama.calls[0][1]
    assert len(prompt) <= app.state.settings.chat_context_max_chars
    assert "message-11" in prompt
    assert "message-0" not in prompt
