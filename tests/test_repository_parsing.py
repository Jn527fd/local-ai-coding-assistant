from pathlib import Path

from app.rag.code_parser import parse_source_chunks
from app.rag.indexer import build_repository_index
from app.rag.retriever import build_rag_prompt, retrieve_relevant_chunks


def chunk_by_symbol(index_data: dict[str, object], symbol: str) -> dict[str, object]:
    chunks = index_data["chunks"]
    assert isinstance(chunks, list)
    for chunk in chunks:
        assert isinstance(chunk, dict)
        if chunk.get("symbol_name") == symbol:
            return chunk
    raise AssertionError(f"Missing chunk for symbol {symbol!r}")


def write_fixture_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "language-fixtures"
    repo_path.mkdir()
    (repo_path / "service.py").write_text(
        "import os\n\n"
        "class BananaService:\n"
        "    def route(self):\n"
        "        return 'banana'\n\n"
        "def carrot_helper():\n"
        "    return 'carrot'\n",
        encoding="utf-8",
    )
    (repo_path / "app.ts").write_text(
        "export function createRouter() {\n"
        "  return 'router';\n"
        "}\n\n"
        "export const bananaHandler = () => 'banana';\n",
        encoding="utf-8",
    )
    (repo_path / "component.jsx").write_text(
        "export function Widget() {\n"
        "  return <div>Widget</div>;\n"
        "}\n",
        encoding="utf-8",
    )
    (repo_path / "README.md").write_text(
        "# Overview\n\nIntro text.\n\n## Install\n\nRun setup.\n",
        encoding="utf-8",
    )
    (repo_path / "config.json").write_text(
        '{\n  "server": {"port": 8000},\n  "features": ["rag"]\n}\n',
        encoding="utf-8",
    )
    (repo_path / "pipeline.yaml").write_text(
        "ingest:\n  parser: lightweight\nsearch:\n  top_k: 5\n",
        encoding="utf-8",
    )
    (repo_path / "index.html").write_text(
        "<main>\n  <section>Content</section>\n</main>\n",
        encoding="utf-8",
    )
    (repo_path / "style.css").write_text(
        ".hero {\n  color: red;\n}\n\n#panel {\n  display: grid;\n}\n",
        encoding="utf-8",
    )
    return repo_path


def test_repository_index_adds_symbol_metadata_for_common_languages(
    tmp_path: Path,
) -> None:
    index_data = build_repository_index(write_fixture_repo(tmp_path), chunk_size=400)

    python_chunk = chunk_by_symbol(index_data, "BananaService")
    ts_chunk = chunk_by_symbol(index_data, "createRouter")
    jsx_chunk = chunk_by_symbol(index_data, "Widget")
    md_chunk = chunk_by_symbol(index_data, "Install")
    json_chunk = chunk_by_symbol(index_data, "server")
    yaml_chunk = chunk_by_symbol(index_data, "ingest")
    html_chunk = chunk_by_symbol(index_data, "main")
    css_chunk = chunk_by_symbol(index_data, ".hero")

    assert index_data["version"] == 2
    assert python_chunk["language"] == "python"
    assert python_chunk["symbol_kind"] == "class"
    assert python_chunk["start_line"] == 3
    assert python_chunk["end_line"] == 5
    assert ts_chunk["language"] == "typescript"
    assert jsx_chunk["language"] == "javascript"
    assert md_chunk["chunk_type"] == "section"
    assert json_chunk["symbol_kind"] == "json-key"
    assert yaml_chunk["symbol_kind"] == "yaml-key"
    assert html_chunk["symbol_kind"] == "element"
    assert css_chunk["symbol_kind"] == "selector"


def test_parser_failures_fall_back_to_line_chunks() -> None:
    chunks = parse_source_chunks(
        file_path=Path("broken.py"),
        content="def not_valid(:\n    pass\n",
        max_chars=200,
    )

    assert len(chunks) == 1
    assert chunks[0].metadata["language"] == "python"
    assert chunks[0].metadata["parser"] == "line-fallback"
    assert chunks[0].metadata["fallback"] is True
    assert "parser failed" in str(chunks[0].metadata["fallbackReason"])


def test_unknown_symbol_files_fall_back_safely() -> None:
    chunks = parse_source_chunks(
        file_path=Path("notes.css"),
        content="/* no selector here */\n",
        max_chars=200,
    )

    assert chunks[0].metadata["language"] == "css"
    assert chunks[0].metadata["chunkType"] == "line-range"
    assert chunks[0].metadata["fallback"] is True


def test_repository_prompt_surfaces_symbol_context(tmp_path: Path) -> None:
    index_data = build_repository_index(write_fixture_repo(tmp_path), chunk_size=400)
    chunks = retrieve_relevant_chunks(index_data, "banana service", limit=1)

    prompt = build_rag_prompt("language-fixtures", "banana service", chunks)

    assert "language: python" in prompt
    assert "class: BananaService" in prompt
    assert "lines 3-5" in prompt


def test_existing_version_one_indexes_remain_retrievable() -> None:
    index_data = {
        "version": 1,
        "repo_name": "old",
        "chunks": [
            {
                "id": "old.py:1",
                "file_path": "old.py",
                "start_line": 1,
                "end_line": 2,
                "content": "def legacy():\n    return 'banana'",
            }
        ],
    }

    chunks = retrieve_relevant_chunks(index_data, "legacy banana", limit=1)
    prompt = build_rag_prompt("old", "legacy banana", chunks)

    assert chunks[0].file_path == "old.py"
    assert "old.py, lines 1-2" in prompt
