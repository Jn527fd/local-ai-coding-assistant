from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from app.rag.indexer import build_repository_index


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

    def __init__(self, index_directory: Path, chunk_size: int) -> None:
        self.index_directory = index_directory
        self.chunk_size = chunk_size

    def index_local(self, repository_path: str) -> RepositoryIndexResult:
        """Index a local directory and persist its JSON representation."""

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

    @staticmethod
    def _safe_name(repo_name: str) -> str:
        """Convert a repository name into a safe index filename."""

        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", repo_name).strip(".-")
        return safe_name or "repository"
