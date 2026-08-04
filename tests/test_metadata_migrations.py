import json
from pathlib import Path
import sqlite3

import pytest

from app.auth.credentials import hash_password, write_credentials_file
from app.config import Settings
from app.metadata import (
    CURRENT_METADATA_SCHEMA_VERSION,
    MetadataMigrationError,
    MetadataMigrationManager,
    MetadataStore,
)
from app.schemas.conversations import ConversationRecord
from app.services.conversation_service import ConversationPersistenceService


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        api_key="test-key",
        credentials_file=tmp_path / "config" / "credentials.json",
        local_settings_file=tmp_path / "config" / "app-settings.json",
        data_directory=tmp_path,
        ollama_base_url="http://ollama.test",
    )


def _manager(settings: Settings) -> MetadataMigrationManager:
    return MetadataMigrationManager(
        MetadataStore(settings.resolved_metadata_database_file),
        settings,
    )


def _conversation(conversation_id: str = "chat-1") -> dict[str, object]:
    return {
        "id": conversation_id,
        "title": "Migrated chat",
        "messages": [{"role": "user", "content": "hello"}],
        "settings": {"llmModel": "qwen3:4b"},
        "metadata": {},
        "attachmentReferences": [],
        "createdAt": "2026-07-03T10:00:00Z",
        "updatedAt": "2026-07-03T10:01:00Z",
    }


def test_metadata_migration_initializes_fresh_database(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manager = _manager(settings)

    result = manager.migrate()

    assert result.previous_version == 0
    assert result.current_version == CURRENT_METADATA_SCHEMA_VERSION
    assert result.applied_versions == [1, 2]
    assert settings.resolved_metadata_database_file.exists()
    assert manager.status()["schemaVersion"] == CURRENT_METADATA_SCHEMA_VERSION


def test_empty_metadata_database_file_uses_default_path(tmp_path: Path) -> None:
    settings = Settings(
        api_key="test-key",
        data_directory=tmp_path,
        metadata_database_file="",
    )

    assert settings.resolved_metadata_database_file == (
        tmp_path / "metadata" / "app.sqlite3"
    ).resolve()


def test_metadata_migration_imports_existing_json_metadata(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_credentials_file(
        settings.resolved_credentials_file,
        [{"username": "test-user", "password_hash": hash_password("password-123")}],
    )
    settings.resolved_local_settings_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    settings.resolved_local_settings_file.write_text(
        json.dumps({"active_model": "llama3.2:3b", "api_key": "local-key"}),
        encoding="utf-8",
    )
    settings.conversation_directory.mkdir(parents=True)
    (settings.conversation_directory / "test-user.json").write_text(
        json.dumps(
            {
                "version": 1,
                "username": "test-user",
                "conversations": [_conversation("chat-1")],
                "deletedConversationIds": [],
            }
        ),
        encoding="utf-8",
    )
    document_metadata = {
        "documentId": "a" * 32,
        "conversationId": "chat-1",
        "originalFilename": "notes.txt",
        "status": "processed",
        "createdAt": "2026-07-03T10:02:00Z",
        "processedAt": "2026-07-03T10:03:00Z",
    }
    document_path = (
        settings.upload_directory / "chat-1" / ("a" * 32) / "metadata.json"
    )
    document_path.parent.mkdir(parents=True)
    document_path.write_text(json.dumps(document_metadata), encoding="utf-8")
    vector_metadata = {
        "collectionId": "json-123",
        "conversationId": "chat-1",
        "embedderModel": "all-minilm",
        "vectorDatabase": "qdrant",
        "source": "json",
    }
    vector_path = settings.vector_index_directory / "chat-1" / "json-123" / "metadata.json"
    vector_path.parent.mkdir(parents=True)
    vector_path.write_text(json.dumps(vector_metadata), encoding="utf-8")
    repo_index = {
        "repo_name": "local-ai-coding-assistant",
        "files": [{"path": "README.md"}],
        "chunks": [{"text": "hello"}],
    }
    settings.index_directory.mkdir(parents=True)
    (settings.index_directory / "local-ai-coding-assistant.json").write_text(
        json.dumps(repo_index),
        encoding="utf-8",
    )

    result = _manager(settings).migrate()
    store = MetadataStore(settings.resolved_metadata_database_file)

    assert result.imported_counts == {
        "users": 1,
        "settings": 2,
        "conversations": 1,
        "documents": 1,
        "vectorCollections": 1,
        "repositoryIndexes": 1,
    }
    assert store.row_count("users") == 1
    assert store.row_count("settings") == 2
    assert store.row_count("conversations") == 1
    assert store.row_count("documents") == 1
    assert store.row_count("vector_collections") == 1
    assert store.row_count("repository_indexes") == 1


def test_metadata_migration_reports_corrupt_database(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.resolved_metadata_database_file.parent.mkdir(parents=True)
    settings.resolved_metadata_database_file.write_text(
        "this is not sqlite",
        encoding="utf-8",
    )

    with pytest.raises(MetadataMigrationError):
        _manager(settings).migrate()


def test_failed_metadata_migration_does_not_record_schema_version(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    settings.conversation_directory.mkdir(parents=True)
    (settings.conversation_directory / "test-user.json").write_text(
        "{not json",
        encoding="utf-8",
    )
    store = MetadataStore(settings.resolved_metadata_database_file)

    with pytest.raises(MetadataMigrationError):
        _manager(settings).migrate()

    assert store.schema_version() == 0


def test_conversation_service_mirrors_json_writes_to_metadata_store(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _manager(settings).migrate()
    store = MetadataStore(settings.resolved_metadata_database_file)
    service = ConversationPersistenceService(
        settings.conversation_directory,
        metadata_store=store,
    )

    service.upsert(
        "test-user",
        ConversationRecord.model_validate(_conversation("chat-1")),
    )
    service.import_conversations(
        "test-user",
        [ConversationRecord.model_validate(_conversation("chat-2"))],
        replace=True,
    )
    service.delete("test-user", "chat-2")

    with sqlite3.connect(settings.resolved_metadata_database_file) as connection:
        rows = connection.execute(
            """
            SELECT id, deleted
            FROM conversations
            WHERE username = 'test-user'
            ORDER BY id
            """
        ).fetchall()

    assert rows == [("chat-2", 1)]
