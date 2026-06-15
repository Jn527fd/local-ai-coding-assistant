from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.auth.credentials import hash_password, write_credentials_file
from app.main import create_app

TEST_API_KEY = "phase-9-test-key"
TEST_USERNAME = "test-user"
TEST_PASSWORD = "test-password-123"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    """Create an isolated application for each test."""

    credentials_file = tmp_path / "config" / "credentials.json"
    local_settings_file = tmp_path / "config" / "app-settings.json"
    write_credentials_file(
        credentials_file,
        [
            {
                "username": TEST_USERNAME,
                "password_hash": TEST_PASSWORD_HASH,
            }
        ],
    )
    settings = Settings(
        api_key=TEST_API_KEY,
        credentials_file=credentials_file,
        local_settings_file=local_settings_file,
        data_directory=tmp_path,
        ollama_base_url="http://ollama.test",
    )
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """Run requests through the FastAPI application in memory."""

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return valid authentication headers for protected routes."""

    return {"Authorization": f"Bearer {TEST_API_KEY}"}


@pytest.fixture
def logged_in_client(client: TestClient) -> TestClient:
    response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
