from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from app.rag.code_parser import language_for_path, parse_source_chunks

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


def repository_file_metadata(
    repository_path: Path,
    file_path: Path,
    content: str,
) -> dict[str, Any]:
    """Return stable metadata used to detect stale repository indexes."""

    stat = file_path.stat()
    return {
        "file_path": file_path.relative_to(repository_path).as_posix(),
        "language": language_for_path(file_path),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def repository_fingerprint(files: list[dict[str, Any]]) -> str:
    """Return a deterministic fingerprint for indexed repository files."""

    payload = json.dumps(
        sorted(files, key=lambda item: str(item.get("file_path") or "")),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_repository_snapshot(repository_path: Path) -> dict[str, Any]:
    """Read supported files and return freshness metadata without chunks."""

    file_metadata: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []
    indexed_files: list[str] = []

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
        file_metadata.append(
            repository_file_metadata(
                repository_path=repository_path,
                file_path=file_path,
                content=content,
            )
        )

    return {
        "files": indexed_files,
        "file_metadata": file_metadata,
        "fingerprint": repository_fingerprint(file_metadata),
        "skipped_files": skipped_files,
    }


def build_repository_index(
    repository_path: Path,
    chunk_size: int,
) -> dict[str, Any]:
    """Read supported files and build a JSON-serializable repository index."""

    indexed_files: list[str] = []
    file_metadata: list[dict[str, Any]] = []
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
        file_metadata.append(
            repository_file_metadata(
                repository_path=repository_path,
                file_path=file_path,
                content=content,
            )
        )
        parsed_chunks = parse_source_chunks(
            file_path=file_path,
            content=content,
            max_chars=chunk_size,
        )
        for chunk_number, chunk in enumerate(parsed_chunks, start=1):
            metadata = dict(chunk.metadata)
            chunks.append(
                {
                    "id": f"{relative_path}:{chunk_number}",
                    "file_path": relative_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                    "language": metadata.get("language"),
                    "chunk_type": metadata.get("chunkType"),
                    "symbol_name": metadata.get("symbolName"),
                    "symbol_kind": metadata.get("symbolKind"),
                    "parser": metadata.get("parser"),
                    "fallback": metadata.get("fallback", False),
                    "fallback_reason": metadata.get("fallbackReason"),
                }
            )

    return {
        "version": 2,
        "repo_name": repository_path.name or "repository",
        "source_path": str(repository_path),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "files": indexed_files,
        "file_metadata": file_metadata,
        "fingerprint": repository_fingerprint(file_metadata),
        "chunks": chunks,
        "skipped_files": skipped_files,
    }
