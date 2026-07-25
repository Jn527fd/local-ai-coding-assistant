import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.chat import get_ollama_service


class FakeOllamaService:
    async def generate(
        self,
        model: str,
        prompt: str,
        images: list[str] | None = None,
    ) -> str:
        return "Session-authenticated response"

    async def list_installed_models(self) -> list[object]:
        return []


@pytest.mark.parametrize(
    ("headers", "expected_status", "expected_detail"),
    [
        ({}, 401, "Login required."),
        (
            {"Authorization": "Bearer invalid-key"},
            401,
            "Missing or invalid API key.",
        ),
    ],
)
def test_chat_rejects_unauthenticated_requests(
    client: TestClient,
    headers: dict[str, str],
    expected_status: int,
    expected_detail: str,
) -> None:
    response = client.post(
        "/chat",
        headers=headers,
        json={"model": "qwen3:4b", "message": "Hello"},
    )

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    if "Authorization" in headers:
        assert response.headers["www-authenticate"] == "Bearer"


def test_logged_in_session_can_chat_without_api_key(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.dependency_overrides[get_ollama_service] = lambda: FakeOllamaService()

    try:
        response = logged_in_client.post(
            "/chat",
            json={"model": "qwen3:4b", "message": "Hello"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"] == "Session-authenticated response"
