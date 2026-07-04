import logging

from fastapi.testclient import TestClient


def test_account_can_persist_and_verify_api_key(
    logged_in_client: TestClient,
) -> None:
    new_key = "short"

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


def test_api_key_update_audit_log_is_redacted(
    logged_in_client: TestClient,
    caplog,
) -> None:
    new_key = "secret-rotation-value"
    caplog.set_level(logging.INFO, logger="app.audit")

    response = logged_in_client.put(
        "/account/api-key",
        json={"api_key": new_key},
    )

    assert response.status_code == 200
    assert "api_key_updated" in caplog.text
    assert "test-user" in caplog.text
    assert new_key not in caplog.text
