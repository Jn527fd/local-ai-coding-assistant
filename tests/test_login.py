from fastapi.testclient import TestClient

from conftest import TEST_PASSWORD, TEST_USERNAME


def test_login_creates_local_session(client: TestClient) -> None:
    login_response = client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert login_response.status_code == 200
    assert login_response.json() == {"username": TEST_USERNAME}

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
