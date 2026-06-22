from fastapi import FastAPI
from fastapi.testclient import TestClient


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


def test_login_cookie_allows_account_and_model_requests(
    app: FastAPI,
    logged_in_client: TestClient,
) -> None:
    app.state.model_manager = FakeModelManager()

    account_response = logged_in_client.get("/account/status")
    model_response = logged_in_client.get("/models/status")

    assert account_response.status_code == 200
    assert account_response.json()["username"] == "test-user"
    assert model_response.status_code == 200
    assert model_response.json()["active_model"] == "qwen3:4b"
    assert model_response.json()["ollama_connected"] is True


def test_lan_browser_origin_is_allowed_by_cors(client: TestClient) -> None:
    origin = "http://192.168.1.204:5173"

    response = client.options(
        "/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
