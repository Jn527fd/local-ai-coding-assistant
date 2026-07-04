from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator


class MetadataStoreError(Exception):
    """Base error for the local metadata database."""


class MetadataDatabaseError(MetadataStoreError):
    """Raised when the metadata database cannot be read or written."""


class MetadataIntegrityError(MetadataStoreError):
    """Raised when the metadata database is corrupt or incompatible."""


SCHEMA_V1_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        payload_json TEXT NOT NULL,
        migrated_from TEXT,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        source_path TEXT,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS conversations (
        username TEXT NOT NULL,
        id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT,
        updated_at TEXT,
        payload_json TEXT NOT NULL,
        deleted INTEGER NOT NULL DEFAULT 0,
        migrated_from TEXT,
        PRIMARY KEY (username, id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
    ON conversations (username, updated_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        original_filename TEXT,
        status TEXT,
        created_at TEXT,
        processed_at TEXT,
        artifact_path TEXT,
        payload_json TEXT NOT NULL,
        migrated_from TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_documents_conversation
    ON documents (conversation_id, created_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS vector_collections (
        collection_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        embedder_model TEXT,
        vector_database TEXT,
        source TEXT,
        artifact_path TEXT,
        payload_json TEXT NOT NULL,
        migrated_from TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_vector_collections_conversation
    ON vector_collections (conversation_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS repository_indexes (
        repo_name TEXT PRIMARY KEY,
        indexed_files INTEGER,
        indexed_chunks INTEGER,
        artifact_path TEXT,
        payload_json TEXT NOT NULL,
        migrated_from TEXT
    )
    """,
]

SCHEMA_V2_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        state TEXT NOT NULL,
        progress INTEGER NOT NULL DEFAULT 0,
        message TEXT,
        target_type TEXT,
        target_id TEXT,
        payload_json TEXT NOT NULL,
        result_json TEXT,
        error TEXT,
        cancel_requested INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_jobs_state_updated
    ON jobs (state, updated_at DESC)
    """,
]


class MetadataStore:
    """Small SQLite catalogue for local app metadata."""

    def __init__(self, database_file: Path) -> None:
        self.database_file = database_file.expanduser().resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_file.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(str(self.database_file))
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
        except sqlite3.Error as exc:
            raise MetadataDatabaseError(
                f"Unable to open metadata database: {self.database_file}"
            ) from exc

        try:
            yield connection
        finally:
            connection.close()

    def check_integrity(self) -> None:
        try:
            with self.connect() as connection:
                result = connection.execute("PRAGMA quick_check").fetchone()
        except sqlite3.DatabaseError as exc:
            raise MetadataIntegrityError(
                f"Metadata database is unreadable: {self.database_file}"
            ) from exc

        if result is None or result[0] != "ok":
            detail = result[0] if result is not None else "no result"
            raise MetadataIntegrityError(
                f"Metadata database integrity check failed: {detail}"
            )

    def schema_version(self) -> int:
        try:
            with self.connect() as connection:
                table = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name = 'schema_migrations'
                    """
                ).fetchone()
                if table is None:
                    return 0
                row = connection.execute(
                    "SELECT MAX(version) AS version FROM schema_migrations"
                ).fetchone()
        except sqlite3.DatabaseError as exc:
            raise MetadataDatabaseError(
                "Unable to read metadata schema version."
            ) from exc

        value = row["version"] if row is not None else None
        return int(value or 0)

    def apply_schema_v1(self, connection: sqlite3.Connection) -> None:
        for statement in SCHEMA_V1_STATEMENTS:
            connection.execute(statement)

    def apply_schema_v2(self, connection: sqlite3.Connection) -> None:
        for statement in SCHEMA_V2_STATEMENTS:
            connection.execute(statement)

    def record_migration(
        self,
        connection: sqlite3.Connection,
        version: int,
        name: str,
    ) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO schema_migrations
                (version, name, applied_at)
            VALUES (?, ?, ?)
            """,
            (version, name, self._now()),
        )

    def list_migrations(self) -> list[dict[str, Any]]:
        try:
            with self.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT version, name, applied_at
                    FROM schema_migrations
                    ORDER BY version
                    """
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise MetadataDatabaseError("Unable to list metadata migrations.") from exc
        return [dict(row) for row in rows]

    def upsert_user(
        self,
        connection: sqlite3.Connection,
        user: dict[str, Any],
        source_path: Path | None = None,
    ) -> None:
        username = user.get("username")
        if not isinstance(username, str) or not username:
            return
        password_hash = user.get("password_hash")
        connection.execute(
            """
            INSERT INTO users
                (username, password_hash, payload_json, migrated_from, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                payload_json = excluded.payload_json,
                migrated_from = excluded.migrated_from,
                updated_at = excluded.updated_at
            """,
            (
                username,
                password_hash if isinstance(password_hash, str) else None,
                self._json(user),
                str(source_path) if source_path is not None else None,
                self._now(),
            ),
        )

    def upsert_setting(
        self,
        connection: sqlite3.Connection,
        key: str,
        value: Any,
        source_path: Path | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO settings (key, value_json, source_path, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                source_path = excluded.source_path,
                updated_at = excluded.updated_at
            """,
            (
                key,
                self._json(value),
                str(source_path) if source_path is not None else None,
                self._now(),
            ),
        )

    def upsert_conversation(
        self,
        username: str,
        conversation: dict[str, Any],
        source_path: Path | None = None,
    ) -> None:
        with self.connect() as connection:
            with connection:
                self.upsert_conversation_in_transaction(
                    connection,
                    username,
                    conversation,
                    source_path,
                )

    def upsert_conversation_in_transaction(
        self,
        connection: sqlite3.Connection,
        username: str,
        conversation: dict[str, Any],
        source_path: Path | None = None,
    ) -> None:
        conversation_id = conversation.get("id")
        if not isinstance(conversation_id, str) or not conversation_id:
            return
        title = conversation.get("title")
        created_at = conversation.get("createdAt")
        updated_at = conversation.get("updatedAt")
        connection.execute(
            """
            INSERT INTO conversations
                (
                    username, id, title, created_at, updated_at, payload_json,
                    deleted, migrated_from
                )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(username, id) DO UPDATE SET
                title = excluded.title,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json,
                deleted = 0,
                migrated_from = excluded.migrated_from
            """,
            (
                username,
                conversation_id,
                title if isinstance(title, str) and title else "Untitled thread",
                created_at if isinstance(created_at, str) else None,
                updated_at if isinstance(updated_at, str) else None,
                self._json(conversation),
                str(source_path) if source_path is not None else None,
            ),
        )

    def replace_user_conversations(
        self,
        username: str,
        conversations: list[dict[str, Any]],
        source_path: Path | None = None,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    "DELETE FROM conversations WHERE username = ?",
                    (username,),
                )
                for conversation in conversations:
                    self.upsert_conversation_in_transaction(
                        connection,
                        username,
                        conversation,
                        source_path,
                    )

    def mark_conversation_deleted(
        self,
        username: str,
        conversation_id: str,
        source_path: Path | None = None,
    ) -> None:
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO conversations
                        (
                            username, id, title, created_at, updated_at,
                            payload_json, deleted, migrated_from
                        )
                    VALUES (?, ?, ?, NULL, ?, ?, 1, ?)
                    ON CONFLICT(username, id) DO UPDATE SET
                        updated_at = excluded.updated_at,
                        deleted = 1,
                        migrated_from = excluded.migrated_from
                    """,
                    (
                        username,
                        conversation_id,
                        "Deleted conversation",
                        self._now(),
                        "{}",
                        str(source_path) if source_path is not None else None,
                    ),
                )

    def upsert_document(
        self,
        connection: sqlite3.Connection,
        metadata: dict[str, Any],
        source_path: Path,
    ) -> None:
        document_id = metadata.get("documentId")
        conversation_id = metadata.get("conversationId")
        if not isinstance(document_id, str) or not isinstance(conversation_id, str):
            return
        connection.execute(
            """
            INSERT INTO documents
                (
                    document_id, conversation_id, original_filename, status,
                    created_at, processed_at, artifact_path, payload_json,
                    migrated_from
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                conversation_id = excluded.conversation_id,
                original_filename = excluded.original_filename,
                status = excluded.status,
                created_at = excluded.created_at,
                processed_at = excluded.processed_at,
                artifact_path = excluded.artifact_path,
                payload_json = excluded.payload_json,
                migrated_from = excluded.migrated_from
            """,
            (
                document_id,
                conversation_id,
                self._optional_text(metadata.get("originalFilename")),
                self._optional_text(metadata.get("status")),
                self._optional_text(metadata.get("createdAt")),
                self._optional_text(metadata.get("processedAt")),
                str(source_path),
                self._json(metadata),
                str(source_path),
            ),
        )

    def upsert_vector_collection(
        self,
        connection: sqlite3.Connection,
        metadata: dict[str, Any],
        source_path: Path,
    ) -> None:
        collection_id = metadata.get("collectionId")
        conversation_id = metadata.get("conversationId")
        if not isinstance(collection_id, str) or not isinstance(conversation_id, str):
            return
        connection.execute(
            """
            INSERT INTO vector_collections
                (
                    collection_id, conversation_id, embedder_model,
                    vector_database, source, artifact_path, payload_json,
                    migrated_from
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(collection_id) DO UPDATE SET
                conversation_id = excluded.conversation_id,
                embedder_model = excluded.embedder_model,
                vector_database = excluded.vector_database,
                source = excluded.source,
                artifact_path = excluded.artifact_path,
                payload_json = excluded.payload_json,
                migrated_from = excluded.migrated_from
            """,
            (
                collection_id,
                conversation_id,
                self._optional_text(metadata.get("embedderModel")),
                self._optional_text(metadata.get("vectorDatabase")),
                self._optional_text(metadata.get("source")),
                str(source_path),
                self._json(metadata),
                str(source_path),
            ),
        )

    def upsert_repository_index(
        self,
        connection: sqlite3.Connection,
        index_data: dict[str, Any],
        source_path: Path,
    ) -> None:
        repo_name = index_data.get("repo_name")
        if not isinstance(repo_name, str) or not repo_name:
            return
        files = index_data.get("files")
        chunks = index_data.get("chunks")
        connection.execute(
            """
            INSERT INTO repository_indexes
                (
                    repo_name, indexed_files, indexed_chunks, artifact_path,
                    payload_json, migrated_from
                )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_name) DO UPDATE SET
                indexed_files = excluded.indexed_files,
                indexed_chunks = excluded.indexed_chunks,
                artifact_path = excluded.artifact_path,
                payload_json = excluded.payload_json,
                migrated_from = excluded.migrated_from
            """,
            (
                repo_name,
                len(files) if isinstance(files, list) else None,
                len(chunks) if isinstance(chunks, list) else None,
                str(source_path),
                self._json(index_data),
                str(source_path),
            ),
        )

    def row_count(self, table: str) -> int:
        if table not in {
            "users",
            "settings",
            "conversations",
            "documents",
            "vector_collections",
            "repository_indexes",
            "schema_migrations",
            "jobs",
        }:
            raise MetadataDatabaseError("Unsupported metadata table.")
        with self.connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        return int(row["count"] if row is not None else 0)

    def upsert_job(self, job: dict[str, Any]) -> None:
        now = self._now()
        created_at = str(job.get("createdAt") or now)
        updated_at = str(job.get("updatedAt") or now)
        with self.connect() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO jobs
                        (
                            id, type, state, progress, message, target_type,
                            target_id, payload_json, result_json, error,
                            cancel_requested, created_at, updated_at,
                            started_at, finished_at
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        type = excluded.type,
                        state = excluded.state,
                        progress = excluded.progress,
                        message = excluded.message,
                        target_type = excluded.target_type,
                        target_id = excluded.target_id,
                        payload_json = excluded.payload_json,
                        result_json = excluded.result_json,
                        error = excluded.error,
                        cancel_requested = excluded.cancel_requested,
                        updated_at = excluded.updated_at,
                        started_at = excluded.started_at,
                        finished_at = excluded.finished_at
                    """,
                    (
                        str(job["id"]),
                        str(job["type"]),
                        str(job["state"]),
                        int(job.get("progress") or 0),
                        self._optional_text(job.get("message")),
                        self._optional_text(job.get("targetType")),
                        self._optional_text(job.get("targetId")),
                        self._json(job.get("payload") or {}),
                        (
                            self._json(job.get("result"))
                            if job.get("result") is not None
                            else None
                        ),
                        self._optional_text(job.get("error")),
                        1 if job.get("cancelRequested") else 0,
                        created_at,
                        updated_at,
                        self._optional_text(job.get("startedAt")),
                        self._optional_text(job.get("finishedAt")),
                    ),
                )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return self._job_from_row(row)

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM jobs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def _job_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["payload_json"] or "{}")
        result = json.loads(row["result_json"]) if row["result_json"] else None
        return {
            "id": row["id"],
            "type": row["type"],
            "state": row["state"],
            "progress": row["progress"],
            "message": row["message"],
            "targetType": row["target_type"],
            "targetId": row["target_id"],
            "payload": payload,
            "result": result,
            "error": row["error"],
            "cancelRequested": bool(row["cancel_requested"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "startedAt": row["started_at"],
            "finishedAt": row["finished_at"],
        }

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
