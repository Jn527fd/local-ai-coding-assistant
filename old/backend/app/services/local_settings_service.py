from hmac import compare_digest
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4


class LocalSettingsError(Exception):
    """Raised when local persisted settings cannot be read or written."""


class LocalSettingsService:
    """Persist mutable secrets and the active model outside source control."""

    def __init__(self, settings_file: Path) -> None:
        self.settings_file = settings_file
        self._lock = Lock()

    def get_api_key(self, fallback: str = "") -> str:
        value = self._read().get("api_key")
        return value if isinstance(value, str) and value else fallback

    def set_api_key(self, api_key: str) -> None:
        self._update("api_key", api_key)

    def api_key_matches(self, candidate: str, fallback: str = "") -> bool:
        expected = self.get_api_key(fallback=fallback)
        return bool(expected and candidate) and compare_digest(
            expected.encode("utf-8"),
            candidate.encode("utf-8"),
        )

    def get_active_model(self, fallback: str) -> str:
        value = self._read().get("active_model")
        return value if isinstance(value, str) and value else fallback

    def set_active_model(self, model: str) -> None:
        self._update("active_model", model)

    def _read(self) -> dict[str, Any]:
        with self._lock:
            return self._read_locked()

    def _read_locked(self) -> dict[str, Any]:
        if not self.settings_file.exists():
            return {}

        try:
            data: Any = json.loads(
                self.settings_file.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LocalSettingsError(
                f"Unable to read local settings: {self.settings_file}"
            ) from exc

        if not isinstance(data, dict):
            raise LocalSettingsError(
                "Local settings file must contain a JSON object."
            )
        return data

    def _update(self, key: str, value: str) -> None:
        with self._lock:
            data = self._read_locked()
            data[key] = value
            self._write_locked(data)

    def _write_locked(self, data: dict[str, Any]) -> None:
        temporary_path: Path | None = None
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.settings_file.with_name(
                f".{self.settings_file.name}.{uuid4().hex}.tmp"
            )
            temporary_path.write_text(
                json.dumps(data, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self.settings_file)
            if os.name == "posix":
                self.settings_file.chmod(0o600)
        except OSError as exc:
            raise LocalSettingsError(
                f"Unable to write local settings: {self.settings_file}"
            ) from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
