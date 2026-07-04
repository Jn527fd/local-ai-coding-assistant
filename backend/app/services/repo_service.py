from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from app.rag.indexer import build_repository_index, build_repository_snapshot


class RepositoryServiceError(Exception):
    """Base error raised by repository indexing."""


class InvalidRepositoryPathError(RepositoryServiceError):
    """Raised when the requested repository path cannot be indexed."""


class RepositoryAccessError(RepositoryServiceError):
    """Raised when the repository directory cannot be traversed."""


class RepositoryIndexWriteError(RepositoryServiceError):
    """Raised when the generated JSON index cannot be saved."""


class RepositoryIndexNotFoundError(RepositoryServiceError):
    """Raised when a requested repository has not been indexed."""


class RepositoryIndexReadError(RepositoryServiceError):
    """Raised when a repository index cannot be read or is malformed."""


@dataclass(frozen=True)
class RepositoryIndexResult:
    """Summary of a completed repository indexing operation."""

    repo_name: str
    indexed_files: int
    indexed_chunks: int
    index_path: Path


class RepositoryService:
    """Index local source repositories into JSON files."""

    def __init__(
        self,
        index_directory: Path,
        chunk_size: int,
        allowed_roots: list[Path] | None = None,
        metadata_store: Any | None = None,
    ) -> None:
        self.index_directory = index_directory
        self.chunk_size = chunk_size
        self.allowed_roots = [
            root.expanduser().resolve() for root in (allowed_roots or [])
        ]
        self.metadata_store = metadata_store

    def index_local(self, repository_path: str) -> RepositoryIndexResult:
        """Index a local directory and persist its JSON representation."""

        resolved_path = self.resolve_repository_path(repository_path)

        try:
            index_data = build_repository_index(
                repository_path=resolved_path,
                chunk_size=self.chunk_size,
            )
        except OSError as exc:
            raise RepositoryAccessError(
                f"Unable to read repository directory: {resolved_path}"
            ) from exc
        repo_name = str(index_data["repo_name"])
        index_path = self.index_directory / f"{self._safe_name(repo_name)}.json"
        self._write_index(index_path, index_data)
        self._write_metadata(index_data, index_path)

        return RepositoryIndexResult(
            repo_name=repo_name,
            indexed_files=len(index_data["files"]),
            indexed_chunks=len(index_data["chunks"]),
            index_path=index_path,
        )

    def load_index(self, repo_name: str) -> dict[str, Any]:
        """Load and validate a repository's persisted JSON index."""

        index_path = self.index_path_for(repo_name)
        if not index_path.is_file():
            raise RepositoryIndexNotFoundError(
                f"Repository index not found for '{repo_name}'. "
                "Index the repository before asking questions."
            )

        try:
            index_data: Any = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RepositoryIndexReadError(
                f"Unable to read repository index: {index_path}"
            ) from exc

        if (
            not isinstance(index_data, dict)
            or not isinstance(index_data.get("repo_name"), str)
            or not isinstance(index_data.get("chunks"), list)
        ):
            raise RepositoryIndexReadError(
                f"Repository index has an invalid format: {index_path}"
            )

        return index_data

    def resolve_repository_path(self, repository_path: str) -> Path:
        """Resolve and validate a local repository path."""

        try:
            resolved_path = Path(repository_path).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise InvalidRepositoryPathError(
                f"Repository path does not exist or cannot be resolved: "
                f"{repository_path}"
            ) from exc

        if not resolved_path.is_dir():
            raise InvalidRepositoryPathError(
                f"Repository path is not a directory: {resolved_path}"
            )
        if self.allowed_roots and not any(
            self._is_relative_to(resolved_path, root) for root in self.allowed_roots
        ):
            roots = ", ".join(str(root) for root in self.allowed_roots)
            raise RepositoryAccessError(
                f"Repository path must be inside an allowed root: {roots}"
            )
        return resolved_path

    def freshness(self, index_data: dict[str, Any]) -> dict[str, Any]:
        """Compare a saved repository index to the current filesystem state."""

        source_path = index_data.get("source_path")
        indexed_fingerprint = index_data.get("fingerprint")
        if not isinstance(source_path, str) or not source_path:
            return {
                "fresh": False,
                "warnings": ["Repository index has no source path metadata."],
            }
        if not isinstance(indexed_fingerprint, str) or not indexed_fingerprint:
            return {
                "fresh": False,
                "warnings": [
                    "Repository index has no freshness fingerprint; re-index it."
                ],
            }

        try:
            resolved_path = self.resolve_repository_path(source_path)
            snapshot = build_repository_snapshot(resolved_path)
        except RepositoryServiceError as exc:
            return {"fresh": False, "warnings": [str(exc)]}
        except OSError as exc:
            return {
                "fresh": False,
                "warnings": [f"Unable to inspect repository freshness: {exc}"],
            }

        current_fingerprint = snapshot["fingerprint"]
        fresh = indexed_fingerprint == current_fingerprint
        warnings = []
        if not fresh:
            warnings.append(
                "Repository index is stale; re-index before relying on answers."
            )
        return {
            "fresh": fresh,
            "warnings": warnings,
            "indexedFingerprint": indexed_fingerprint,
            "currentFingerprint": current_fingerprint,
            "indexedFileCount": len(index_data.get("files") or []),
            "currentFileCount": len(snapshot.get("files") or []),
        }

    def index_path_for(self, repo_name: str) -> Path:
        """Return the index path for a repository name."""

        return self.index_directory / f"{self._safe_name(repo_name)}.json"

    def _write_index(self, index_path: Path, index_data: dict[str, object]) -> None:
        """Write an index atomically to avoid leaving partial JSON files."""

        temporary_path: Path | None = None

        try:
            self.index_directory.mkdir(parents=True, exist_ok=True)
            temporary_path = index_path.with_name(
                f".{index_path.name}.{uuid4().hex}.tmp"
            )
            temporary_path.write_text(
                json.dumps(index_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(index_path)
        except OSError as exc:
            raise RepositoryIndexWriteError(
                f"Unable to write repository index to {index_path}."
            ) from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def _write_metadata(self, index_data: dict[str, Any], index_path: Path) -> None:
        if self.metadata_store is None:
            return
        try:
            with self.metadata_store.connect() as connection:
                with connection:
                    self.metadata_store.upsert_repository_index(
                        connection,
                        index_data,
                        index_path,
                    )
        except Exception:
            return

    @staticmethod
    def _safe_name(repo_name: str) -> str:
        """Convert a repository name into a safe index filename."""

        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", repo_name).strip(".-")
        return safe_name or "repository"

    @staticmethod
    def _is_relative_to(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
