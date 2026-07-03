from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any

from app.config import Settings
from app.metadata.store import (
    MetadataDatabaseError,
    MetadataIntegrityError,
    MetadataStore,
)

logger = logging.getLogger(__name__)

CURRENT_METADATA_SCHEMA_VERSION = 1


class MetadataMigrationError(Exception):
    """Raised when local metadata migrations cannot complete safely."""


@dataclass(frozen=True)
class MetadataMigrationResult:
    database_file: Path
    previous_version: int
    current_version: int
    applied_versions: list[int] = field(default_factory=list)
    imported_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class MetadataMigrationManager:
    """Forward-only migration runner for the local metadata database."""

    def __init__(
        self,
        store: MetadataStore,
        settings: Settings,
    ) -> None:
        self.store = store
        self.settings = settings

    def migrate(self) -> MetadataMigrationResult:
        try:
            self.store.check_integrity()
            previous_version = self.store.schema_version()
        except (MetadataDatabaseError, MetadataIntegrityError) as exc:
            raise MetadataMigrationError(str(exc)) from exc

        if previous_version > CURRENT_METADATA_SCHEMA_VERSION:
            raise MetadataMigrationError(
                "Metadata database schema version "
                f"{previous_version} is newer than this application supports "
                f"({CURRENT_METADATA_SCHEMA_VERSION})."
            )

        if previous_version == CURRENT_METADATA_SCHEMA_VERSION:
            return MetadataMigrationResult(
                database_file=self.store.database_file,
                previous_version=previous_version,
                current_version=previous_version,
            )

        imported_counts: dict[str, int] = {}
        warnings: list[str] = []
        applied_versions: list[int] = []

        try:
            with self.store.connect() as connection:
                with connection:
                    if previous_version < 1:
                        self.store.apply_schema_v1(connection)
                        counts, migration_warnings = self._migrate_json_metadata(
                            connection
                        )
                        imported_counts.update(counts)
                        warnings.extend(migration_warnings)
                        self.store.record_migration(
                            connection,
                            1,
                            "initial_metadata_catalogue",
                        )
                        applied_versions.append(1)
        except (OSError, UnicodeError, sqlite3.DatabaseError) as exc:
            raise MetadataMigrationError(
                "Metadata migration failed before completion; existing JSON "
                "artifacts were left unchanged."
            ) from exc

        for warning in warnings:
            logger.warning("Metadata migration warning: %s", warning)

        return MetadataMigrationResult(
            database_file=self.store.database_file,
            previous_version=previous_version,
            current_version=CURRENT_METADATA_SCHEMA_VERSION,
            applied_versions=applied_versions,
            imported_counts=imported_counts,
            warnings=warnings,
        )

    def status(self) -> dict[str, Any]:
        try:
            self.store.check_integrity()
            version = self.store.schema_version()
        except (MetadataDatabaseError, MetadataIntegrityError) as exc:
            raise MetadataMigrationError(str(exc)) from exc
        return {
            "databaseFile": str(self.store.database_file),
            "schemaVersion": version,
            "currentSchemaVersion": CURRENT_METADATA_SCHEMA_VERSION,
            "migrations": self.store.list_migrations() if version else [],
        }

    def _migrate_json_metadata(
        self,
        connection: sqlite3.Connection,
    ) -> tuple[dict[str, int], list[str]]:
        counts = {
            "users": 0,
            "settings": 0,
            "conversations": 0,
            "documents": 0,
            "vectorCollections": 0,
            "repositoryIndexes": 0,
        }
        warnings: list[str] = []

        counts["users"] = self._import_credentials(connection)
        counts["settings"] = self._import_local_settings(connection)
        counts["conversations"] = self._import_conversations(connection)
        counts["documents"], document_warnings = self._import_documents(connection)
        warnings.extend(document_warnings)
        counts["vectorCollections"], vector_warnings = self._import_vector_metadata(
            connection
        )
        warnings.extend(vector_warnings)
        counts["repositoryIndexes"], repo_warnings = self._import_repository_indexes(
            connection
        )
        warnings.extend(repo_warnings)
        return counts, warnings

    def _import_credentials(self, connection: sqlite3.Connection) -> int:
        path = self.settings.resolved_credentials_file
        if not path.exists():
            return 0
        data = self._read_required_json_object(path, "credentials")
        users = data.get("users")
        if not isinstance(users, list):
            raise MetadataMigrationError(
                f"Credentials metadata must contain a users array: {path}"
            )
        count = 0
        for user in users:
            if isinstance(user, dict):
                self.store.upsert_user(connection, user, path)
                count += 1
        return count

    def _import_local_settings(self, connection: sqlite3.Connection) -> int:
        path = self.settings.resolved_local_settings_file
        if not path.exists():
            return 0
        data = self._read_required_json_object(path, "local settings")
        for key, value in data.items():
            self.store.upsert_setting(connection, str(key), value, path)
        return len(data)

    def _import_conversations(self, connection: sqlite3.Connection) -> int:
        directory = self.settings.conversation_directory
        if not directory.exists():
            return 0
        count = 0
        for path in sorted(directory.glob("*.json")):
            data = self._read_required_json_object(path, "conversation store")
            username = data.get("username")
            conversations = data.get("conversations")
            if not isinstance(username, str) or not isinstance(conversations, list):
                raise MetadataMigrationError(
                    f"Conversation metadata has an invalid shape: {path}"
                )
            for conversation in conversations:
                if not isinstance(conversation, dict):
                    raise MetadataMigrationError(
                        f"Conversation metadata contains a non-object record: {path}"
                    )
                self.store.upsert_conversation_in_transaction(
                    connection,
                    username,
                    conversation,
                    path,
                )
                count += 1
        return count

    def _import_documents(
        self,
        connection: sqlite3.Connection,
    ) -> tuple[int, list[str]]:
        directory = self.settings.upload_directory
        if not directory.exists():
            return 0, []
        count = 0
        warnings: list[str] = []
        for path in sorted(directory.glob("*/*/metadata.json")):
            data = self._read_optional_json_object(path, warnings)
            if data is None:
                continue
            self.store.upsert_document(connection, data, path)
            count += 1
        return count, warnings

    def _import_vector_metadata(
        self,
        connection: sqlite3.Connection,
    ) -> tuple[int, list[str]]:
        directory = self.settings.vector_index_directory
        if not directory.exists():
            return 0, []
        count = 0
        warnings: list[str] = []
        for path in sorted(directory.glob("*/*/metadata.json")):
            data = self._read_optional_json_object(path, warnings)
            if data is None:
                continue
            self.store.upsert_vector_collection(connection, data, path)
            count += 1
        return count, warnings

    def _import_repository_indexes(
        self,
        connection: sqlite3.Connection,
    ) -> tuple[int, list[str]]:
        directory = self.settings.index_directory
        if not directory.exists():
            return 0, []
        count = 0
        warnings: list[str] = []
        for path in sorted(directory.glob("*.json")):
            data = self._read_optional_json_object(path, warnings)
            if data is None:
                continue
            self.store.upsert_repository_index(connection, data, path)
            count += 1
        return count, warnings

    @staticmethod
    def _read_required_json_object(path: Path, label: str) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MetadataMigrationError(
                f"Unable to migrate {label} metadata from {path}."
            ) from exc
        if not isinstance(data, dict):
            raise MetadataMigrationError(
                f"Unable to migrate {label} metadata because it is not a JSON object: "
                f"{path}"
            )
        return data

    @staticmethod
    def _read_optional_json_object(
        path: Path,
        warnings: list[str],
    ) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            warnings.append(f"Skipped unreadable metadata artifact {path}: {exc}")
            return None
        if not isinstance(data, dict):
            warnings.append(f"Skipped non-object metadata artifact {path}.")
            return None
        return data
