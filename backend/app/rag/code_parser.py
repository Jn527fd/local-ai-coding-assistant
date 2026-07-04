from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from app.rag.chunker import TextChunk, chunk_text


LANGUAGE_BY_EXTENSION = {
    ".css": "css",
    ".html": "html",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "javascript",
    ".md": "markdown",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".yaml": "yaml",
    ".yml": "yaml",
}

SYMBOL_PATTERNS = {
    "javascript": re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\b|"
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="
    ),
    "typescript": re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\b|"
        r"^\s*(?:export\s+)?(?:class|interface|type)\s+([A-Za-z_$][\w$]*)\b|"
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="
    ),
    "css": re.compile(r"^\s*([^@{}\n][^{]+)\{"),
    "html": re.compile(r"^\s*<([A-Za-z][\w:-]*)(?:\s|>|/)"),
    "markdown": re.compile(r"^(#{1,6})\s+(.+?)\s*$"),
    "yaml": re.compile(r"^([A-Za-z0-9_.-]+):(?:\s|$)"),
}


@dataclass(frozen=True)
class ParsedCodeChunk:
    """Repository chunk with optional language and symbol metadata."""

    content: str
    start_line: int
    end_line: int
    metadata: dict[str, Any]


def language_for_path(file_path: Path) -> str:
    """Return the lightweight language id for a source path."""

    return LANGUAGE_BY_EXTENSION.get(file_path.suffix.lower(), "text")


def parse_source_chunks(
    file_path: Path,
    content: str,
    max_chars: int,
) -> list[ParsedCodeChunk]:
    """Return symbol-aware chunks, falling back to line chunking."""

    language = language_for_path(file_path)
    try:
        if language == "python":
            chunks = _parse_python(content, max_chars)
        elif language in {"javascript", "typescript", "css", "html", "markdown", "yaml"}:
            chunks = _parse_pattern_language(content, language, max_chars)
        elif language == "json":
            chunks = _parse_json(content, max_chars)
        else:
            chunks = []
    except Exception as exc:
        return _fallback_chunks(
            content=content,
            max_chars=max_chars,
            language=language,
            reason=f"parser failed: {exc.__class__.__name__}",
        )

    if not chunks:
        return _fallback_chunks(
            content=content,
            max_chars=max_chars,
            language=language,
            reason="no language-aware chunks found",
        )
    return [
        ParsedCodeChunk(
            content=chunk.content,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            metadata={
                "language": language,
                "chunkType": chunk.metadata.get("chunkType", "symbol"),
                "symbolName": chunk.metadata.get("symbolName"),
                "symbolKind": chunk.metadata.get("symbolKind"),
                "parser": chunk.metadata.get("parser", "lightweight"),
                "fallback": False,
            },
        )
        for chunk in chunks
    ]


def _parse_python(content: str, max_chars: int) -> list[TextChunk]:
    tree = ast.parse(content)
    lines = content.splitlines()
    chunks: list[TextChunk] = []
    for node in tree.body:
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            continue
        start_line = int(getattr(node, "lineno", 1))
        end_line = int(getattr(node, "end_lineno", start_line))
        symbol_kind = "class" if isinstance(node, ast.ClassDef) else "function"
        chunks.extend(
            _bounded_symbol_chunks(
                lines=lines,
                start_line=start_line,
                end_line=end_line,
                max_chars=max_chars,
                metadata={
                    "chunkType": "symbol",
                    "symbolName": node.name,
                    "symbolKind": symbol_kind,
                    "parser": "python-ast",
                },
            )
        )
    return chunks


def _parse_pattern_language(
    content: str,
    language: str,
    max_chars: int,
) -> list[TextChunk]:
    lines = content.splitlines()
    starts: list[tuple[int, str, str]] = []
    pattern = SYMBOL_PATTERNS[language]
    for line_number, line in enumerate(lines, start=1):
        match = pattern.search(line)
        if not match:
            continue
        groups = [group for group in match.groups() if group]
        if groups:
            symbol_name = (
                groups[-1] if language == "markdown" else groups[0]
            ).strip()
        else:
            symbol_name = line.strip()[:80]
        starts.append((line_number, symbol_name, _symbol_kind(language, line)))

    chunks: list[TextChunk] = []
    for index, (start_line, symbol_name, symbol_kind) in enumerate(starts):
        next_start = starts[index + 1][0] if index + 1 < len(starts) else len(lines) + 1
        end_line = max(start_line, next_start - 1)
        chunks.extend(
            _bounded_symbol_chunks(
                lines=lines,
                start_line=start_line,
                end_line=end_line,
                max_chars=max_chars,
                metadata={
                    "chunkType": "section" if language == "markdown" else "symbol",
                    "symbolName": symbol_name,
                    "symbolKind": symbol_kind,
                    "parser": f"{language}-patterns",
                },
            )
        )
    return chunks


def _parse_json(content: str, max_chars: int) -> list[TextChunk]:
    data = json.loads(content)
    lines = content.splitlines()
    chunks: list[TextChunk] = []
    if isinstance(data, dict):
        keys = [str(key) for key in data.keys()]
        for key in keys:
            line_number = _first_line_containing(lines, f'"{key}"') or 1
            chunks.extend(
                _bounded_symbol_chunks(
                    lines=lines,
                    start_line=line_number,
                    end_line=line_number,
                    max_chars=max_chars,
                    metadata={
                        "chunkType": "object-key",
                        "symbolName": key,
                        "symbolKind": "json-key",
                        "parser": "json-stdlib",
                    },
                )
            )
    return chunks


def _bounded_symbol_chunks(
    lines: list[str],
    start_line: int,
    end_line: int,
    max_chars: int,
    metadata: dict[str, Any],
) -> list[TextChunk]:
    text = "\n".join(lines[start_line - 1 : end_line])
    chunks = chunk_text(text, max_chars=max_chars)
    return [
        TextChunk(
            content=chunk.content,
            start_line=start_line + chunk.start_line - 1,
            end_line=start_line + chunk.end_line - 1,
            metadata=metadata,
        )
        for chunk in chunks
    ]


def _fallback_chunks(
    content: str,
    max_chars: int,
    language: str,
    reason: str,
) -> list[ParsedCodeChunk]:
    return [
        ParsedCodeChunk(
            content=chunk.content,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            metadata={
                "language": language,
                "chunkType": "line-range",
                "symbolName": None,
                "symbolKind": None,
                "parser": "line-fallback",
                "fallback": True,
                "fallbackReason": reason,
            },
        )
        for chunk in chunk_text(content, max_chars=max_chars)
    ]


def _first_line_containing(lines: list[str], needle: str) -> int | None:
    for line_number, line in enumerate(lines, start=1):
        if needle in line:
            return line_number
    return None


def _symbol_kind(language: str, line: str) -> str:
    stripped = line.strip()
    if language == "markdown":
        return "heading"
    if language == "css":
        return "selector"
    if language == "html":
        return "element"
    if language == "yaml":
        return "yaml-key"
    if "class " in stripped:
        return "class"
    if "interface " in stripped:
        return "interface"
    if "type " in stripped:
        return "type"
    if "function " in stripped:
        return "function"
    return "binding"
