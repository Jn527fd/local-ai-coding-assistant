from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from app.rag.chunker import chunk_text

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}

SUPPORTED_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}


def _raise_walk_error(error: OSError) -> None:
    """Raise directory traversal errors instead of silently skipping them."""

    raise error


def iter_code_files(repository_path: Path) -> list[Path]:
    """Return supported code files while pruning ignored directories."""

    code_files: list[Path] = []

    for current_root, directory_names, file_names in os.walk(
        repository_path,
        onerror=_raise_walk_error,
    ):
        directory_names[:] = sorted(
            name for name in directory_names if name not in IGNORED_DIRECTORIES
        )

        root_path = Path(current_root)
        for file_name in sorted(file_names):
            file_path = root_path / file_name
            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                code_files.append(file_path)

    return code_files


def build_repository_index(
    repository_path: Path,
    chunk_size: int,
) -> dict[str, Any]:
    """Read supported files and build a JSON-serializable repository index."""

    indexed_files: list[str] = []
    chunks: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []

    for file_path in iter_code_files(repository_path):
        relative_path = file_path.relative_to(repository_path).as_posix()

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            skipped_files.append(
                {
                    "file_path": relative_path,
                    "reason": str(exc),
                }
            )
            continue

        indexed_files.append(relative_path)
        for chunk_number, chunk in enumerate(
            chunk_text(content, max_chars=chunk_size),
            start=1,
        ):
            chunks.append(
                {
                    "id": f"{relative_path}:{chunk_number}",
                    "file_path": relative_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                }
            )

    return {
        "version": 1,
        "repo_name": repository_path.name or "repository",
        "source_path": str(repository_path),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "files": indexed_files,
        "chunks": chunks,
        "skipped_files": skipped_files,
    }
