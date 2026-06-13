from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

TEST_API_KEY = "phase-9-test-key"


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    """Create an isolated application for each test."""

    settings = Settings(
        api_key=TEST_API_KEY,
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
