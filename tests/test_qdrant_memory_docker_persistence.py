from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import time
from uuid import uuid4
from urllib.request import urlopen

import pytest

from app.ai.vectorstores.qdrant import QdrantVectorStore
from app.services.conversation_memory import ConversationMemoryService

from tests.test_conversation_memory import FakeMemoryEmbedder


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_compose_qdrant_volume_configuration_is_persistent() -> None:
    for compose_file in ("docker-compose.yml", "docker-compose.prod.yml"):
        text = (REPO_ROOT / compose_file).read_text(encoding="utf-8").replace(
            "\r\n",
            "\n",
        )

        assert "qdrant_storage:/qdrant/storage" in text
        assert "volumes:\n  qdrant_storage:" in text
        assert "VECTOR_STORE_BACKEND: qdrant" in text
        assert "QDRANT_URL: http://qdrant:6333" in text


@pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_MEMORY_TESTS") != "1",
    reason="set RUN_DOCKER_MEMORY_TESTS=1 to run Docker Qdrant persistence test",
)
@pytest.mark.asyncio
async def test_qdrant_memory_survives_compose_down_container_recreation(
    tmp_path: Path,
) -> None:
    port = _free_port()
    project = f"memory-persistence-{uuid4().hex[:10]}"
    compose_file = tmp_path / "compose.yml"
    compose_file.write_text(
        f"""
name: {project}
services:
  qdrant:
    image: qdrant/qdrant:v1.18.3
    ports:
      - "127.0.0.1:{port}:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
volumes:
  qdrant_storage:
""".strip(),
        encoding="utf-8",
    )
    base_command = ["docker", "compose", "-f", str(compose_file), "-p", project]
    qdrant_url = f"http://127.0.0.1:{port}"

    try:
        _run([*base_command, "up", "-d", "qdrant"])
        _wait_for_qdrant(qdrant_url)
        first_service = ConversationMemoryService(
            vector_store=QdrantVectorStore(tmp_path / "unused", url=qdrant_url),
            embedder_provider=FakeMemoryEmbedder(),
            collection_name="docker_memory_persistence_test",
            min_importance=0.2,
        )
        stored = await first_service.store(
            "workspace-a",
            "conversation-a",
            "Decision: docker compose down keeps the Qdrant memory volume.",
            "decision",
            0.9,
            "message-a",
            "user",
            "all-minilm",
        )
        assert len(stored.memories) == 1
        first_service.vector_store.close()

        _run([*base_command, "down"])
        _run([*base_command, "up", "-d", "qdrant"])
        _wait_for_qdrant(qdrant_url)

        second_service = ConversationMemoryService(
            vector_store=QdrantVectorStore(tmp_path / "unused-again", url=qdrant_url),
            embedder_provider=FakeMemoryEmbedder(),
            collection_name="docker_memory_persistence_test",
            min_importance=0.2,
        )
        listed = second_service.list("workspace-a", "conversation-a")

        assert len(listed.memories) == 1
        assert "compose down keeps" in listed.memories[0].text
    finally:
        _run([*base_command, "down", "-v"], check=False)


def _run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        text=True,
        capture_output=True,
        timeout=120,
    )


def _wait_for_qdrant(url: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{url}/collections", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise AssertionError("Qdrant did not become reachable in time.")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
