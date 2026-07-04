import logging
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth.credentials import write_credentials_file
from app.config import Settings
from app.main import create_app
from conftest import TEST_PASSWORD, TEST_PASSWORD_HASH, TEST_USERNAME


def test_login_creates_local_session(client: TestClient) -> None:
    login_response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert login_response.status_code == 200
    assert login_response.json() == {"username": TEST_USERNAME}
    assert login_response.cookies.get("local_ai_session")
    assert login_response.cookies.get("local_ai_csrf")
    assert "HttpOnly" in login_response.headers["set-cookie"]
    assert "SameSite=lax" in login_response.headers["set-cookie"]

    session_response = client.get("/auth/me")
    assert session_response.status_code == 200
    assert session_response.json() == {"username": TEST_USERNAME}


def test_login_rejects_invalid_password(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password."}


def test_login_rate_limit_blocks_repeated_failures(client: TestClient) -> None:
    for _ in range(4):
        response = client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": "wrong-password"},
    )
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many login attempts. Try again later."}

    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 429


def test_cookie_session_routes_require_csrf_for_unsafe_methods(
    client: TestClient,
) -> None:
    login_response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert login_response.status_code == 200

    blocked_response = client.put(
        "/account/api-key",
        json={"api_key": "rotated-test-key"},
    )
    assert blocked_response.status_code == 403
    assert blocked_response.json() == {"detail": "CSRF token missing or invalid."}

    allowed_response = client.put(
        "/account/api-key",
        headers={"X-CSRF-Token": client.cookies.get("local_ai_csrf")},
        json={"api_key": "rotated-test-key"},
    )
    assert allowed_response.status_code == 200


def test_security_headers_are_added(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "microphone=()" in response.headers["permissions-policy"]


def test_signed_session_survives_app_restart(tmp_path: Path) -> None:
    credentials_file = tmp_path / "config" / "credentials.json"
    local_settings_file = tmp_path / "config" / "app-settings.json"
    write_credentials_file(
        credentials_file,
        [{"username": TEST_USERNAME, "password_hash": TEST_PASSWORD_HASH}],
    )
    settings = Settings(
        api_key="test-key",
        credentials_file=credentials_file,
        local_settings_file=local_settings_file,
        data_directory=tmp_path,
        ollama_base_url="http://ollama.test",
        session_signing_key="stable-local-signing-key",
    )

    with TestClient(create_app(settings)) as first_client:
        login_response = first_client.post(
            "/auth/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        )
        assert login_response.status_code == 200
        session_cookie = first_client.cookies.get("local_ai_session")

    with TestClient(create_app(settings)) as second_client:
        second_client.cookies.set("local_ai_session", session_cookie)
        response = second_client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {"username": TEST_USERNAME}


def test_auth_audit_logs_do_not_include_password(
    client: TestClient,
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="app.audit")

    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    audit_text = caplog.text
    assert "login_succeeded" in audit_text
    assert TEST_USERNAME in audit_text
    assert TEST_PASSWORD not in audit_text
