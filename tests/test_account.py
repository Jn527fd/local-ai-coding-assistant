from fastapi.testclient import TestClient


def test_account_can_persist_and_verify_api_key(
    logged_in_client: TestClient,
) -> None:
    new_key = "new-local-api-key-1234567890"

    update_response = logged_in_client.put(
        "/account/api-key",
        json={"api_key": new_key},
    )
    assert update_response.status_code == 200
    assert update_response.json()["api_key_active"] is True

    status_response = logged_in_client.get(
        "/account/status",
        headers={"Authorization": f"Bearer {new_key}"},
    )
    assert status_response.status_code == 200
    assert status_response.json() == {
        "username": "test-user",
        "api_key_configured": True,
        "api_key_active": True,
    }
