import json
import threading
import urllib.request
from collections.abc import Iterator
from http.server import ThreadingHTTPServer

import pytest

from tests.fakes.fake_ollama import FakeOllamaHandler


@pytest.fixture
def fake_ollama_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllamaHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.mark.unit
def test_fake_ollama_supports_app_endpoints(fake_ollama_url: str) -> None:
    with urllib.request.urlopen(f"{fake_ollama_url}/api/tags", timeout=5) as response:
        tags = json.loads(response.read().decode("utf-8"))

    generation = post_json(
        f"{fake_ollama_url}/api/generate",
        {"model": "llama-test:latest", "prompt": "hello"},
    )
    rerank = post_json(
        f"{fake_ollama_url}/api/generate",
        {
            "model": "bge-reranker-v2-m3:latest",
            "prompt": "Query:\nalpha\n\nPassage:\nalpha beta\n\nScore:",
        },
    )
    embeddings = post_json(
        f"{fake_ollama_url}/api/embed",
        {"model": "nomic-embed-text:latest", "input": ["alpha", "banana"]},
    )

    assert tags["models"][0]["name"] == "qwen3:4b"
    assert "Fake Ollama response" in generation["response"]
    assert float(str(rerank["response"])) > 0
    assert len(embeddings["embeddings"]) == 2
