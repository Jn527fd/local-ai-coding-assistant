from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_LLM = "smollm2:135m"
DEFAULT_EMBEDDER = "all-minilm"
DEFAULT_RERANKER = "qllama/bge-reranker-v2-m3:q4_k_m"


def main() -> int:
    ollama_path = shutil.which("ollama")
    if ollama_path is None:
        print("Ollama is not installed or is not on PATH.")
        print("")
        print("Install Ollama, then rerun this command:")
        print("  https://ollama.com/download")
        print("")
        print("After installing, start the daemon with:")
        print("  ollama serve")
        return 1

    base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    if not ollama_reachable(base_url):
        print(f"Ollama CLI found at: {ollama_path}")
        print(f"Ollama daemon is not reachable at {base_url}.")
        print("")
        print("Start Ollama, then rerun this command:")
        print("  ollama serve")
        print("")
        print("If your daemon uses another host, set OLLAMA_BASE_URL first.")
        return 1

    llm = os.environ.get("OLLAMA_TEST_LLM", DEFAULT_LLM)
    embedder = os.environ.get("OLLAMA_TEST_EMBEDDER", DEFAULT_EMBEDDER)
    reranker = os.environ.get("OLLAMA_TEST_RERANKER", DEFAULT_RERANKER)
    models = [llm, embedder]
    if os.environ.get("PULL_RERANKER") == "1":
        models.append(reranker)

    installed = installed_models(base_url)
    for model in models:
        if model_is_installed(model, installed):
            print(f"Already installed: {model}")
            continue
        print(f"Pulling CPU-friendly smoke model: {model}")
        result = pull_model(model, base_url)
        if result != 0:
            return result

    print("")
    print("Ollama smoke setup complete.")
    print("Run:")
    print("  RUN_OLLAMA_TESTS=1 make test-ollama-smoke")
    if os.environ.get("PULL_RERANKER") != "1":
        print("")
        print("Optional reranker smoke setup:")
        print("  PULL_RERANKER=1 make setup-ollama-smoke")
        print("  RUN_OLLAMA_TESTS=1 RUN_RERANKER_TESTS=1 make test-ollama-smoke")
    return 0


def ollama_reachable(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError):
        return False


def installed_models(base_url: str) -> set[str]:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return set()

    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return set()
    names = set()
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("name") or model.get("model")
        if isinstance(name, str) and name:
            names.add(name)
    return names


def model_is_installed(requested: str, installed: set[str]) -> bool:
    return resolved_model_name(requested, installed) is not None


def resolved_model_name(requested: str, installed: set[str]) -> str | None:
    candidates = [requested]
    if ":" not in requested:
        candidates.append(f"{requested}:latest")
    for candidate in candidates:
        if candidate in installed:
            return candidate
    requested_repo = requested.split(":", 1)[0]
    for name in installed:
        if name.split(":", 1)[0] == requested_repo:
            return name
    return None


def pull_model(model: str, base_url: str) -> int:
    env = os.environ.copy()
    env.setdefault("OLLAMA_HOST", base_url)
    try:
        completed = subprocess.run(
            ["ollama", "pull", model],
            check=False,
            env=env,
        )
    except OSError as exc:
        print(f"Could not run 'ollama pull {model}': {exc}")
        return 1
    if completed.returncode != 0:
        print(f"Failed to pull {model}.")
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
