from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from threading import Lock
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.conversations import ConversationRecord

if TYPE_CHECKING:
    from app.metadata import MetadataStore

USERNAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class ConversationPersistenceError(Exception):
    """Base error for local conversation persistence."""


class ConversationStorageError(ConversationPersistenceError):
    """Raised when persisted conversation data cannot be read or written."""


class ConversationNotFoundError(ConversationPersistenceError):
    """Raised when a requested conversation does not exist."""


class ConversationPersistenceService:
    """Persist local conversations in small user-scoped JSON files."""

    def __init__(
        self,
        storage_directory: Path,
        max_conversations_per_user: int = 50,
        metadata_store: "MetadataStore | None" = None,
    ) -> None:
        self.storage_directory = storage_directory.expanduser().resolve()
        self.max_conversations_per_user = max(1, max_conversations_per_user)
        self.metadata_store = metadata_store
        self._lock = Lock()

    def list(self, username: str) -> list[ConversationRecord]:
        data = self._read(username)
        return self._records_from_data(data, username)

    def get(self, username: str, conversation_id: str) -> ConversationRecord:
        for conversation in self.list(username):
            if conversation.id == conversation_id:
                return conversation
        raise ConversationNotFoundError("Conversation was not found.")

    def upsert(
        self,
        username: str,
        conversation: ConversationRecord,
    ) -> ConversationRecord:
        now = self._now()
        normalized = self._normalize_record(conversation, now)
        with self._lock:
            data = self._read_locked(username)
            conversations = self._records_from_data(data, username)
            existing = {
                item.id: item
                for item in conversations
                if item.id != normalized.id
            }
            existing[normalized.id] = normalized
            next_conversations = sorted(
                existing.values(),
                key=lambda item: item.updatedAt or item.createdAt or "",
                reverse=True,
            )[: self.max_conversations_per_user]
            data["conversations"] = [
                item.model_dump(mode="json", exclude_none=True)
                for item in next_conversations
            ]
            deleted_ids = set(data.get("deletedConversationIds") or [])
            deleted_ids.discard(normalized.id)
            data["deletedConversationIds"] = sorted(deleted_ids)
            self._write_locked(username, data)
        self._mirror_conversation(username, normalized)
        return normalized

    def delete(self, username: str, conversation_id: str) -> None:
        with self._lock:
            data = self._read_locked(username)
            conversations = self._records_from_data(data, username)
            remaining = [
                item
                for item in conversations
                if item.id != conversation_id
            ]
            if len(remaining) == len(conversations):
                raise ConversationNotFoundError("Conversation was not found.")
            data["conversations"] = [
                item.model_dump(mode="json", exclude_none=True)
                for item in remaining
            ]
            deleted_ids = set(data.get("deletedConversationIds") or [])
            deleted_ids.add(conversation_id)
            data["deletedConversationIds"] = sorted(deleted_ids)
            self._write_locked(username, data)
        if self.metadata_store is not None:
            self.metadata_store.mark_conversation_deleted(
                username,
                conversation_id,
                self._user_file(username),
            )

    def import_conversations(
        self,
        username: str,
        conversations: list[ConversationRecord],
        replace: bool = False,
    ) -> list[ConversationRecord]:
        now = self._now()
        normalized_records = [
            self._normalize_record(conversation, now)
            for conversation in conversations
        ]
        with self._lock:
            data = self._empty_data(username) if replace else self._read_locked(username)
            existing = (
                {}
                if replace
                else {
                    item.id: item
                    for item in self._records_from_data(data, username)
                }
            )
            for conversation in normalized_records:
                existing[conversation.id] = conversation
            next_conversations = sorted(
                existing.values(),
                key=lambda item: item.updatedAt or item.createdAt or "",
                reverse=True,
            )[: self.max_conversations_per_user]
            data["conversations"] = [
                item.model_dump(mode="json", exclude_none=True)
                for item in next_conversations
            ]
            deleted_ids = set(data.get("deletedConversationIds") or [])
            for conversation in normalized_records:
                deleted_ids.discard(conversation.id)
            data["deletedConversationIds"] = sorted(deleted_ids)
            self._write_locked(username, data)
        self._mirror_conversations(username, next_conversations, replace=replace)
        return next_conversations

    def export_conversations(self, username: str) -> dict[str, Any]:
        return {
            "username": username,
            "exportedAt": self._now(),
            "conversations": [
                item.model_dump(mode="json", exclude_none=True)
                for item in self.list(username)
            ],
        }

    def _records_from_data(
        self,
        data: dict[str, Any],
        username: str,
    ) -> list[ConversationRecord]:
        raw_conversations = data.get("conversations", [])
        if not isinstance(raw_conversations, list):
            raise ConversationStorageError(
                f"Conversation store for {username!r} must contain a list."
            )
        records: list[ConversationRecord] = []
        try:
            for item in raw_conversations:
                records.append(ConversationRecord.model_validate(item))
        except ValidationError as exc:
            raise ConversationStorageError(
                f"Conversation store for {username!r} contains invalid records."
            ) from exc
        return records

    def _normalize_record(
        self,
        conversation: ConversationRecord,
        now: str,
    ) -> ConversationRecord:
        created_at = conversation.createdAt or conversation.updatedAt or now
        updated_at = conversation.updatedAt or now
        return conversation.model_copy(
            update={
                "title": conversation.title.strip() or "Untitled thread",
                "createdAt": created_at,
                "updatedAt": updated_at,
            }
        )

    def _read(self, username: str) -> dict[str, Any]:
        with self._lock:
            return self._read_locked(username)

    def _read_locked(self, username: str) -> dict[str, Any]:
        path = self._user_file(username)
        if not path.exists():
            return self._empty_data(username)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConversationStorageError(
                f"Unable to read conversation store: {path}"
            ) from exc
        if not isinstance(data, dict):
            raise ConversationStorageError(
                f"Conversation store must be a JSON object: {path}"
            )
        return data

    def _write_locked(self, username: str, data: dict[str, Any]) -> None:
        path = self._user_file(username)
        temporary_path: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data["version"] = 1
            data["username"] = username
            temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
            temporary_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(path)
            if os.name == "posix":
                path.chmod(0o600)
        except OSError as exc:
            raise ConversationStorageError(
                f"Unable to write conversation store: {path}"
            ) from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _mirror_conversation(
        self,
        username: str,
        conversation: ConversationRecord,
    ) -> None:
        if self.metadata_store is None:
            return
        self.metadata_store.upsert_conversation(
            username,
            conversation.model_dump(mode="json", exclude_none=True),
            self._user_file(username),
        )

    def _mirror_conversations(
        self,
        username: str,
        conversations: list[ConversationRecord],
        replace: bool,
    ) -> None:
        if self.metadata_store is None:
            return
        payloads = [
            conversation.model_dump(mode="json", exclude_none=True)
            for conversation in conversations
        ]
        if replace:
            self.metadata_store.replace_user_conversations(
                username,
                payloads,
                self._user_file(username),
            )
            return
        for payload in payloads:
            self.metadata_store.upsert_conversation(
                username,
                payload,
                self._user_file(username),
            )

    def _user_file(self, username: str) -> Path:
        safe_username = USERNAME_PATTERN.sub("_", username).strip("._-")
        if not safe_username:
            safe_username = "user"
        return self.storage_directory / f"{safe_username}.json"

    @staticmethod
    def _empty_data(username: str) -> dict[str, Any]:
        return {
            "version": 1,
            "username": username,
            "conversations": [],
            "deletedConversationIds": [],
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
