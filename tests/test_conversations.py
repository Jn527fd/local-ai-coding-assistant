import json
from pathlib import Path

import pytest

from app.schemas.conversations import ConversationRecord
from app.services.conversation_service import (
    ConversationNotFoundError,
    ConversationPersistenceService,
    ConversationStorageError,
)


def _conversation(
    conversation_id: str = "chat-1",
    title: str = "First chat",
) -> dict[str, object]:
    return {
        "id": conversation_id,
        "title": title,
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "createdAt": "2026-07-03T10:00:00Z",
            }
        ],
        "settings": {
            "llmModel": "llama3.2:3b",
            "ragPipeline": "basic",
            "reranker": "none",
            "contextCompressor": "none",
        },
        "metadata": {"source": "test"},
        "attachmentReferences": [
            {"name": "diagram.png", "kind": "image"}
        ],
        "updatedAt": "2026-07-03T10:00:00Z",
    }


def test_conversation_service_round_trips_user_scoped_records(tmp_path: Path) -> None:
    service = ConversationPersistenceService(tmp_path / "conversations")
    record = ConversationRecord.model_validate(_conversation())

    saved = service.upsert("test-user", record)

    assert saved.id == "chat-1"
    assert service.list("test-user")[0].title == "First chat"
    assert service.list("other-user") == []
    assert service.get("test-user", "chat-1").messages[0]["content"] == "Hello"


def test_conversation_service_delete_removes_records(tmp_path: Path) -> None:
    service = ConversationPersistenceService(tmp_path / "conversations")
    service.upsert("test-user", ConversationRecord.model_validate(_conversation()))

    service.delete("test-user", "chat-1")

    assert service.list("test-user") == []
    with pytest.raises(ConversationNotFoundError):
        service.get("test-user", "chat-1")


def test_conversation_service_missing_store_is_empty(tmp_path: Path) -> None:
    service = ConversationPersistenceService(tmp_path / "conversations")

    assert service.list("missing-user") == []


def test_conversation_service_corrupt_store_raises(tmp_path: Path) -> None:
    storage = tmp_path / "conversations"
    storage.mkdir()
    (storage / "test-user.json").write_text("{not json", encoding="utf-8")
    service = ConversationPersistenceService(storage)

    with pytest.raises(ConversationStorageError):
        service.list("test-user")


def test_conversation_api_requires_login(client) -> None:
    response = client.get("/conversations")

    assert response.status_code == 401


def test_conversation_api_create_list_read_update_delete(logged_in_client) -> None:
    create_response = logged_in_client.post(
        "/conversations",
        json=_conversation(),
    )
    assert create_response.status_code == 201
    assert create_response.json()["conversation"]["id"] == "chat-1"

    list_response = logged_in_client.get("/conversations")
    assert list_response.status_code == 200
    assert list_response.json()["conversations"][0]["title"] == "First chat"

    read_response = logged_in_client.get("/conversations/chat-1")
    assert read_response.status_code == 200
    assert read_response.json()["conversation"]["messages"][0]["content"] == "Hello"

    updated = _conversation(title="Renamed chat")
    update_response = logged_in_client.put(
        "/conversations/chat-1",
        json=updated,
    )
    assert update_response.status_code == 200
    assert update_response.json()["conversation"]["title"] == "Renamed chat"

    delete_response = logged_in_client.delete("/conversations/chat-1")
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "deleted": True,
        "conversationId": "chat-1",
    }
    assert logged_in_client.get("/conversations/chat-1").status_code == 404
    assert logged_in_client.get("/conversations").json()["conversations"] == []


def test_conversation_api_rejects_mismatched_update_id(logged_in_client) -> None:
    response = logged_in_client.put(
        "/conversations/chat-2",
        json=_conversation("chat-1"),
    )

    assert response.status_code == 400


def test_conversation_api_import_and_export(logged_in_client) -> None:
    import_response = logged_in_client.post(
        "/conversations/import",
        json={"conversations": [_conversation("chat-1"), _conversation("chat-2")]},
    )
    assert import_response.status_code == 200
    assert import_response.json()["imported"] == 2

    export_response = logged_in_client.get("/conversations/export/all")
    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["username"] == "test-user"
    assert {item["id"] for item in payload["conversations"]} == {
        "chat-1",
        "chat-2",
    }


def test_conversation_api_reports_corrupt_store(logged_in_client, tmp_path: Path) -> None:
    store = tmp_path / "conversations" / "test-user.json"
    store.parent.mkdir(parents=True)
    store.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    response = logged_in_client.get("/conversations")

    assert response.status_code == 500
    assert "Conversation store" in response.json()["detail"]
