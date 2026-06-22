import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer invalid-key"},
    ],
)
def test_chat_rejects_missing_or_invalid_api_key(
    client: TestClient,
    headers: dict[str, str],
) -> None:
    response = client.post(
        "/chat",
        headers=headers,
        json={"model": "qwen3:4b", "message": "Hello"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid API key."}
    assert response.headers["www-authenticate"] == "Bearer"
