"""Small deterministic Ollama-compatible server for local tests.

The fake intentionally implements only the endpoints this app calls. It avoids
logging prompt bodies so test output cannot leak document or chat content.
"""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


FAKE_MODELS = [
    {
        "name": "qwen3:4b",
        "model": "qwen3:4b",
        "size": 2_600_000_000,
        "modified_at": "2026-01-01T00:00:00Z",
        "details": {
            "family": "qwen3",
            "parameter_size": "4B",
            "quantization_level": "Q4_K_M",
        },
    },
    {
        "name": "llama-test:latest",
        "model": "llama-test:latest",
        "size": 1_500_000_000,
        "modified_at": "2026-01-02T00:00:00Z",
        "details": {
            "family": "llama",
            "parameter_size": "3B",
            "quantization_level": "Q4_K_M",
        },
    },
    {
        "name": "nomic-embed-text:latest",
        "model": "nomic-embed-text:latest",
        "size": 274_000_000,
        "modified_at": "2026-01-03T00:00:00Z",
        "details": {
            "family": "nomic-bert",
            "parameter_size": "137M",
            "quantization_level": "F16",
        },
    },
    {
        "name": "bge-reranker-v2-m3:latest",
        "model": "bge-reranker-v2-m3:latest",
        "size": 568_000_000,
        "modified_at": "2026-01-04T00:00:00Z",
        "details": {
            "family": "bge",
            "parameter_size": "568M",
            "quantization_level": "F16",
        },
    },
    {
        "name": "llava:7b",
        "model": "llava:7b",
        "size": 4_700_000_000,
        "modified_at": "2026-01-05T00:00:00Z",
        "details": {
            "family": "llava",
            "parameter_size": "7B",
            "quantization_level": "Q4_K_M",
        },
    },
]

WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in WORD_RE.finditer(text)}


def _extract_block(prompt: str, label: str) -> str:
    pattern = rf"{re.escape(label)}:\s*(.*?)(?:\n[A-Z][A-Za-z ]+:\s*|\Z)"
    match = re.search(pattern, prompt, flags=re.DOTALL)
    if match is None:
        return ""
    return match.group(1).strip()


def _score_prompt(prompt: str) -> str:
    query = _extract_block(prompt, "Query")
    passage = _extract_block(prompt, "Passage")
    query_terms = _tokenize(query)
    passage_terms = _tokenize(passage)
    if not query_terms or not passage_terms:
        return "0.05"
    overlap = len(query_terms & passage_terms) / max(1, len(query_terms))
    score = min(0.99, max(0.05, 0.1 + overlap * 0.85))
    return f"{score:.2f}"


def _embedding_for(text: str) -> list[float]:
    terms = _tokenize(text)
    text_lower = text.lower()
    dimensions = [
        "alpha",
        "banana",
        "carrot",
        "document",
        "python",
        "react",
        "settings",
        "vector",
    ]
    vector = [1.0 if term in terms else 0.0 for term in dimensions]
    vector.append(min(1.0, len(text) / 2000.0))
    vector.append(float(sum(ord(char) for char in text_lower) % 97) / 97.0)
    return vector


class FakeOllamaHandler(BaseHTTPRequestHandler):
    server_version = "FakeOllama/1.0"

    def do_GET(self) -> None:
        if self._offline():
            self._send_json({"error": "fake ollama is offline"}, status=503)
            return
        if self.path == "/api/tags":
            self._send_json({"models": FAKE_MODELS})
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        if self._offline():
            self._send_json({"error": "fake ollama is offline"}, status=503)
            return

        body = self._read_json_body()
        if self.path == "/api/generate":
            self._handle_generate(body)
            return
        if self.path == "/api/embed":
            self._handle_embed(body)
            return
        if self.path == "/api/embeddings":
            self._handle_embeddings(body)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _offline(self) -> bool:
        return os.environ.get("FAKE_OLLAMA_SCENARIO") == "offline"

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _handle_generate(self, body: dict[str, Any]) -> None:
        if os.environ.get("FAKE_OLLAMA_SCENARIO") == "generate-error":
            self._send_json({"error": "fake generation failure"}, status=500)
            return

        model = str(body.get("model") or "")
        prompt = str(body.get("prompt") or "")
        if "reranker" in model.lower() or "Score:" in prompt:
            response = _score_prompt(prompt)
        elif "Summarize" in prompt or "summary" in prompt.lower():
            response = "Summary: Earlier discussion condensed by fake Ollama."
        else:
            response = "Fake Ollama response from the deterministic test server."

        self._send_json(
            {
                "model": model,
                "created_at": "2026-01-01T00:00:00Z",
                "response": response,
                "done": True,
                "prompt_eval_count": max(1, len(prompt) // 4),
                "eval_count": max(1, len(response) // 4),
            }
        )

    def _handle_embed(self, body: dict[str, Any]) -> None:
        raw_input = body.get("input")
        texts = raw_input if isinstance(raw_input, list) else [raw_input]
        embeddings = [_embedding_for(str(item or "")) for item in texts]
        self._send_json({"model": body.get("model"), "embeddings": embeddings})

    def _handle_embeddings(self, body: dict[str, Any]) -> None:
        prompt = str(body.get("prompt") or "")
        self._send_json({"model": body.get("model"), "embedding": _embedding_for(prompt)})

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("FAKE_OLLAMA_HOST", "127.0.0.1")
    port = int(os.environ.get("FAKE_OLLAMA_PORT", "11435"))
    server = ThreadingHTTPServer((host, port), FakeOllamaHandler)
    print(f"Fake Ollama listening on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
