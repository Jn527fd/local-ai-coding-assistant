from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.redaction import REDACTED, redact_diagnostics


class FakeModelManager:
    async def status(self) -> dict[str, object]:
        return {
            "active_model": "qwen3:4b",
            "installed_models": ["qwen3:4b"],
            "supported_models": [{"name": "qwen3:4b"}],
            "ollama_connected": True,
            "phase": "idle",
            "warning": "",
            "error": "",
        }


def test_redacts_diagnostics_secrets_content_and_paths() -> None:
    payload = {
        "api_key": "secret-key",
        "Authorization": "Bearer secret",
        "csrfToken": "csrf",
        "session_cookie": "cookie",
        "prompt": "What is in my private doc?",
        "chatMessages": ["hello"],
        "documentText": "private document body",
        "ocrContent": "scanned text",
        "filePath": r"C:\Users\naran\private\doc.pdf",
        "nested": {
            "safeCount": 3,
            "error": r"Failed near C:\Users\naran\private\doc.pdf",
        },
    }

    redacted = redact_diagnostics(payload)

    assert redacted["api_key"] == REDACTED
    assert redacted["Authorization"] == REDACTED
    assert redacted["csrfToken"] == REDACTED
    assert redacted["session_cookie"] == REDACTED
    assert redacted["prompt"] == REDACTED
    assert redacted["chatMessages"] == REDACTED
    assert redacted["documentText"] == REDACTED
    assert redacted["ocrContent"] == REDACTED
    assert redacted["filePath"] == REDACTED
    assert redacted["nested"]["safeCount"] == 3
    assert redacted["nested"]["error"] == REDACTED


def test_diagnostics_status_returns_safe_structured_metadata(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    app.state.model_manager = FakeModelManager()
    app.state.diagnostics_service.model_manager = app.state.model_manager

    response = client.get("/diagnostics/status", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert set(data) >= {"runtime", "models", "documents", "retrieval", "jobs"}
    assert data["models"]["ollamaConnected"] is True
    assert data["models"]["installedModelCount"] == 1
    assert "api_key" not in str(data).lower()
    assert "test-password" not in str(data)
    assert "local_ai_session" not in str(data)


def test_support_bundle_is_metadata_only_and_redacted(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    app.state.model_manager = FakeModelManager()
    app.state.diagnostics_service.model_manager = app.state.model_manager

    response = client.get("/diagnostics/support-bundle", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["bundleVersion"] == 1
    assert data["redaction"] == {
        "mode": "metadata-only",
        "contentIncluded": False,
        "secretsIncluded": False,
        "privatePathsIncluded": False,
    }
    serialized = str(data).lower()
    assert "prompt" not in serialized
    assert "documenttext" not in serialized
    assert "cookie" not in serialized
    assert "csrf" not in serialized


def test_diagnostics_require_api_key(client: TestClient) -> None:
    response = client.get("/diagnostics/status")

    assert response.status_code == 401
